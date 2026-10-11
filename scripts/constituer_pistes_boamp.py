"""Constituer une liste bornée d'avis BOAMP à examiner, sans inférence de pénurie.

Les unités sont des avis, jamais des marchés supposés uniques.
Les critères de sélection sont publiés et déterministes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

try:
    from scripts.analyser_historique_boamp import (
        MOTIFS, VERSION as VERSION_BILAN, BilanInvalide,
        normaliser, sha256,
    )
    from scripts.rechercher_historique_boamp import VERSION as VERSION_INDEX
except ModuleNotFoundError:
    from analyser_historique_boamp import (
        MOTIFS, VERSION as VERSION_BILAN, BilanInvalide,
        normaliser, sha256,
    )
    from rechercher_historique_boamp import VERSION as VERSION_INDEX

VERSION = "pistes-enquete-boamp-v1"
PLAFOND = 12
PLAFOND_ACHETEUR = 2


def constituer(index: Path, preuve: Path, bilan: Path,
               plafond: int = PLAFOND,
               plafond_acheteur: int = PLAFOND_ACHETEUR) -> dict:
    if not 1 <= plafond <= 30 or not 1 <= plafond_acheteur <= 5:
        raise BilanInvalide("Limites de sélection incorrectes.")
    if not index.is_file() or not preuve.is_file() or not bilan.is_file():
        raise BilanInvalide("Fichiers de provenance de la recherche manquants.")
    p = json.loads(preuve.read_text(encoding="utf-8"))
    b = json.loads(bilan.read_text(encoding="utf-8"))
    empreinte = sha256(index)
    if (not isinstance(p, dict) or not isinstance(b, dict)
            or p.get("version") != "publication-index-boamp-v1"
            or b.get("version") != VERSION_BILAN
            or empreinte != p.get("sha256_index")
            or empreinte != b.get("sha256_index")
            or b.get("revision_depot") != p.get("revision_depot")
            or b.get("nombre_avis") != p.get("avis_indexes")):
        raise BilanInvalide("Bilan, index et fiche de provenance incohérents.")
    themes = b.get("themes_lexicaux")
    if not isinstance(themes, dict) or set(themes) != set(MOTIFS):
        raise BilanInvalide("Périmètre lexical du bilan incorrect.")
    for nom, motifs in MOTIFS.items():
        if themes[nom].get("regles") != list(motifs):
            raise BilanInvalide("Règles lexicales différentes de celles du bilan.")
    reguliers = {nom: [re.compile(x) for x in regles] for nom, regles in MOTIFS.items()}
    listes = {nom: [] for nom in MOTIFS}
    acheteurs_par_theme = {nom: Counter() for nom in MOTIFS}
    retenus = set()
    with closing(sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)) as conn:
        version = conn.execute(
            "SELECT valeur FROM informations WHERE cle='version'"
        ).fetchone()
        if version is None or version[0] != VERSION_INDEX:
            raise BilanInvalide("Version de l'index incorrecte.")
        for (jour, identifiant, objet, acheteur, url, archive, observe_le) in conn.execute(
            "SELECT jour, identifiant, objet, acheteur, avis, archive_source, releve_le "
            "FROM recherche ORDER BY jour DESC, identifiant ASC"
        ):
            if not isinstance(objet, str) or not isinstance(identifiant, str):
                raise BilanInvalide("Champs d'avis inattendus.")
            texte = normaliser(objet)
            nom_acheteur = (acheteur or "").strip()
            cle_acheteur = normaliser(nom_acheteur) if nom_acheteur else "NON_RENSEIGNE"
            for nom, patterns in reguliers.items():
                if len(listes[nom]) >= plafond:
                    continue
                expressions = [
                    pattern.pattern for pattern in patterns if pattern.search(texte)
                ]
                if not expressions or acheteurs_par_theme[nom][cle_acheteur] >= plafond_acheteur:
                    continue
                cle = (jour, identifiant, nom)
                if cle in retenus:
                    continue
                listes[nom].append({
                    "date_parution": jour,
                    "identifiant": identifiant,
                    "objet": objet[:400],
                    "acheteur_declare": nom_acheteur[:200],
                    "lien_officiel": url,
                    "archive_verifiee": archive,
                    "releve_le": observe_le,
                    "regles_correspondantes": expressions,
                    "besoin_scientifique_valide": False,
                    "disponibilite_competences_etablie": False,
                    "decision_institutionnelle_etablie": False,
                })
                acheteurs_par_theme[nom][cle_acheteur] += 1
                retenus.add(cle)
    return {
        "version": VERSION,
        "revision_depot": p["revision_depot"],
        "sha256_index": empreinte,
        "nombre_avis_examines": b["nombre_avis"],
        "methode": "dates_descendantes_puis_identifiants_croissants",
        "limite_par_theme": plafond,
        "limite_par_acheteur_normalise_et_theme": plafond_acheteur,
        "pistes": {
            nom: {
                "total_correspondances_dans_bilan": themes[nom]["avis"],
                "nombre_pistes": len(listes[nom]),
                "pistes": listes[nom],
            } for nom in MOTIFS
        },
        "selection_non_representative": True,
        "aucune_validation_de_besoin": True,
        "controle_complementaire_attendu": (
            "Vérifier chaque annonce officielle, l'identité de l'acheteur, "
            "les compétences existantes, la chronologie et les mécanismes "
            "de mobilisation avant d'ouvrir un épisode empirique."
        ),
    }


def ecrire(donnees: dict, cible: Path) -> None:
    cible.parent.mkdir(parents=True, exist_ok=True)
    fd, nom = tempfile.mkstemp(prefix=".pistes-boamp-", suffix=".json",
                               dir=cible.parent)
    os.close(fd)
    temp = Path(nom)
    try:
        temp.write_text(
            json.dumps(donnees, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temp, cible)
    finally:
        temp.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--preuve-index", required=True, type=Path)
    parser.add_argument("--bilan", required=True, type=Path)
    parser.add_argument("--sortie", required=True, type=Path)
    parser.add_argument("--limite", type=int, default=PLAFOND)
    args = parser.parse_args()
    try:
        resultat = constituer(args.index, args.preuve_index, args.bilan, args.limite)
        ecrire(resultat, args.sortie)
        print(json.dumps({
            "version": VERSION,
            "nombre_pistes": sum(x["nombre_pistes"] for x in resultat["pistes"].values()),
            "par_theme": {k: x["nombre_pistes"] for k, x in resultat["pistes"].items()},
            "sortie": str(args.sortie),
        }, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as erreur:
        parser.exit(1, f"Sélection BOAMP interrompue : {type(erreur).__name__}: {erreur}\n")


if __name__ == "__main__":
    main()
