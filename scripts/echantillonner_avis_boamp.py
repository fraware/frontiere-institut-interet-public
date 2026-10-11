"""Tirage stratifié documentaire BOAMP, avec dénominateurs et témoins lexicaux."""
from __future__ import annotations
import argparse
import calendar
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

try:
    from scripts.analyser_historique_boamp import (
        MOTIFS, BilanInvalide, produire, normaliser,
    )
except ModuleNotFoundError:
    from analyser_historique_boamp import (
        MOTIFS, BilanInvalide, produire, normaliser,
    )

VERSION = "echantillon-exploratoire-boamp-v2"
TEMOIN = "temoin_sans_expression_des_sept_domaines"
SEMENCE = "frontiere-exploration-2026-10-v1"


def etat_strate(valeur):
    if not isinstance(valeur, str):
        return "NON_RENSEIGNE"
    texte = valeur.strip().upper()
    return texte if texte in ("INITIAL", "RECTIFICATIF",
                              "MODIFICATION", "ANNULATION") else "AUTRE"


def mois_couverts(jours):
    presentes = set(jours)
    if not presentes or len(presentes) != len(jours):
        raise BilanInvalide("Journées absentes ou répétées.")
    for valeur in jours:
        try:
            if date.fromisoformat(valeur).isoformat() != valeur:
                raise ValueError("non canonique")
        except ValueError as erreur:
            raise BilanInvalide("Date documentaire incorrecte.") from erreur
    debut, fin = date.fromisoformat(min(jours)), date.fromisoformat(max(jours))
    y, m = debut.year, debut.month
    complets, couverture = [], []
    while (y, m) <= (fin.year, fin.month):
        mois = f"{y:04d}-{m:02d}"
        attendus = calendar.monthrange(y, m)[1]
        vus = sum(f"{mois}-{n:02d}" in presentes for n in range(1, attendus + 1))
        ok = vus == attendus
        couverture.append({"mois": mois, "jours_archives": vus,
                           "jours_calendaires": attendus, "mois_complet": ok})
        if ok:
            complets.append(mois)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return complets, couverture


def rang(semence, strate, jour, identifiant):
    message = json.dumps([semence, *strate, jour, identifiant],
                         ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def selectionner(groupes, strate, notice, quota):
    liste = groupes[strate]
    if len(liste) < quota:
        liste.append(notice)
        return
    pire = max(range(len(liste)), key=lambda k: (
        liste[k]["rang_sha256"], liste[k]["date_parution"], liste[k]["identifiant"]))
    if (notice["rang_sha256"], notice["date_parution"], notice["identifiant"]) < (
        liste[pire]["rang_sha256"], liste[pire]["date_parution"], liste[pire]["identifiant"]):
        liste[pire] = notice


def constituer(index, preuve, bilan, *, quota=4, semence=SEMENCE):
    if type(quota) is not int or not 1 <= quota <= 50:
        raise BilanInvalide("Quota par strate incorrect.")
    if not isinstance(semence, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{8,120}", semence):
        raise BilanInvalide("Semence incorrecte.")
    reference = produire(index, preuve)
    if json.loads(bilan.read_text(encoding="utf-8")) != reference:
        raise BilanInvalide("Bilan différent de l'index vérifié.")
    groupes = defaultdict(list)
    effectifs = Counter()
    suivis = set()
    nombre, exclus, multit, categories_renseignees, etats_absents = 0, 0, 0, 0, 0
    motifs = {t: [re.compile(x) for x in m] for t, m in MOTIFS.items()}
    with closing(sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)) as con:
        dates = [j for (j,) in con.execute("SELECT jour FROM provenance ORDER BY jour")]
        complets, couverture = mois_couverts(dates)
        retenus = set(complets)
        for jour, code, objet, acheteur, categorie, etat, lien, archive, releve in con.execute(
            "SELECT jour,identifiant,objet,acheteur,categorie,etat,avis,archive_source,releve_le "
            "FROM recherche ORDER BY jour,identifiant"
        ):
            nombre += 1
            categories_renseignees += bool(isinstance(categorie, str) and categorie.strip())
            etats_absents += etat_strate(etat) == "NON_RENSEIGNE"
            if (jour, code) in suivis:
                raise BilanInvalide("Avis dupliqué dans l'index.")
            suivis.add((jour, code))
            if not isinstance(objet, str):
                raise BilanInvalide("Objet documentaire incorrect.")
            expression = normaliser(objet)
            domaines = [theme for theme, regles in motifs.items()
                        if any(r.search(expression) for r in regles)]
            multit += len(domaines) > 1
            mois = jour[:7]
            if mois not in retenus:
                exclus += 1
                continue
            etat_documentaire = etat_strate(etat)
            for theme in domaines or [TEMOIN]:
                strate = (mois, etat_documentaire, theme)
                effectifs[strate] += 1
                selectionner(groupes, strate, {
                    "date_parution": jour, "identifiant": code,
                    "objet": objet[:500],
                    "acheteur_declare": (acheteur or "")[:200],
                    "categorie_declaree": categorie,
                    "etat_documentaire_declare": etat,
                    "lien_officiel": lien, "archive_source": archive,
                    "releve_le": releve, "themes_detectes": domaines,
                    "rang_sha256": rang(semence, strate, jour, code),
                    "besoin_scientifique_valide": False,
                    "competence_mobilisable_etablie": False,
                }, quota)
    if nombre != reference["nombre_avis"] or not complets:
        raise BilanInvalide("Couverture historique insuffisante ou incohérente.")
    resultats, references = [], set()
    for strate in sorted(effectifs):
        items = sorted(groupes[strate], key=lambda x: (
            x["rang_sha256"], x["date_parution"], x["identifiant"]))
        for x in items:
            references.add((x["date_parution"], x["identifiant"]))
        n = effectifs[strate]
        resultats.append({
            "mois": strate[0], "etat_documentaire": strate[1], "domaine": strate[2],
            "population_documentaire": n, "nombre_tire": len(items),
            "fraction_tirage": {"numerateur": len(items), "denominateur": n},
            "avis": items,
        })
    return {
        "version": VERSION,
        "revision_depot_source": reference["revision_depot"],
        "sha256_index_boamp": reference["sha256_index"],
        "semence": semence, "quota_par_strate": quota,
        "nombre_avis_examines": nombre,
        "nombre_avis_mois_incomplets_exclus": exclus,
        "nombre_avis_multithemes": multit,
        "nombre_categories_marche_renseignees": categories_renseignees,
        "nombre_categories_marche_manquantes": nombre - categories_renseignees,
        "nombre_etats_documentaires_absents": etats_absents,
        "stratification_categorie_marche_effective": False,
        "stratification_effective": ["mois_civil_complet", "etat_documentaire", "domaine_lexical"],
        "mois_complets": complets, "couverture_calendaire": couverture,
        "nombre_strates": len(resultats),
        "nombre_tirages": sum(x["nombre_tire"] for x in resultats),
        "nombre_avis_distincts": len(references),
        "strates": resultats,
        "methode": "classement_sha256_dans_mois_etat_documentaire_et_domaine",
        "selection_non_representative_de_la_demande_nationale": True,
        "temoin_ne_signifie_pas_absence_de_besoin": True,
        "chevauchements_de_domaines_conserves": True,
        "evaluation_externe_effectuee": False,
    }


def ecrire(rapport, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporaire_nom = tempfile.mkstemp(
        prefix=".echantillon-boamp-", suffix=".json", dir=destination.parent,
    )
    os.close(fd)
    temporaire = Path(temporaire_nom)
    try:
        temporaire.write_text(
            json.dumps(rapport, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporaire, destination)
    finally:
        temporaire.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--preuve-index", required=True, type=Path)
    parser.add_argument("--bilan", required=True, type=Path)
    parser.add_argument("--sortie", required=True, type=Path)
    parser.add_argument("--quota", type=int, default=4)
    parser.add_argument("--semence", default=SEMENCE)
    arguments = parser.parse_args()
    try:
        rapport = constituer(
            arguments.index, arguments.preuve_index, arguments.bilan,
            quota=arguments.quota, semence=arguments.semence,
        )
        ecrire(rapport, arguments.sortie)
        print(json.dumps({
            "version": VERSION,
            "mois_complets": len(rapport["mois_complets"]),
            "strates": rapport["nombre_strates"],
            "tirages": rapport["nombre_tirages"],
            "avis_distincts": rapport["nombre_avis_distincts"],
            "exclus_mois_incomplets":
                rapport["nombre_avis_mois_incomplets_exclus"],
            "sortie": str(arguments.sortie),
        }, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as erreur:
        parser.exit(1, f"Échantillonnage BOAMP interrompu : {erreur}\n")


if __name__ == "__main__":
    main()
