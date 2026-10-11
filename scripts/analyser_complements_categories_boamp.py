"""Mesurer la couverture des catégories BOAMP réobservées et datées.

Comparer les références initiales au complément sans réécrire le premier
relevé. Les catégories sont des états connus à la date de relecture.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile

try:
    from scripts.analyser_historique_boamp import produire, BilanInvalide
    from scripts.completer_categories_boamp import (
        verifier_complement, chemins,
    )
except ModuleNotFoundError:
    from analyser_historique_boamp import produire, BilanInvalide
    from completer_categories_boamp import verifier_complement, chemins

VERSION = "qualite-categories-complements-v1"


def analyser(index: Path, preuve: Path, base: Path) -> dict:
    original = produire(index, preuve)
    with closing(sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)) as conn:
        jours = {
            jour: nb for jour, nb in conn.execute(
                "SELECT jour,nombre_initial FROM provenance ORDER BY jour"
            )
        }
        total_index = conn.execute("SELECT COUNT(*) FROM recherche").fetchone()[0]
        categories_index = conn.execute(
            "SELECT COUNT(*) FROM recherche "
            "WHERE categorie IN ('SERVICES','FOURNITURES','TRAVAUX')"
        ).fetchone()[0]
        categories_autres = conn.execute(
            "SELECT COUNT(*) FROM recherche WHERE categorie IS NOT NULL "
            "AND categorie NOT IN ('SERVICES','FOURNITURES','TRAVAUX')"
        ).fetchone()[0]
    if len(jours) != original["couverture"]["jours_archives"] or total_index != original["nombre_avis"]:
        raise BilanInvalide("Index source ou effectifs de journées incohérents.")
    racine = base / "categories_boamp"
    toutes_fiches = sorted(racine.glob("20??/??/20??-??-??.json")) if racine.exists() else []
    tous_gzip = sorted(racine.glob("20??/??/20??-??-??.jsonl.gz")) if racine.exists() else []
    noms = {p.stem for p in toutes_fiches}
    noms_archive = {p.name[:-9] for p in tous_gzip}
    if len(noms) != len(toutes_fiches) or noms != noms_archive:
        raise BilanInvalide("Compléments sans fiche, sans archive ou dates répétées.")
    if not noms <= set(jours):
        raise BilanInvalide("Complément sans archive initiale correspondante.")
    colonnes = defaultdict(Counter)
    couvertes = 0
    categories = 0
    absents = 0
    ajoutes = 0
    dates_recontrole = set()
    for fiche in toutes_fiches:
        jour = fiche.stem
        initial = base / "historique_boamp" / jour[:4] / jour[5:7] / (jour + ".json")
        if not initial.is_file():
            raise BilanInvalide("Relevé BOAMP initial manquant.")
        constat = verifier_complement(base, initial)
        nb = constat["nombre_identifiants_initiaux"]
        if nb != jours[jour]:
            raise BilanInvalide("Dénominateur de complément divergent de l'index.")
        n_cat = constat["categories_renseignees_pour_identifiants_initiaux"]
        n_abs = constat["nombre_identifiants_absents_depuis_initial"]
        n_ajout = constat["nombre_identifiants_ajoutes_depuis_initial"]
        couvertes += nb
        categories += n_cat
        absents += n_abs
        ajoutes += n_ajout
        dates_recontrole.add(constat["controle_le"])
        mois = jour[:7]
        colonnes[mois]["jours_avec_complement"] += 1
        colonnes[mois]["identifiants_initiaux_couverts"] += nb
        colonnes[mois]["categories_retrouvees_lors_du_recontrole"] += n_cat
        colonnes[mois]["identifiants_absents_lors_du_recontrole"] += n_abs
        colonnes[mois]["nouveaux_identifiants_lors_du_recontrole"] += n_ajout
    par_mois = []
    for mois in sorted({j[:7] for j in jours}):
        denom = sum(n for j, n in jours.items() if j[:7] == mois)
        count = colonnes[mois]
        par_mois.append({
            "mois": mois,
            "jours_archives_initiaux": sum(j.startswith(mois) for j in jours),
            "avis_initiaux_archives": denom,
            "jours_avec_complement": count["jours_avec_complement"],
            "identifiants_initiaux_couverts": count["identifiants_initiaux_couverts"],
            "categories_retrouvees_lors_du_recontrole":
                count["categories_retrouvees_lors_du_recontrole"],
            "identifiants_absents_lors_du_recontrole":
                count["identifiants_absents_lors_du_recontrole"],
            "nouveaux_identifiants_lors_du_recontrole":
                count["nouveaux_identifiants_lors_du_recontrole"],
            "couverture_des_identifiants_archives": (
                round(count["identifiants_initiaux_couverts"] / denom, 6)
                if denom else None
            ),
        })
    return {
        "version": VERSION,
        "revision_depot_source": original["revision_depot"],
        "sha256_index_boamp": original["sha256_index"],
        "jours_archives_au_total": len(jours),
        "avis_de_l_index": total_index,
        "categories_du_dernier_etat_BOAMP_deja_dans_index": categories_index,
        "categories_non_canoniques_deja_dans_index": categories_autres,
        "jours_avec_complements_verifies": len(toutes_fiches),
        "identifiants_initiaux_couverts": couvertes,
        "identifiants_initiaux_sans_complement": sum(jours.values()) - couvertes,
        "categories_retrouvees_lors_des_recontroles": categories,
        "categories_non_retrouvees_parmi_identifiants_couverts": couvertes - categories,
        "identifiants_absents_au_recontrole": absents,
        "identifiants_nouveaux_au_recontrole": ajoutes,
        "nombre_instants_de_controle_distincts": len(dates_recontrole),
        "mesures_par_mois": par_mois,
        "unite": "identifiant_d_avis_documentaire",
        "categorie_a_la_date_de_publication_initiale_etablie": False,
        "demande_scientifique_validee": False,
        "comparaison_causale_possible": False,
        "interpretation": (
            "Couverture d'une seconde observation officielle datée, sur les "
            "identifiants des clichés initiaux. Les nouvelles catégories sont "
            "réobservées ultérieurement ; elles ne prouvent pas une classification "
            "historique, ni le besoin d'une ressource scientifique. Les avis "
            "manquants de la seconde observation sont comptés séparément."
        ),
    }


def ecrire(donnees: dict, sortie: Path) -> None:
    sortie.parent.mkdir(parents=True, exist_ok=True)
    fd, nom = tempfile.mkstemp(prefix=".qualite-categories-", suffix=".json",
                               dir=sortie.parent)
    os.close(fd)
    temporaire = Path(nom)
    try:
        temporaire.write_text(
            json.dumps(donnees, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporaire, sortie)
    finally:
        temporaire.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", required=True, type=Path)
    p.add_argument("--preuve-index", required=True, type=Path)
    p.add_argument("--sources", type=Path, default=Path("institutionnel/besoins_publics"))
    p.add_argument("--sortie", required=True, type=Path)
    a = p.parse_args()
    try:
        rapport = analyser(a.index, a.preuve_index, a.sources)
        ecrire(rapport, a.sortie)
        print(json.dumps({
            "version": VERSION,
            "jours_verifies": rapport["jours_avec_complements_verifies"],
            "avis_initiaux_couverts": rapport["identifiants_initiaux_couverts"],
            "categories_reobservees": rapport["categories_retrouvees_lors_des_recontroles"],
            "avis_absents_recontrole": rapport["identifiants_absents_au_recontrole"],
        }, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        p.exit(1, f"Analyse qualité BOAMP interrompue : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
