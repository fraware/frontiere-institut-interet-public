from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_LOCAL = RACINE / "institutionnel" / "entites" / "locales"
DOSSIER_ROAE = RACINE / "institutionnel" / "entites" / "roae"
BASE = (
    "https://api-lannuaire.service-public.gouv.fr/api/explore/v2.1/catalog/"
    "datasets/api-lannuaire-administration-locale-competence-geographique/records"
)

CODE_COMMUNE_RE = re.compile(r"^[0-9A-Z]{5}$")
TYPE_SERVICE_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def nettoyer(valeur: Any) -> str | None:
    if valeur is None:
        return None
    texte = str(valeur).strip()
    return texte or None


def charger_index(dossier: Path, cle_identifiant: str) -> dict[str, dict[str, Any]]:
    resultat: dict[str, dict[str, Any]] = {}
    if not dossier.exists():
        return resultat

    for chemin in sorted(dossier.glob("*.jsonl")):
        with chemin.open("r", encoding="utf-8") as fichier:
            for ligne in fichier:
                if not ligne.strip():
                    continue
                entite = json.loads(ligne)
                identifiants = entite.get("identifiants") or {}
                identifiant = nettoyer(identifiants.get(cle_identifiant))
                if identifiant:
                    resultat[identifiant] = entite
    return resultat


def construire_where(commune: str | None, type_service: str | None) -> str:
    clauses = []
    if commune:
        valeur = commune.strip().upper()
        if not CODE_COMMUNE_RE.fullmatch(valeur):
            raise ValueError(
                "Le code Insee doit contenir exactement cinq caractères alphanumériques."
            )
        clauses.append(f'code_insee_commune="{valeur}"')
    if type_service:
        valeur = type_service.strip()
        if not TYPE_SERVICE_RE.fullmatch(valeur):
            raise ValueError(
                "Le type de service contient des caractères non autorisés."
            )
        clauses.append(f'code_type_service_local="{valeur}"')
    if not clauses:
        raise ValueError(
            "Une commune ou un type de service est nécessaire. "
            "Le jeu complet comporte plusieurs millions d'enregistrements."
        )
    return " AND ".join(clauses)


def interroger(commune: str | None, type_service: str | None) -> list[dict[str, Any]]:
    where = construire_where(commune, type_service)
    offset = 0
    resultats: list[dict[str, Any]] = []

    while True:
        parametres = urllib.parse.urlencode(
            {
                "where": where,
                "limit": 100,
                "offset": offset,
                "order_by": "code_insee_commune,code_type_service_local",
            }
        )
        requete = urllib.request.Request(
            f"{BASE}?{parametres}",
            headers={
                "User-Agent": "FRONTIERE-referentiel-institutionnel/2.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(requete, timeout=45) as reponse:
            donnees = json.loads(reponse.read().decode("utf-8"))

        lot = donnees.get("results") or []
        resultats.extend(item for item in lot if isinstance(item, dict))

        total = int(donnees.get("total_count") or len(resultats))
        if not lot or len(resultats) >= total:
            break
        offset += len(lot)

    return resultats


def normaliser_ids(valeur: Any) -> list[str]:
    if valeur is None:
        return []
    if isinstance(valeur, str):
        try:
            decode = json.loads(valeur)
        except json.JSONDecodeError:
            return [valeur]
        return normaliser_ids(decode)
    if isinstance(valeur, list):
        return [
            texte
            for item in valeur
            if (texte := nettoyer(item))
        ]
    return []


def resoudre(
    resultats: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    locaux = charger_index(DOSSIER_LOCAL, "dila_local_id")
    roae = charger_index(DOSSIER_ROAE, "dila_id")
    sortie = []

    for item in resultats:
        organismes = []
        for identifiant in normaliser_ids(item.get("id_service_local")):
            entite = locaux.get(identifiant) or roae.get(identifiant)
            organismes.append(
                {
                    "identifiant_dila": identifiant,
                    "resolu": entite is not None,
                    "entite_id": entite.get("id") if entite else None,
                    "nom": entite.get("nom_officiel") if entite else None,
                    "type_institutionnel": entite.get("type_institutionnel")
                    if entite
                    else None,
                }
            )

        sortie.append(
            {
                "code_insee_commune": item.get("code_insee_commune"),
                "nom_commune": item.get("nom_commune"),
                "code_type_service_local": item.get("code_type_service_local"),
                "organismes": organismes,
            }
        )

    return sortie


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Interroge la compétence géographique officielle des services locaux "
            "et résout les identifiants vers le graphe FRONTIÈRE."
        )
    )
    parser.add_argument("--commune", help="Code Insee de commune, par exemple 75056.")
    parser.add_argument("--type", dest="type_service", help="Code de type, par exemple mairie.")
    args = parser.parse_args()

    resultats = interroger(args.commune, args.type_service)
    sortie = resoudre(resultats)
    print(json.dumps(sortie, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
