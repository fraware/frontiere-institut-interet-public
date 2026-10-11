"""Capturer deux avis BOAMP amont, sous condition d'identité de procédure.

La concordance documentaire n'établit ni début d'exécution ni pénurie.
Les réponses officielles sont conservées octet par octet.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata

try:
    from scripts.collecter_notices_pilotes_boamp import (
        adresse, obtenir_octets, qualifier, verifier_capture,
    )
    from scripts.collecter_avis_lies_boamp import verifier_lies
except ModuleNotFoundError:
    from collecter_notices_pilotes_boamp import (
        adresse, obtenir_octets, qualifier, verifier_capture,
    )
    from collecter_avis_lies_boamp import verifier_lies

VERSION = "captures-avis-amont-boamp-v1"


class AvisAmontInvalide(ValueError):
    """Réponse historique ou rattachement documentaire incompatible."""


def normaliser(texte: str) -> str:
    if not isinstance(texte, str):
        raise AvisAmontInvalide("Identifiant ou acheteur absent.")
    ascii_ = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in ascii_ if c.isascii() and c.isalnum()).upper()


def identifiant_interne(notice: dict) -> str:
    formulaire = notice.get("donnees")
    if not isinstance(formulaire, str):
        raise AvisAmontInvalide("Formulaire détaillé absent.")
    try:
        structure = json.loads(formulaire)
    except json.JSONDecodeError as exc:
        raise AvisAmontInvalide("Formulaire détaillé invalide.") from exc
    documents = structure.get("EFORMS") if isinstance(structure, dict) else None
    if not isinstance(documents, dict) or len(documents) != 1:
        raise AvisAmontInvalide("Formulaire européen inattendu.")
    racine = next(iter(documents.values()))
    projet = racine.get("cac:ProcurementProject") if isinstance(racine, dict) else None
    valeur = projet.get("cbc:ID") if isinstance(projet, dict) else None
    if isinstance(valeur, dict):
        valeur = valeur.get("#text")
    if not isinstance(valeur, str) or not valeur.strip():
        raise AvisAmontInvalide("Identifiant interne du marché absent.")
    return normaliser(valeur)


def obtenir_avis_aval(principaux: Path, lies: Path) -> dict:
    original = verifier_capture(principaux)
    lies_verifies = verifier_lies(lies, principaux)
    ensemble = {}
    for dossier, fiches, code_cle, fichier_cle, empreinte_cle, statut_cle, attendu in [
        (principaux, original["cas"], "identifiant", "fichier_reponse",
         "sha256_reponse_http", "etat_observation", "notice_retrouvee_et_identifiee"),
        (lies, lies_verifies["avis"], "identifiant", "fichier",
         "sha256", "etat_recherche", "notice_retrouvee"),
    ]:
        for fiche in fiches:
            if fiche[statut_cle] != attendu:
                continue
            code = fiche[code_cle]
            if code in ensemble:
                raise AvisAmontInvalide("Avis aval dupliqué dans les archives.")
            notice = json.loads((dossier / fiche[fichier_cle]).read_bytes())["results"][0]
            ensemble[code] = {"notice": notice, "sha256": fiche[empreinte_cle]}
    return ensemble


def lire_candidats(chemin: Path) -> list[dict]:
    registre = json.loads(chemin.read_text(encoding="utf-8"))
    if registre.get("version") != "avis-amont-cibles-boamp-v1":
        raise AvisAmontInvalide("Version du registre de candidats inconnue.")
    candidats = registre.get("candidats")
    if not isinstance(candidats, list) or not candidats or len(candidats) > 12:
        raise AvisAmontInvalide("Effectif de candidats incorrect.")
    codes = []
    for c in candidats:
        for cle in ("avis_amont", "avis_aval"):
            if not isinstance(c.get(cle), str) or not re.fullmatch(r"[0-9]{2}-[0-9]{2,8}", c[cle]):
                raise AvisAmontInvalide("Identifiant du registre invalide.")
        if not isinstance(c.get("reference_interne_normalisee"), str) or not re.fullmatch(
            r"[A-Z0-9]{6,80}", c["reference_interne_normalisee"]
        ):
            raise AvisAmontInvalide("Référence interne cible invalide.")
        codes.append(c["avis_amont"])
    if len(codes) != len(set(codes)):
        raise AvisAmontInvalide("Avis amont dupliqué.")
    return candidats


def qualifier_amont(brut: bytes, candidat: dict, aval: dict) -> dict:
    observation = qualifier(brut, candidat["avis_amont"], candidat["date_attendue"])
    if observation["etat_observation"] != "notice_retrouvee_et_identifiee":
        return {"statut": "non_retrouve_lors_du_releve", "date_parution": None,
                "nature": None, "etat": None,
                "reference_interne_observee": None, "acheteur_concordant": None}
    notice = json.loads(brut)["results"][0]
    ref = identifiant_interne(notice)
    if ref != candidat["reference_interne_normalisee"]:
        raise AvisAmontInvalide("L'identifiant interne de l'avis amont contredit le registre.")
    if identifiant_interne(aval["notice"]) != ref:
        raise AvisAmontInvalide("Identifiants internes amont et aval différents.")
    if normaliser(notice.get("nomacheteur")) != normaliser(aval["notice"].get("nomacheteur")):
        raise AvisAmontInvalide("Acheteurs amont et aval différents.")
    if notice["dateparution"] > aval["notice"]["dateparution"]:
        raise AvisAmontInvalide("Avis amont publié après son avis aval.")
    return {"statut": "avis_amont_identifie_par_reference", "date_parution": notice["dateparution"],
            "nature": notice.get("nature"), "etat": notice.get("etat"),
            "reference_interne_observee": ref, "acheteur_concordant": True}


def verifier_amont(dossier: Path, principaux: Path, lies: Path, registre: Path) -> dict:
    avals = obtenir_avis_aval(principaux, lies)
    candidats = lire_candidats(registre)
    rapport = json.loads((dossier / "rapport.json").read_text(encoding="utf-8"))
    if (rapport.get("version") != VERSION or
        rapport.get("sha256_registre") != hashlib.sha256(registre.read_bytes()).hexdigest()):
        raise AvisAmontInvalide("Version ou empreinte de registre incorrecte.")
    fiches = rapport.get("avis", [])
    if len(fiches) != len(candidats) or [
        x.get("avis_amont") for x in fiches
    ] != [x["avis_amont"] for x in candidats]:
        raise AvisAmontInvalide("Inventaire de l'archive incohérent.")
    for candidat, fiche in zip(candidats, fiches):
        code = candidat["avis_amont"]
        aval = avals.get(candidat["avis_aval"])
        if not aval or fiche.get("avis_aval") != candidat["avis_aval"] or (
            fiche.get("empreinte_avis_aval") != aval["sha256"]
        ):
            raise AvisAmontInvalide("Avis aval absent ou empreinte incompatible.")
        chemin = dossier / (code + ".json")
        if chemin.is_symlink() or not chemin.is_file() or fiche.get("fichier_reponse") != chemin.name:
            raise AvisAmontInvalide("Fichier de réponse amont absent.")
        brut = chemin.read_bytes()
        if (hashlib.sha256(brut).hexdigest() != fiche.get("sha256_reponse_http") or
            len(brut) != fiche.get("octets")):
            raise AvisAmontInvalide("Empreinte ou longueur de la réponse amont incorrecte.")
        if fiche.get("source_officielle") != adresse(code):
            raise AvisAmontInvalide("Source de l'avis amont modifiée.")
        observation = qualifier_amont(brut, candidat, aval)
        if any(fiche.get(cle) != valeur for cle, valeur in observation.items()):
            raise AvisAmontInvalide("Qualification documentaire incohérente.")
    if rapport.get("retrouves") != sum(x["statut"] == "avis_amont_identifie_par_reference" for x in fiches):
        raise AvisAmontInvalide("Nombre d'avis amont trouvés incohérent.")
    return rapport


def capturer_amont(principaux: Path, lies: Path, registre: Path,
                   sortie: Path, obtenir=obtenir_octets,
                   instant: datetime | None = None) -> dict:
    observation = instant or datetime.now(timezone.utc)
    if observation.tzinfo is None or observation.utcoffset() is None:
        raise AvisAmontInvalide("Horodatage sans fuseau.")
    candidats, avals = lire_candidats(registre), obtenir_avis_aval(principaux, lies)
    if sortie.exists() or sortie.is_symlink():
        raise AvisAmontInvalide("Répertoire de sortie déjà existant.")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".amont-boamp-", dir=sortie.parent))
    try:
        fiches = []
        for candidat in candidats:
            code = candidat["avis_amont"]
            aval = avals.get(candidat["avis_aval"])
            if aval is None:
                raise AvisAmontInvalide("Avis aval absent des captures vérifiées.")
            url = adresse(code)
            brut = obtenir(url)
            resultat = qualifier_amont(brut, candidat, aval)
            nom = code + ".json"
            (temp / nom).write_bytes(brut)
            fiches.append({
                "avis_amont": code, "avis_aval": candidat["avis_aval"],
                "empreinte_avis_aval": aval["sha256"], "source_officielle": url,
                "fichier_reponse": nom, "octets": len(brut),
                "sha256_reponse_http": hashlib.sha256(brut).hexdigest(), **resultat,
            })
        rapport = {
            "version": VERSION,
            "observation": observation.astimezone(timezone.utc).isoformat(),
            "sha256_registre": hashlib.sha256(registre.read_bytes()).hexdigest(),
            "avis": fiches,
            "retrouves": sum(x["statut"] == "avis_amont_identifie_par_reference" for x in fiches),
            "pieces_contractuelles_obtenues": False,
            "livraison_et_reception_verifiees": False,
            "premiere_contribution_utile_etablie": False,
            "causes_des_besoins_etablies": False,
        }
        (temp / "rapport.json").write_text(
            json.dumps(rapport, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        verifier_amont(temp, principaux, lies, registre)
        os.rename(temp, sortie)
        return rapport
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--principaux", type=Path, required=True)
    p.add_argument("--lies", type=Path, required=True)
    p.add_argument("--registre", type=Path,
                   default=Path("evaluation/avis_amont_cibles_boamp_v1.json"))
    p.add_argument("--sortie", type=Path)
    p.add_argument("--verifier", type=Path)
    a = p.parse_args()
    try:
        if a.verifier:
            bilan = verifier_amont(a.verifier, a.principaux, a.lies, a.registre)
        elif a.sortie:
            bilan = capturer_amont(a.principaux, a.lies, a.registre, a.sortie)
        else:
            raise AvisAmontInvalide("Préciser --sortie ou --verifier.")
        print(json.dumps({"candidats": len(bilan["avis"]),
                          "retrouves": bilan["retrouves"]}, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.exit(1, f"Capture amont non validée : {exc}\n")


if __name__ == "__main__":
    main()
