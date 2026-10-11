"""Rapprocher des pistes BOAMP et des descriptions officielles de capacités publiques.

Rapprochement documentaire strict, non causal : les correspondances sur un avis
ou sur le nom d'un organisme ne prouvent ni besoin en compétences, ni
disponibilité, ni lien contractuel entre acheteur et organisme trouvé.
Aucun service distant ni modèle probabiliste.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

try:
    from scripts.analyser_historique_boamp import (
        BilanInvalide, MOTIFS, normaliser as normaliser_avis,
        produire as verifier_bilan,
    )
    from scripts.constituer_pistes_boamp import constituer
    from scripts.rechercher_capacites_institutionnelles import (
        ouvrir_index, chercher, verifier_sources, normaliser as mots_organisme,
    )
except ModuleNotFoundError:
    from analyser_historique_boamp import (
        BilanInvalide, MOTIFS, normaliser as normaliser_avis,
        produire as verifier_bilan,
    )
    from constituer_pistes_boamp import constituer
    from rechercher_capacites_institutionnelles import (
        ouvrir_index, chercher, verifier_sources, normaliser as mots_organisme,
    )

VERSION = "croisement-avis-capacites-v3"
RESTITUTION_MOTEUR = 500
MAX_PISTES_PAR_THEME = 12
MAX_RESULTATS_PAR_CLASSE = 3
CLASSES = (
    ("capacite_publiee", "capacites_json", "capacite_publiee"),
    ("mission_publiee", "missions_json", "mission_publiee"),
    ("domaine_scientifique_publie", "domaines_json", "domaine_scientifique_publie"),
    ("nom_seul", "nom", "nom_uniquement"),
)
COLONNES = {
    "correspondances_aux_missions_ou_capacites_publiees",
    "correspondances_aux_domaines_scientifiques_publies",
    "correspondances_de_nom_uniquement",
}


def contient_expression(texte: str, expression: str) -> bool:
    """Correspondance contiguë de mots normalisés, jamais simple recouvrement OR."""
    if not isinstance(texte, str):
        return False
    attendus = mots_organisme(expression)
    presents = mots_organisme(texte)
    if not attendus or len(attendus) > len(presents):
        return False
    n = len(attendus)
    return any(presents[i:i + n] == attendus
               for i in range(len(presents) - n + 1))


def expressions_avis(avis: dict, theme: str) -> list[str]:
    """Retenir les seules expressions présentes dans l'objet, selon les règles gelées."""
    objet = avis.get("objet")
    motifs = avis.get("regles_correspondantes")
    if (not isinstance(objet, str) or not isinstance(motifs, list)
            or theme not in MOTIFS or not set(motifs) <= set(MOTIFS[theme])):
        raise BilanInvalide("Piste documentaire ou expressions annoncées incohérentes.")
    texte = normaliser_avis(objet)
    resultats = []
    for motif in motifs:
        trouve = re.search(motif, texte)
        if trouve is None:
            raise BilanInvalide("Expression de l'avis non retrouvée dans son objet.")
        expression = trouve.group(0)
        if expression not in resultats:
            resultats.append(expression)
    if not resultats:
        raise BilanInvalide("Piste sans expression documentée.")
    return resultats


def preuves_exactes(db: sqlite3.Connection, identifiant: str, expression: str) -> list[dict]:
    """Retrouver l'expression entière dans un passage publié, non dans un titre seul."""
    ligne = db.execute(
        "SELECT nom, capacites_json, missions_json, domaines_json "
        "FROM organismes WHERE identifiant = ?", (identifiant,),
    ).fetchone()
    if ligne is None:
        raise BilanInvalide("Organisme renvoyé sans notice institutionnelle.")
    resultat = []
    for niveau, colonne, _ in CLASSES[:3]:
        textes = json.loads(ligne[colonne])
        for passage in textes:
            if (isinstance(passage, dict)
                    and isinstance(passage.get("texte"), str)
                    and isinstance(passage.get("source_id"), str)
                    and passage["source_id"].strip()
                    and contient_expression(passage["texte"], expression)):
                resultat.append({
                    "niveau": niveau,
                    "expression": expression,
                    "texte_publie": passage["texte"][:350],
                    "source_id": passage["source_id"],
                    "sha256_passage_complet": hashlib.sha256(json.dumps([passage["source_id"], passage["texte"]], ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
                })
    if not resultat and contient_expression(ligne["nom"], expression):
        resultat.append({
            "niveau": "nom_seul", "expression": expression,
            "texte_publie": ligne["nom"][:350],
            "source_id": None, "sha256_passage_complet": None,
        })
    return resultat


def chercher_expressions_exactes(
    db: sqlite3.Connection, expression: str, *, plafond: int = RESTITUTION_MOTEUR,
) -> dict:
    """Interroger les quatre champs par expression FTS5 entière.

    Le nombre total de résultats demeure inconnu lorsqu'un champ atteint le
    plafond. On conserve une borne inférieure et une indication explicite.
    """
    if type(plafond) is not int or not 1 <= plafond <= 2000:
        raise BilanInvalide("Plafond de candidats incorrect.")
    mots = mots_organisme(expression)
    if not mots or len(mots) > 10:
        raise BilanInvalide("Expression normalisée invalide.")
    # La syntaxe FTS est entièrement produite à partir des jetons normalisés.
    phrase = " ".join(mots)
    candidats = {}
    effectifs_par_champ = {}
    tronques = []
    for colonne in ("capacite_index", "mission_index", "domaine_index", "nom_index"):
        requete = f'{colonne} : "{phrase}"'
        lignes = db.execute(
            "SELECT o.identifiant, o.nom, o.famille, o.observe_le, o.fichier, "
            "o.sources_json FROM termes AS t "
            "JOIN organismes AS o ON o.numero = t.rowid "
            "WHERE termes MATCH ? AND o.etat = 'ACTIF' "
            "ORDER BY o.identifiant LIMIT ?",
            (requete, plafond + 1),
        ).fetchall()
        effectifs_par_champ[colonne] = min(len(lignes), plafond)
        if len(lignes) > plafond:
            tronques.append(colonne)
        for row in lignes[:plafond]:
            code = row["identifiant"]
            if code not in candidats:
                candidats[code] = {
                    "identifiant": code,
                    "nom": row["nom"],
                    "famille": row["famille"],
                    "observe_le": row["observe_le"],
                    "fichier_indexe": row["fichier"],
                    "provenance_notice": json.loads(row["sources_json"]),
                }
    return {
        "candidats": [candidats[k] for k in sorted(candidats)],
        "candidats_examines": len(candidats),
        "effectifs_par_champ_bornes": effectifs_par_champ,
        "champs_tronques": tronques,
        "methode": "expression_entiere_par_champ_fts5",
    }


def croiser(index_boamp: Path, preuve: Path, bilan: Path,
            index_organismes: Path, entites: Path,
            limite: int = MAX_RESULTATS_PAR_CLASSE) -> dict:
    if type(limite) is not int or not 1 <= limite <= 10:
        raise BilanInvalide("Nombre maximal de résultats par classe incorrect.")
    # Reconstituer et vérifier le bilan avant d'utiliser une liste de pistes.
    attendu = verifier_bilan(index_boamp, preuve)
    etabli = json.loads(bilan.read_text(encoding="utf-8"))
    if etabli != attendu:
        raise BilanInvalide("Bilan documentaire non reproductible pour l'index fourni.")
    selection = constituer(index_boamp, preuve, bilan,
                           plafond=MAX_PISTES_PAR_THEME)
    expression_memo = {}
    dossiers, n_queries = [], 0
    with closing(ouvrir_index(index_organismes)) as db:
        controle = verifier_sources(db, entites)
        if not controle["conforme"]:
            raise BilanInvalide(
                "Référentiel institutionnel modifié : reconstruire l'index avant croisement."
            )
        identite = db.execute(
            "SELECT valeur FROM informations WHERE cle='empreinte_sources'"
        ).fetchone()["valeur"]
        if not identite:
            raise BilanInvalide("Empreinte du référentiel institutionnel absente.")
        nombre_organismes = int(db.execute(
            "SELECT valeur FROM informations WHERE cle='nombre_entites'"
        ).fetchone()["valeur"])
        for theme, bloc in selection["pistes"].items():
            for avis in bloc["pistes"]:
                expressions = expressions_avis(avis, theme)
                candidats = {}
                controles = []
                tronque = False
                for expression in expressions:
                    if expression not in expression_memo:
                        expression_memo[expression] = chercher_expressions_exactes(
                            db, expression,
                        )
                        n_queries += 1
                    resultat = expression_memo[expression]
                    coupe = bool(resultat["champs_tronques"])
                    tronque |= coupe
                    controles.append({
                        "expression": expression,
                        "candidats_lexicaux_examines": resultat["candidats_examines"],
                        "candidats_par_champ_bornes":
                            resultat["effectifs_par_champ_bornes"],
                        "champs_tronques": resultat["champs_tronques"],
                        "recherche_tronquee": coupe,
                        "methode": resultat["methode"],
                    })
                    for ref in resultat["candidats"]:
                        preuves = preuves_exactes(db, ref["identifiant"], expression)
                        if not preuves:
                            continue
                        ancien = candidats.get(ref["identifiant"])
                        if ancien is None:
                            candidats[ref["identifiant"]] = {
                                "identifiant": ref["identifiant"],
                                "nom": ref["nom"],
                                "famille": ref["famille"],
                                "observe_le": ref["observe_le"],
                                "fichier_indexe": ref["fichier_indexe"],
                                "provenance_notice": ref["provenance_notice"],
                                "passages_justificatifs": [],
                                "disponibilite": "INCONNUE",
                                "mobilisabilite": "NON_ETABLIE",
                            }
                            ancien = candidats[ref["identifiant"]]
                        deja = {(p["niveau"], p["expression"], p["texte_publie"], p["source_id"])
                                for p in ancien["passages_justificatifs"]}
                        for passage in preuves:
                            signature = (passage["niveau"], passage["expression"],
                                         passage["texte_publie"], passage["source_id"])
                            if signature not in deja:
                                ancien["passages_justificatifs"].append(passage)
                                deja.add(signature)
                groupes = {x[0]: [] for x in CLASSES}
                priorites = {x[0]: n for n, x in enumerate(CLASSES)}
                for ressource in candidats.values():
                    passages = ressource["passages_justificatifs"]
                    passages.sort(key=lambda p: (priorites[p["niveau"]], p["expression"],
                                                 p["texte_publie"]))
                    niveau = passages[0]["niveau"]
                    ressource["niveau_documentaire"] = niveau
                    groupes[niveau].append(ressource)
                for niveau in groupes:
                    groupes[niveau].sort(key=lambda v: (v["nom"].casefold(), v["identifiant"]))
                limites = {k: len(v) > limite for k, v in groupes.items()}
                dossiers.append({
                    "theme": theme,
                    "date_parution": avis["date_parution"],
                    "identifiant_avis": avis["identifiant"],
                    "objet": avis["objet"],
                    "acheteur_declare": avis["acheteur_declare"],
                    "lien_avis": avis["lien_officiel"],
                    "archive_source_avis": avis["archive_verifiee"],
                    "releve_avis_le": avis["releve_le"],
                    "expressions_extraites": expressions,
                    "controles_recherche": controles,
                    "recherche_tronquee": tronque,
                    "effectifs_retrouves_avant_restitution": {
                        k: len(v) for k, v in groupes.items()
                    },
                    "groupes": {k: v[:limite] for k, v in groupes.items()},
                    "groupes_tronques": limites,
                    "besoin_scientifique_valide": False,
                    "capacite_operationnelle_verifiee": False,
                    "disponibilite_etablie": False,
                    "lien_contractuel_avec_acheteur_etabli": False,
                    "qualification_humaine_effectuee": False,
                })
    compteurs = Counter(d["theme"] for d in dossiers)
    avec_mission = sum(bool(d["groupes"]["capacite_publiee"]
                          or d["groupes"]["mission_publiee"]) for d in dossiers)
    avec_domaine = sum(bool(d["groupes"]["domaine_scientifique_publie"]) for d in dossiers)
    avec_nom = sum(bool(d["groupes"]["nom_seul"]) for d in dossiers)
    return {
        "version": VERSION,
        "revision_depot_source": selection["revision_depot"],
        "sha256_index_boamp": selection["sha256_index"],
        "empreinte_sha256_referentiel": identite,
        "nombre_avis_dans_corpus": selection["nombre_avis_examines"],
        "nombre_organismes_dans_index": nombre_organismes,
        "nombre_pistes": len(dossiers),
        "nombre_requetes_distinctes": n_queries,
        "pistes_par_theme": dict(sorted(compteurs.items())),
        "pistes_avec_mission_ou_capacite_documentaire": avec_mission,
        "pistes_avec_domaine_scientifique_documentaire": avec_domaine,
        "pistes_avec_correspondance_nominale": avec_nom,
        "pistes_sans_resultat_dans_les_limites": sum(
            not any(d["groupes"].values()) for d in dossiers
        ),
        "limite_candidats_par_champ_et_expression": RESTITUTION_MOTEUR,
        "methode_recherche": "expression_entiere_par_champ_fts5",
        "limite_restitution_par_classe_et_piste": limite,
        "selection_non_representative": True,
        "aucune_preuve_d_insuffisance_de_competences": True,
        "aucune_preuve_de_disponibilite": True,
        "interpretation": (
            "Rapprochement strict d'expressions d'avis avec des passages publiés "
            "de notices institutionnelles. Aucun lien entre acheteur et organisme, "
            "ni aucune compétence mobilisable, n'est établi. Une absence de résultat "
            "n'est jamais une preuve d'absence de capacité publique."
        ),
        "dossiers": dossiers,
    }


def ecrire(rapport: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, nom = tempfile.mkstemp(
        prefix=".croisement-boamp-", suffix=".json", dir=destination.parent,
    )
    os.close(fd)
    temporaire = Path(nom)
    try:
        temporaire.write_text(
            json.dumps(rapport, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporaire, destination)
    finally:
        temporaire.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-boamp", required=True, type=Path)
    parser.add_argument("--preuve-index", required=True, type=Path)
    parser.add_argument("--bilan", required=True, type=Path)
    parser.add_argument("--index-institutions", required=True, type=Path)
    parser.add_argument("--entites", required=True, type=Path)
    parser.add_argument("--sortie", required=True, type=Path)
    parser.add_argument("--limite", type=int, default=MAX_RESULTATS_PAR_CLASSE)
    a = parser.parse_args()
    try:
        r = croiser(a.index_boamp, a.preuve_index, a.bilan, a.index_institutions,
                   a.entites, limite=a.limite)
        ecrire(r, a.sortie)
        print(json.dumps({
            "version": VERSION, "pistes": r["nombre_pistes"],
            "requêtes_uniques": r["nombre_requetes_distinctes"],
            "sortie": str(a.sortie),
        }, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as erreur:
        parser.exit(1, f"Croisement documentaire interrompu : {erreur}\n")


if __name__ == "__main__":
    main()
