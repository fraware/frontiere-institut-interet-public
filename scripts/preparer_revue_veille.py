"""Préparer une file de revue documentaire sans attribuer de besoin opérationnel.

Deux provenances publiques déjà enregistrées sont analysées hors réseau :
publications des flux institutionnels et délibérations SCDL. La recherche
lexicale sert uniquement à sélectionner des pièces à examiner.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

from scripts.auditer_fraicheur_veille import PolitiqueInvalide, date_utc

RACINE = Path(__file__).resolve().parents[1]
FLUX = Path("institutionnel/flux_publics/observations.json")
DELIBERATIONS = Path("institutionnel/deliberations_publiques/pistes.json")
MOTIFS = {
    "intelligence_artificielle": re.compile(r"\bintelligence artificielle\b|\bia generative\b"),
    "cybersecurite": re.compile(r"\bcybersecurite\b|\bsecurite informatique\b"),
    "recherche": re.compile(r"\brecherche scientifique\b|\blaboratoires? de recherche\b"),
    "infrastructure": re.compile(r"\binfrastructures? de calcul\b|\bcalcul intensif\b"),
    "competence": re.compile(r"\bcompetences? techniques\b|\bexpertise scientifique\b"),
    "commande_publique": re.compile(r"\bcommande publique\b|\bmarches? publics?\b"),
}
PLAFOND_TITRE = 190


def normaliser(valeur: str) -> str:
    terme = unicodedata.normalize("NFKD", valeur.casefold())
    return "".join(c for c in terme if not unicodedata.combining(c))


def reperes(texte: str) -> list[str]:
    return [nom for nom, motif in MOTIFS.items() if motif.search(normaliser(texte))]


def url_reference(valeur: object) -> str | None:
    if not isinstance(valeur, str) or len(valeur) > 2048:
        return None
    details = urlsplit(valeur)
    if (details.scheme != "https" or not details.hostname or details.username
            or details.password or details.port not in (None, 443)):
        return None
    return valeur


def categorie_temporelle(date: str | None, maintenant: datetime) -> str:
    if date is None:
        return "date_publication_inconnue"
    try:
        moment = date_utc(date)
    except PolitiqueInvalide:
        return "date_publication_invalide"
    jours = (maintenant - moment).total_seconds() / 86400
    if jours < -1:
        return "date_publication_future_a_verifier"
    return "publication_90_jours" if jours <= 90 else "archives"


def preparer_revue(flux: dict, deliberations: dict, maintenant: datetime,
                   *, limite: int = 80) -> dict:
    """Produire une file sans fusion ni classement de crédibilité d'un besoin."""
    if type(limite) is not int or not 1 <= limite <= 500:
        raise PolitiqueInvalide("Limite des dossiers invalide")
    publications = flux.get("observations")
    actes = deliberations.get("pistes")
    if not isinstance(publications, list) or not isinstance(actes, list):
        raise PolitiqueInvalide("Registres d'observation incomplets")
    candidats = []
    identifiants = set()
    for item in publications:
        if not isinstance(item, dict):
            raise PolitiqueInvalide("Publication mal formée")
        if item.get("nature_signal") != "publication_publique_non_qualifiee":
            raise PolitiqueInvalide("Nature de signal inattendue")
        identifiant = item.get("identifiant_publication")
        source = item.get("source_id")
        titre = item.get("titre")
        premier = item.get("observe_initialement_le")
        if (not isinstance(identifiant, str) or len(identifiant) != 64
                or not isinstance(source, str) or not isinstance(titre, str)
                or not isinstance(premier, str)):
            raise PolitiqueInvalide("Identité ou provenance de publication incorrecte")
        date_utc(premier)
        identite = "flux:" + source + ":" + identifiant
        if identite in identifiants:
            raise PolitiqueInvalide("Publication dupliquée")
        identifiants.add(identite)
        mots = reperes(titre + " " + str(item.get("description") or ""))
        if not mots:
            continue
        candidats.append({
            "id": identite,
            "nature": "publication_institutionnelle",
            "source_id": source,
            "reperage_lexical": mots,
            "titre_court": " ".join(titre.split())[:PLAFOND_TITRE],
            "url_reference": url_reference(item.get("lien")),
            "date_publication": item.get("date_publication"),
            "observe_pour_la_premiere_fois": premier,
            "classe_temporelle": categorie_temporelle(item.get("date_publication"), maintenant),
            "statut_preuve": "publication_non_qualifiee",
        })
    for item in actes:
        if not isinstance(item, dict):
            raise PolitiqueInvalide("Délibération mal formée")
        identifiant = item.get("identifiant")
        premier = item.get("observe_pour_la_premiere_fois")
        if (not isinstance(identifiant, str) or len(identifiant) != 64
                or not isinstance(premier, str)):
            raise PolitiqueInvalide("Identité SCDL absente")
        date_utc(premier)
        identite = "scdl:" + identifiant
        if identite in identifiants:
            raise PolitiqueInvalide("Délibération dupliquée")
        identifiants.add(identite)
        jour = item.get("deliberation_date")
        date_acte = jour + "T00:00:00+00:00" if isinstance(jour, str) else None
        candidats.append({
            "id": identite,
            "nature": "piste_de_deliberation",
            "source_id": item.get("jeu_id"),
            "reperage_lexical": item.get("mots_de_reperage"),
            "titre_court": None,
            "reference_acte": item.get("deliberation_id"),
            "collectivite": item.get("collectivite"),
            "url_reference": url_reference(item.get("url_document_annonce")),
            "date_publication": date_acte,
            "observe_pour_la_premiere_fois": premier,
            "classe_temporelle": categorie_temporelle(date_acte, maintenant),
            "statut_preuve": "correspondance_scdl_non_qualifiee",
        })
    candidats.sort(key=lambda x: (x["observe_pour_la_premiere_fois"], x["id"]), reverse=True)
    vus = candidats[:limite]
    return {
        "version": 1,
        "produit_le": maintenant.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "fichiers_sources": [str(FLUX), str(DELIBERATIONS)],
        "selection_par_reperage_lexical_uniquement": True,
        "nombre_total_de_pistes_selectionnees": len(candidats),
        "nombre_dossiers_dans_la_file": len(vus),
        "file_limitee": len(candidats) > limite,
        "dossiers": vus,
    }


def resume(revue: dict) -> str:
    lignes = [
        "## FRONTIÈRE — file de revue documentaire",
        f"{revue['nombre_dossiers_dans_la_file']} pistes affichées sur "
        f"{revue['nombre_total_de_pistes_selectionnees']} repérages. "
        "**Aucune n'est un besoin public validé.**",
        "",
        "| Origine | Date du document | Statut | Repères |",
        "|---|---|---|---|",
    ]
    for item in revue["dossiers"][:25]:
        date = item["date_publication"] or "inconnue"
        lignes.append(
            f"| {item['nature']} | {date} | {item['classe_temporelle']} | "
            f"{', '.join(item['reperage_lexical'] or [])} |"
        )
    if revue["nombre_dossiers_dans_la_file"] > 25:
        lignes.append("")
        lignes.append("Consulter le fichier JSON joint pour la liste complète.")
    lignes.append("")
    lignes.append("La file sert uniquement à choisir des documents à relire. "
                  "Les décisions, usages, effets et compétences ne sont pas déduits automatiquement.")
    return "\n".join(lignes) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--racine", type=Path, default=RACINE)
    parser.add_argument("--limite", type=int, default=80)
    parser.add_argument("--sortie-json", type=Path)
    parser.add_argument("--resume-markdown", type=Path)
    args = parser.parse_args()
    try:
        a = json.loads((args.racine / FLUX).read_text(encoding="utf-8"))
        b = json.loads((args.racine / DELIBERATIONS).read_text(encoding="utf-8"))
        resultat = preparer_revue(a, b, datetime.now(timezone.utc), limite=args.limite)
    except (OSError, ValueError, TypeError) as exc:
        print(f"Revue impossible : {type(exc).__name__}: {exc}")
        return 1
    texte = resume(resultat)
    print(texte)
    if args.sortie_json:
        args.sortie_json.parent.mkdir(parents=True, exist_ok=True)
        args.sortie_json.write_text(json.dumps(resultat, ensure_ascii=False, indent=2)
                                    + "\n", encoding="utf-8")
    if args.resume_markdown:
        args.resume_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.resume_markdown.write_text(texte, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
