"""Relever seulement l'en-tête du fichier d'offres publiques publié par la DGAFP."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "institutionnel" / "besoins_publics"
CATALOGUE = DOSSIER / "ressources_emplois_publics.json"
SCHEMA = DOSSIER / "schema_emplois_publics.json"
ETAT = DOSSIER / "etat_schema_emplois_publics.json"
MAXIMUM = 65_536


class ErreurColonnes(ValueError):
    """En-tête insuffisant ou fichier inaccessible dans les limites prévues."""


def choisir(ressources: list[dict]) -> dict:
    listes = [x for x in ressources if isinstance(x, dict) and x.get("format") == "csv"
              and isinstance(x.get("url"), str) and x["url"].startswith(
                  "https://static.data.gouv.fr/resources/")]
    if not listes:
        raise ErreurColonnes("Aucun fichier CSV de la plateforme officielle n'est référencé.")
    return max(listes, key=lambda x: (x.get("modifie_le") or "", x.get("id") or ""))


def detecter_entete(brut: bytes) -> dict:
    """Ne lire aucune ligne individuelle dans le résultat public."""
    if not brut or len(brut) > MAXIMUM:
        raise ErreurColonnes("En-tête vide ou trop volumineux.")
    try:
        texte = brut.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            texte = brut.decode("windows-1252")
        except UnicodeDecodeError as e:
            raise ErreurColonnes("Encodage incompatible.") from e
    if not texte or "\n" not in texte:
        raise ErreurColonnes("Première ligne incomplète.")
    lignes = texte.splitlines(keepends=True)
    choix = []
    for sep in (";", ",", "\t", "|"):
        try:
            champs = next(csv.reader(io.StringIO(lignes[0]), delimiter=sep))
        except (csv.Error, StopIteration):
            continue
        if 2 <= len(champs) <= 300 and all(ch.strip() for ch in champs):
            choix.append((len(champs), sep, champs))
    if not choix:
        raise ErreurColonnes("Séparateur et colonnes non identifiés.")
    _, sep, entetes = max(choix, key=lambda x: x[0])
    if len(set(x.casefold().strip() for x in entetes)) != len(entetes):
        raise ErreurColonnes("Colonnes de noms répétés.")
    return {
        "separateur": {";": "point-virgule", ",": "virgule", "\t": "tabulation", "|": "barre"}[sep],
        "colonnes": [x.strip()[:160] for x in entetes],
        "nombre_colonnes": len(entetes),
        "lignes_individuelles_copiees": 0,
    }


def lire_en_tete(url: str) -> dict:
    if not url.startswith("https://static.data.gouv.fr/resources/"):
        raise ErreurColonnes("Adresse du fichier non autorisée.")
    requete = Request(url, headers={
        "User-Agent": "FRONTIERE-inventaire-structure-offres/1.0",
        "Range": f"bytes=0-{MAXIMUM-1}",
    })
    with urlopen(requete, timeout=40) as response:
        if response.status != 206:
            raise ErreurColonnes("Le serveur ne prend pas en charge les lectures partielles.")
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "static.data.gouv.fr":
            raise ErreurColonnes("Source redirigée hors de la plateforme officielle.")
        donnees = response.read(MAXIMUM + 1)
    return detecter_entete(donnees)


def enregistrer(chemin: Path, valeur: dict) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    t = chemin.with_suffix(".json.tmp")
    t.write_text(json.dumps(valeur, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                 encoding="utf-8")
    t.replace(chemin)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dossier", type=Path, default=DOSSIER)
    a = p.parse_args()
    try:
        source = json.loads((a.dossier / CATALOGUE.name).read_text(encoding="utf-8"))
        fichier = choisir(source["ressources"])
        result = lire_en_tete(fichier["url"])
        instant = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        resultat = dict(result, source_id=fichier["id"], titre_fichier=fichier["titre"],
                        date_modification_declaree=fichier.get("modifie_le"),
                        source="Les offres diffusées sur Choisir le Service Public")
        enregistrer(a.dossier / SCHEMA.name, resultat)
        etat = {"controle_le": instant, "source_id": fichier["id"],
                "nombre_colonnes": result["nombre_colonnes"],
                "fichier_entier_telecharge": False}
        enregistrer(a.dossier / ETAT.name, etat)
        print(json.dumps(etat, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as err:
        p.exit(1, f"Observation de structure interrompue : {type(err).__name__}: {err}\n")


if __name__ == "__main__":
    main()
