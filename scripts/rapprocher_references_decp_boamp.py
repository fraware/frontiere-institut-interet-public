"""Présélection documentaire entre marchés DECP et avis BOAMP archivés.

Une référence interne de *procédure* BOAMP ressemblant à un identifiant de
*contrat* DECP ne constitue jamais une identité contractuelle prouvée.
Ce programme produit uniquement des pistes auditables, sans imputer d'effet
sur les compétences, les budgets ou les délais d'exécution.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unicodedata

try:
    from scripts.collecter_notices_pilotes_boamp import verifier_capture
    from scripts.consolider_attributions_decp import rapports_dgfip
    from scripts.indexer_attributions_decp_sqlite import verifier_rapport
except ModuleNotFoundError as exc:
    # En exécution directe, Python place scripts/ et non sa racine sur sys.path.
    if exc.name != "scripts":
        raise
    from collecter_notices_pilotes_boamp import verifier_capture
    from consolider_attributions_decp import rapports_dgfip
    from indexer_attributions_decp_sqlite import verifier_rapport

VERSION = "rapprochement-references-decp-boamp-v1"
CHEMIN_REFERENCE = "/donnees/EFORMS/{formulaire}/cac:ProcurementProject/cbc:ID"
CODE_AVIS = re.compile(r"^[0-9]{2}-[0-9]{2,8}$")
MAX_AVIS = 1500


class RapprochementInvalide(ValueError):
    """Relevé incomplet, incohérent ou dépourvu d'une provenance contrôlable."""


def empreinte(chemin: Path) -> str:
    """Empreinte des octets archivés, indépendamment du traitement JSON."""
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def reference_normalisee(valeur: object) -> str | None:
    """Normalisation de recherche, explicitement non probante juridiquement.

    Les accents, espaces et signes de ponctuation sont neutralisés. Une
    référence très courte est exclue afin de limiter les collisions triviales.
    """
    if not isinstance(valeur, str) or len(valeur) > 200:
        return None
    texte = unicodedata.normalize("NFKD", valeur)
    cle = "".join(c.upper() for c in texte if c.isascii() and c.isalnum())
    return cle if 6 <= len(cle) <= 100 else None


def _texte_id(valeur: object) -> str | None:
    """Lire uniquement un identifiant scalaire ou son contenu textuel XML."""
    if isinstance(valeur, dict):
        if set(valeur) - {"#text", "@schemeName", "@schemeAgencyID"}:
            return None
        valeur = valeur.get("#text")
    return valeur if isinstance(valeur, str) else None


def extraire_reference(notice: dict) -> tuple[str | None, str | None, str]:
    """Lire le chemin officiel connu, sans recherche récursive opportuniste."""
    donnees = notice.get("donnees")
    if not isinstance(donnees, str):
        return None, None, "formulaire_absent_ou_inconnu"
    try:
        structure = json.loads(donnees)
    except (ValueError, TypeError) as exc:
        raise RapprochementInvalide("Formulaire officiel JSON incorrect.") from exc
    if not isinstance(structure, dict):
        raise RapprochementInvalide("Formulaire officiel non structuré.")
    eforms = structure.get("EFORMS")
    if not isinstance(eforms, dict) or len(eforms) != 1:
        return None, None, "format_non_interprete"
    type_formulaire, corps = next(iter(eforms.items()))
    if type_formulaire not in {"ContractNotice", "ContractAwardNotice"} or not isinstance(corps, dict):
        return None, None, "format_non_interprete"
    projet = corps.get("cac:ProcurementProject")
    if not isinstance(projet, dict):
        return None, None, "reference_absente"
    originale = _texte_id(projet.get("cbc:ID"))
    if originale is None:
        return None, None, "reference_absente"
    normalisee = reference_normalisee(originale)
    if normalisee is None:
        return None, None, "reference_non_comparable"
    return normalisee, originale, CHEMIN_REFERENCE.format(formulaire=type_formulaire)


def lire_marches(aife: Path, dgfip: Path) -> tuple[dict, dict]:
    """Valider les relevés entiers avant de regrouper les contrats distincts."""
    rapport_aife = json.loads(aife.read_text(encoding="utf-8"))
    rapport_dgfip = json.loads(dgfip.read_text(encoding="utf-8"))
    rapports = [rapport_aife] + rapports_dgfip(rapport_dgfip)
    marches: dict[tuple[str, str], dict] = {}
    for rapport in rapports:
        for ligne in verifier_rapport(rapport):
            cle = (ligne["acheteur_siret"], ligne["id_marche"])
            fiche = marches.setdefault(cle, {
                "acheteur_siret": cle[0],
                "id_marche": cle[1],
                "versions_observees": 0,
                "provenances": [],
            })
            fiche["versions_observees"] += 1
            fiche["provenances"].append({
                "source_catalogue": rapport["source_catalogue"],
                "ressource_id": rapport["ressource_id"],
                "sha256_fichier_brut": rapport["sha256_fichier_brut"],
            })
    references = defaultdict(list)
    non_comparables = 0
    for cle, fiche in sorted(marches.items()):
        normalisee = reference_normalisee(cle[1])
        if normalisee is None:
            non_comparables += 1
            continue
        references[normalisee].append(fiche)
    return dict(references), {
        "identites_marches": len(marches),
        "identites_non_comparables": non_comparables,
        "sha256_releve_aife": empreinte(aife),
        "sha256_releve_dgfip": empreinte(dgfip),
    }


def lire_avis(dossiers: list[Path]) -> tuple[dict, dict]:
    """Contrôler chaque manifeste existant et chaque octet BOAMP conservé."""
    avis = {}
    nombre_fichiers = 0
    non_interpretes = defaultdict(int)
    for dossier in dossiers:
        rapport = verifier_capture(dossier)
        nombre_fichiers += len(rapport["cas"])
        if nombre_fichiers > MAX_AVIS:
            raise RapprochementInvalide("Plafond de notices BOAMP dépassé.")
        for fiche in rapport["cas"]:
            code = fiche["identifiant"]
            if not CODE_AVIS.fullmatch(code):
                raise RapprochementInvalide("Identifiant BOAMP incompatible.")
            chemin = dossier / fiche["fichier_reponse"]
            brut = chemin.read_bytes()
            sha = hashlib.sha256(brut).hexdigest()
            if sha != fiche["sha256_reponse_http"]:
                raise RapprochementInvalide("Empreinte BOAMP modifiée.")
            if code in avis:
                if avis[code]["sha256_reponse_http"] != sha:
                    raise RapprochementInvalide("Deux versions incompatibles du même avis.")
                continue
            if fiche["etat_observation"] != "notice_retrouvee_et_identifiee":
                non_interpretes["non_retrouve"] += 1
                avis[code] = {"sha256_reponse_http": sha, "reference": None}
                continue
            source = json.loads(brut)["results"][0]
            reference, originale, chemin_reference = extraire_reference(source)
            if reference is None:
                non_interpretes[chemin_reference] += 1
            avis[code] = {
                "identifiant": code,
                "sha256_reponse_http": sha,
                "url_officielle": fiche["source_officielle_interrogee"],
                "date_parution": fiche["date_parution_reobservee"],
                "nature": source.get("nature"),
                "reference": reference,
                "reference_originale": originale,
                "chemin_reference": chemin_reference,
                "acheteur_libelle_non_verifie": source.get("nomacheteur"),
            }
    references = defaultdict(list)
    for fiche in avis.values():
        if fiche["reference"] is not None:
            references[fiche["reference"]].append(fiche)
    return dict(references), {
        "avis_distincts": len(avis),
        "avis_references_interpretees": sum(map(len, references.values())),
        "avis_non_interpretes": dict(sorted(non_interpretes.items())),
    }


def produire(aife: Path, dgfip: Path, captures: list[Path]) -> dict:
    """Ne promouvoir aucune concordance de référence en lien contractuel certain."""
    if not captures:
        raise RapprochementInvalide("Une archive de captures BOAMP est indispensable.")
    marches, compte_marches = lire_marches(aife, dgfip)
    avis, compte_avis = lire_avis(captures)
    pistes = []
    for ref, notices in sorted(avis.items()):
        candidats = marches.get(ref, [])
        if not candidats:
            continue
        pistes.append({
            "reference_normalisee": ref,
            "classement": (
                "reference_partagee_plusieurs_identites_de_marche"
                if len(candidats) > 1 else "reference_commune_non_suffisante"
            ),
            "avis_boamp": sorted(notices, key=lambda n: n["identifiant"]),
            "identites_decp": candidats,
            "nombre_avis": len(notices),
            "nombre_marches_distincts": len(candidats),
            "identite_contractuelle_verifiee": False,
            "concordance_siret_verifiee_dans_boamp": False,
            "examen_humain_ou_piece_complementaire_necessaire": True,
        })
    return {
        "version": VERSION,
        "entrees": {**compte_marches, **compte_avis,
                    "captures": len(captures)},
        "nombre_references_communes": len(pistes),
        "nombre_pistes_avec_un_marche": sum(
            len(p["identites_decp"]) == 1 for p in pistes
        ),
        "nombre_pistes_ambigues": sum(
            len(p["identites_decp"]) > 1 for p in pistes
        ),
        "correspondances_contractuelles_verifiees": 0,
        "preuve_premiere_contribution_utile": False,
        "pistes": pistes,
        "limite": (
            "Une référence de procédure BOAMP et un identifiant de contrat DECP "
            "peuvent coïncider sans désigner juridiquement le même marché. "
            "Aucune correspondance contractuelle, date d'exécution ni pénurie "
            "de compétences n'est établie par cette seule présélection."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aife", type=Path,
                   default=Path("institutionnel/decp/sonde_aife_json.json"))
    p.add_argument("--dgfip", type=Path,
                   default=Path("institutionnel/decp/lot_dgfip_xml.json"))
    p.add_argument("--captures", type=Path, action="append", required=True,
                   help="Dossier de captures BOAMP avec rapport.json et réponses brutes.")
    p.add_argument("--sortie", type=Path, required=True)
    args = p.parse_args()
    try:
        rapport = produire(args.aife, args.dgfip, args.captures)
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.sortie.parent) as dossier:
            temporaire = Path(dossier) / "rapport.json"
            temporaire.write_text(
                json.dumps(rapport, indent=2, ensure_ascii=False,
                           sort_keys=True, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            temporaire.replace(args.sortie)
        print(json.dumps({
            "references_communes": rapport["nombre_references_communes"],
            "pistes_ambigues": rapport["nombre_pistes_ambigues"],
            "correspondances_contractuelles_verifiees": 0,
        }, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.exit(1, f"Rapprochement refusé : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
