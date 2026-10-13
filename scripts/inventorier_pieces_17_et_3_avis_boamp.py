"""Inventorier les seules références de consultation contenues dans vingt avis.

Sources : dix-sept notices indépendantes BOAMP et trois notices explicitement
liées, toutes conservées sous empreinte SHA-256. Une URL de dossier n'est pas
une pièce contractuelle téléchargée ni une preuve de son accessibilité.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qs
from zipfile import ZipFile

try:
    from scripts.suivre_avis_lies_independants_boamp import (
        LiensInvalides, lire_json, sha, sources, verifier_archive,
    )
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from suivre_avis_lies_independants_boamp import (
        LiensInvalides, lire_json, sha, sources, verifier_archive,
    )

VERSION = "references-pieces-vingt-avis-v1"
URL_MAX = 3000
MAX_MENTIONS = 120


def listes(valeur) -> list[dict]:
    if valeur is None:
        return []
    if isinstance(valeur, dict):
        return [valeur]
    if isinstance(valeur, list) and all(isinstance(x, dict) for x in valeur):
        return valeur
    raise LiensInvalides("Structure de références de documents ambiguë")


def textuel(valeur) -> str | None:
    if isinstance(valeur, str):
        return valeur
    if isinstance(valeur, dict) and set(valeur) <= {"#text", "@schemeName"}:
        valeur = valeur.get("#text")
        if isinstance(valeur, str):
            return valeur
    return None


def qualifier_url(adresse: object) -> str:
    """Aucune requête HTTP, même pour une adresse identifiant un dossier."""
    if not isinstance(adresse, str) or not 0 < len(adresse) <= URL_MAX:
        return "adresse_absente_ou_inexploitable"
    try:
        u = urlsplit(adresse)
    except ValueError:
        return "adresse_absente_ou_inexploitable"
    if (u.scheme != "https" or not u.hostname or u.username or u.password
            or u.fragment or u.port not in (None, 443)):
        return "adresse_absente_ou_inexploitable"
    domaine = u.hostname.casefold()
    if domaine.endswith(".safelinks.protection.outlook.com"):
        return "redirection_externe_non_suivie"
    p = u.path.casefold()
    q = parse_qs(u.query, keep_blank_values=True)
    if (re.search(r"/pack/annonce_marche_public_[0-9]+_[0-9]+[.]html$", p)
            or re.search(r"/entreprise/consultation/[0-9]+$", p)
            or ("pcslid" in {x.casefold() for x in q})
            or ("id" in q and any(
                x.isdecimal() and len(x) >= 4 for x in q["id"]
            ) and "entrepriseadvancedsearch" in u.query.casefold())):
        return "adresse_dossier_referencee"
    return "adresse_portail_ou_page_generique"


def extraire(notice: dict, code: str, origine: str, empreinte: str) -> list[dict]:
    brut = notice.get("donnees")
    if not isinstance(brut, str):
        return []
    structure = json.loads(brut)
    eforms = structure.get("EFORMS") if isinstance(structure, dict) else None
    if not isinstance(eforms, dict) or len(eforms) != 1:
        return []
    formulaire, racine = next(iter(eforms.items()))
    if not isinstance(racine, dict):
        raise LiensInvalides("Formulaire eForms invalide")
    lots = racine.get("cac:ProcurementProjectLot")
    blocs = listes(lots)
    lignes = []
    for i, lot in enumerate(blocs):
        termes = lot.get("cac:TenderingTerms")
        if termes is None:
            continue
        if not isinstance(termes, dict):
            raise LiensInvalides("Conditions de consultation non structurées")
        references = termes.get("cac:CallForTendersDocumentReference")
        for j, ref in enumerate(listes(references)):
            attache = ref.get("cac:Attachment")
            externe = attache.get("cac:ExternalReference") if isinstance(attache, dict) else None
            url = externe.get("cbc:URI") if isinstance(externe, dict) else None
            if isinstance(url, dict):
                url = textuel(url)
            if isinstance(url, str) and len(url) > URL_MAX:
                raise LiensInvalides("Adresse documentaire trop longue")
            champ_lot = (
                f"/donnees/EFORMS/{formulaire}/cac:ProcurementProjectLot"
                + (f"/{i}" if isinstance(lots, list) else "")
            )
            chemin = champ_lot + "/cac:TenderingTerms/cac:CallForTendersDocumentReference"
            if isinstance(references, list):
                chemin += f"/{j}"
            reference = textuel(ref.get("cbc:ID"))
            if reference is not None and len(reference) > 300:
                raise LiensInvalides("Référence documentaire trop longue")
            lignes.append({
                "avis": code, "origine": origine, "sha256_reponse_officielle": empreinte,
                "lot_position": i,
                "reference_declaree": reference,
                "adresse_citee": url,
                "categorie_adresse": qualifier_url(url),
                "chemin_reference": chemin,
                "chemin_adresse": chemin + "/cac:Attachment/cac:ExternalReference/cbc:URI",
                "document_telecharge": False,
                "acte_contractuel_verifie": False,
            })
            if len(lignes) > MAX_MENTIONS:
                raise LiensInvalides("Plafond de références dans un avis dépassé")
    return lignes


def produire(archive_boamp: Path, chaines: Path, lies: Path) -> dict:
    liens_sources, sha_chaines = sources(archive_boamp, chaines)
    rapport_lies = verifier_archive(lies, archive_boamp, chaines)
    assert len(liens_sources) == len(rapport_lies["avis_lies"])
    octets_rapport_lies = (lies / "rapport.json").read_bytes()
    chaines_doc = lire_json(chaines.read_bytes())
    origines = chaines_doc["dossiers"]
    lignes = []
    avis = []
    with ZipFile(archive_boamp) as z:
        for fiche in origines:
            code = fiche["avis_boamp"]
            b = z.read("releve-issues-36/" + code + ".json")
            if sha(b) != fiche["empreinte_avis_boamp"]:
                raise LiensInvalides("Empreinte de notice d'origine divergente")
            n = lire_json(b)["results"][0]
            extraites = extraire(n, code, "avis_echantillon_17", sha(b))
            lignes.extend(extraites)
            avis.append({"avis": code, "origine": "avis_echantillon_17",
                         "references_declarees": len(extraites),
                         "empreinte_source": sha(b)})
    for fiche in rapport_lies["avis_lies"]:
        code = fiche["avis_lie"]
        b = (lies / (code + ".json")).read_bytes()
        if sha(b) != fiche["sha256"]:
            raise LiensInvalides("Empreinte d'avis lié différente")
        if fiche["statut_recherche"] != "avis_officiel_retrouve":
            avis.append({"avis": code, "origine": "avis_explicitement_lie",
                         "references_declarees": None,
                         "empreinte_source": sha(b)})
            continue
        n = lire_json(b)["results"][0]
        extraites = extraire(n, code, "avis_explicitement_lie", sha(b))
        lignes.extend(extraites)
        avis.append({"avis": code, "origine": "avis_explicitement_lie",
                     "references_declarees": len(extraites),
                     "empreinte_source": sha(b)})
    if (len(avis) != 20 or len({x["avis"] for x in avis}) != 20
            or len(lignes) > MAX_MENTIONS * 20):
        raise LiensInvalides("Périmètre de vingt avis altéré")
    classes = Counter(x["categorie_adresse"] for x in lignes)
    reliees = {}
    for x in lignes:
        reliees.setdefault(x["avis"], set()).add(x["adresse_citee"])
    regroupement = {}
    for x in rapport_lies["avis_lies"]:
        parent, enfant = x["avis_source"], x["avis_lie"]
        lp = {r["adresse_citee"] for r in lignes if r["avis"] == parent}
        le = {r["adresse_citee"] for r in lignes if r["avis"] == enfant}
        communs = sorted((lp & le) - {None})
        regroupement[parent] = {
            "avis_lie": enfant,
            "adresses_strictement_identiques": communs,
            "adresses_precises_identiques": [
                u for u in communs if qualifier_url(u) == "adresse_dossier_referencee"
            ],
            "identity_juridique_etablie": False,
        }
    return {
        "version": VERSION,
        "sha256_rapport_chaines": sha_chaines,
        "sha256_rapport_avis_lies": sha(octets_rapport_lies),
        "nombre_avis_examens": len(avis),
        "nombre_avis_origine": len(origines),
        "nombre_avis_lies_retrouves": rapport_lies["nombre_retrouves"],
        "nombre_avis_mentionnant_documents": len(reliees),
        "nombre_mentions_references_documents": len(lignes),
        "nombre_adresses_distinctes": len({x["adresse_citee"] for x in lignes if x["adresse_citee"]}),
        "nombre_paires_avis_adresse_distinctes": sum(len(s) for s in reliees.values()),
        "categories": dict(sorted(classes.items())),
        "concordances_adresses_entre_avis_lies": regroupement,
        "avis": avis,
        "references_documentaires": lignes,
        "pieces_effectivement_telechargees": 0,
        "actes_contractuels_verifies": 0,
        "premiere_contribution_utile_mesuree": 0,
        "limite": (
            "Mention dans un champ eForms seulement. Une adresse de dossier "
            "ne garantit ni accessibilité publique ni téléchargement, "
            "et une adresse de portail générique ne désigne aucun dossier."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-boamp", type=Path, required=True)
    p.add_argument("--chaines", type=Path, required=True)
    p.add_argument("--avis-lies", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.sortie.exists() or a.sortie.is_symlink():
            raise LiensInvalides("Refus d'écraser un rapport")
        d = produire(a.archive_boamp, a.chaines, a.avis_lies)
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        a.sortie.write_text(
            json.dumps(d, sort_keys=True, ensure_ascii=False, indent=2,
                       allow_nan=False) + "\n", encoding="utf-8",
        )
        print(json.dumps({
            "avis": d["nombre_avis_examens"],
            "avis_avec_references": d["nombre_avis_mentionnant_documents"],
            "mentions": d["nombre_mentions_references_documents"],
            "adresses_distinctes": d["nombre_adresses_distinctes"],
            "pieces_obtenues": 0,
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, f"Inventaire de pièces refusé : {exc}\n")


if __name__ == "__main__":
    main()
