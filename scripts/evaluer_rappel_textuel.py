"""Comparer le rappel textuel exact du moteur classique et du croisement v3."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import os
import tempfile

try:
    from scripts.analyser_historique_boamp import produire, BilanInvalide
    from scripts.constituer_pistes_boamp import constituer
    from scripts.croiser_pistes_capacites import (
        expressions_avis, preuves_exactes, chercher_expressions_exactes,
    )
    from scripts.rechercher_capacites_institutionnelles import (
        ouvrir_index, verifier_sources, chercher, normaliser,
    )
except ModuleNotFoundError:
    from analyser_historique_boamp import produire, BilanInvalide
    from constituer_pistes_boamp import constituer
    from croiser_pistes_capacites import (
        expressions_avis, preuves_exactes, chercher_expressions_exactes,
    )
    from rechercher_capacites_institutionnelles import (
        ouvrir_index, verifier_sources, chercher, normaliser,
    )

VERSION = "banc-rappel-textuel-capacites-v1"
CHAMPS = ("capacite_index", "mission_index", "domaine_index", "nom_index")
SORTIES = (
    "correspondances_aux_missions_ou_capacites_publiees",
    "correspondances_aux_domaines_scientifiques_publies",
    "correspondances_de_nom_uniquement",
)


def reference_exacte(db, expression):
    tokens = normaliser(expression)
    if not tokens or len(tokens) > 10:
        raise BilanInvalide("Expression à évaluer invalide.")
    candidat_ids = set()
    phrase = " ".join(tokens)
    for champ in CHAMPS:
        for code, in db.execute(
            "SELECT o.identifiant FROM termes AS t "
            "JOIN organismes AS o ON o.numero=t.rowid "
            "WHERE termes MATCH ? AND o.etat='ACTIF'",
            (f'{champ} : "{phrase}"',),
        ):
            candidat_ids.add(code)
    resultat = sorted(code for code in candidat_ids if preuves_exactes(
        db, code, expression,
    ))
    digest = hashlib.sha256(
        json.dumps(resultat, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return set(resultat), digest


def ids_verifies(db, candidats, expression):
    return {
        item["identifiant"] for item in candidats
        if preuves_exactes(db, item["identifiant"], expression)
    }


def comparer(index_boamp, preuve, bilan, index_institutions, entites):
    b = produire(index_boamp, preuve)
    if json.loads(bilan.read_text(encoding="utf-8")) != b:
        raise BilanInvalide("Bilan BOAMP non reproductible.")
    pistes = constituer(index_boamp, preuve, bilan)
    expressions = {
        terme for theme, bloc in pistes["pistes"].items()
        for avis in bloc["pistes"]
        for terme in expressions_avis(avis, theme)
    }
    if not expressions:
        raise BilanInvalide("Aucune expression technique à comparer.")
    lignes, sommes = [], {"reference": 0, "ancien": 0, "nouveau": 0}
    with closing(ouvrir_index(index_institutions)) as db:
        validation = verifier_sources(db, entites)
        if not validation["conforme"]:
            raise BilanInvalide("Fichiers institutionnels modifiés depuis l'index.")
        identite = db.execute(
            "SELECT valeur FROM informations WHERE cle='empreinte_sources'"
        ).fetchone()["valeur"]
        for expression in sorted(expressions):
            oracle, digest = reference_exacte(db, expression)
            ancienne = chercher(db, expression, limite=25)
            avant = ids_verifies(
                db, [item for nom in SORTIES for item in ancienne[nom]], expression,
            )
            nouvelle = chercher_expressions_exactes(db, expression, plafond=500)
            apres = ids_verifies(db, nouvelle["candidats"], expression)
            if not avant <= oracle or not apres <= oracle:
                raise BilanInvalide("Résultat hors du recensement textuel de référence.")
            manquants_nouveau = oracle - apres
            if manquants_nouveau and not nouvelle["champs_tronques"]:
                raise BilanInvalide("Omission inexpliquée du moteur de recherche exact.")
            for key, n in (
                ("reference", len(oracle)), ("ancien", len(avant)),
                ("nouveau", len(apres)),
            ):
                sommes[key] += n
            lignes.append({
                "expression": expression,
                "reference_textuelle": len(oracle),
                "sha256_identifiants_reference": digest,
                "ancien_trouves": len(avant),
                "nouveau_trouves": len(apres),
                "ancien_manques": len(oracle - avant),
                "nouveau_manques": len(manquants_nouveau),
                "nouvelle_recherche_tronquee": bool(nouvelle["champs_tronques"]),
                "champs_tronques": nouvelle["champs_tronques"],
                "rappel_ancien": len(avant) / len(oracle) if oracle else None,
                "rappel_nouveau": len(apres) / len(oracle) if oracle else None,
                "reference_scientifique_humaine": False,
            })
    return {
        "version": VERSION,
        "revision_depot_source": b["revision_depot"],
        "sha256_index_boamp": b["sha256_index"],
        "empreinte_referentiel_institutionnel": identite,
        "nombre_expressions_distinctes": len(expressions),
        "sommes_non_dedoublonnees_entre_expressions": sommes,
        "rappel_global_ancien_sur_occurrences_textuelles": (
            sommes["ancien"] / sommes["reference"] if sommes["reference"] else None
        ),
        "rappel_global_nouveau_sur_occurrences_textuelles": (
            sommes["nouveau"] / sommes["reference"] if sommes["reference"] else None
        ),
        "resultats": lignes,
        "reference": "recensement_exhaustif_des_expressions_exactes_dans_le_referentiel_indexe",
        "mesure_de_pertinence_scientifique": False,
        "mesure_de_disponibilite": False,
        "interpretation": (
            "Le recensement vérifie des correspondances textuelles exactes "
            "dans la même source. Les identifiants peuvent se répéter entre "
            "expressions. Ce rappel technique ne mesure ni la pertinence "
            "des organismes ni leur disponibilité ni la valeur d'une méthode "
            "sur des besoins réels."
        ),
    }


