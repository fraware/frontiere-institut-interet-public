"""Contre-vérifier les tirages BOAMP par une seconde procédure intégrale.

Le contrôle relit les avis de l'index attesté, reconstruit indépendamment
les dénominateurs et les premiers rangs de chaque strate, vérifie les avis
publiés et mesure la sensibilité à des semences alternatives.
"""
from __future__ import annotations

import argparse
import calendar
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sqlite3

try:
    from scripts.analyser_historique_boamp import MOTIFS, normaliser
except ModuleNotFoundError:
    from analyser_historique_boamp import MOTIFS, normaliser

VERSION = "contre-verification-tirage-boamp-v1"
VERSION_TIRAGE = "echantillon-exploratoire-boamp-v2"
TEMOIN = "temoin_sans_expression_des_sept_domaines"
SEMENCES_REPLICATION = ("frontiere-contrepreuve-alpha-2026", "frontiere-contrepreuve-beta-2026")
ETATS = {"INITIAL", "RECTIFICATIF", "MODIFICATION", "ANNULATION"}


class ControleInvalide(ValueError):
    """La sélection publiée ne correspond pas aux avis de référence."""


def empreinte(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def empreinte_tirage(semence: str, cle: tuple[str, str, str],
                    jour: str, identifiant: str) -> str:
    # Reconstruction distincte : on recalcule les octets de la clé, sans
    # réutiliser le code de tri du générateur d'échantillon.
    elements = [semence, cle[0], cle[1], cle[2], jour, identifiant]
    octets = json.dumps(
        elements, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(octets).hexdigest()


def meilleurs(stock: dict, cle: tuple, entree: tuple, quota: int) -> None:
    # Tri intégral des k+1 candidats par strate ; algorithme volontairement
    # distinct de celui du tirage d'origine (élimination du pire rang).
    stock[cle].append(entree)
    stock[cle].sort()
    if len(stock[cle]) > quota:
        stock[cle].pop()


def mois_civils_attestes(jours: list[str]) -> tuple[list[str], list[dict]]:
    uniques = set(jours)
    if not jours or len(uniques) != len(jours):
        raise ControleInvalide("Inventaire journalier vide ou dupliqué.")
    try:
        dates = [date.fromisoformat(v) for v in jours]
    except (ValueError, TypeError) as erreur:
        raise ControleInvalide("Date d'inventaire illisible.") from erreur
    if any(d.isoformat() != raw for d, raw in zip(dates, jours)):
        raise ControleInvalide("Date d'inventaire non canonique.")
    start, end = min(dates), max(dates)
    annee, mois = start.year, start.month
    complets, details = [], []
    while (annee, mois) <= (end.year, end.month):
        nom = f"{annee:04d}-{mois:02d}"
        total = calendar.monthrange(annee, mois)[1]
        count = sum(f"{nom}-{day:02d}" in uniques for day in range(1, total + 1))
        valide = count == total
        details.append({
            "mois": nom, "jours_archives": count,
            "jours_calendaires": total, "mois_complet": valide,
        })
        if valide:
            complets.append(nom)
        if mois == 12:
            annee, mois = annee + 1, 1
        else:
            mois += 1
    return complets, details


def classer_etat(valeur) -> str:
    if not isinstance(valeur, str):
        return "NON_RENSEIGNE"
    valeur = valeur.strip().upper()
    return valeur if valeur in ETATS else "AUTRE"


def verifier_rapports(index: Path, preuve: Path, echantillon: Path) -> dict:
    if not all(p.is_file() for p in (index, preuve, echantillon)):
        raise ControleInvalide("Fichier de contre-vérification absent.")
    source = json.loads(preuve.read_text(encoding="utf-8"))
    resultat = json.loads(echantillon.read_text(encoding="utf-8"))
    sha = empreinte(index)
    if (source.get("version") != "publication-index-boamp-v1"
            or sha != source.get("sha256_index")
            or sha != resultat.get("sha256_index_boamp")
            or source.get("revision_depot") != resultat.get("revision_depot_source")
            or resultat.get("version") != VERSION_TIRAGE
            or resultat.get("stratification_categorie_marche_effective") is not False
            or resultat.get("stratification_effective") != [
                "mois_civil_complet", "etat_documentaire", "domaine_lexical",
            ]):
        raise ControleInvalide("Provenance ou version du tirage incohérente.")
    quota = resultat.get("quota_par_strate")
    semence = resultat.get("semence")
    if type(quota) is not int or not 1 <= quota <= 50:
        raise ControleInvalide("Quota incorrect.")
    if not isinstance(semence, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{8,120}", semence):
        raise ControleInvalide("Semence incorrecte.")
    return {"source": source, "echantillon": resultat,
            "sha_index": sha, "quota": quota, "semence": semence}



def auditer(index: Path, preuve: Path, echantillon: Path) -> dict:
    p = verifier_rapports(index, preuve, echantillon)
    fichier, source = p["echantillon"], p["source"]
    quota, semence = p["quota"], p["semence"]
    regler = {nom: tuple(re.compile(x) for x in expressions)
              for nom, expressions in MOTIFS.items()}
    total = 0
    categories_renseignees = 0
    etats_absents = 0
    multithemes = 0
    hors_mois = 0
    per_strate = Counter()
    per_etat = Counter()
    per_mois = Counter()
    top = defaultdict(list)
    alternatives = {s: defaultdict(list) for s in SEMENCES_REPLICATION}
    ids = set()
    with closing(sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)) as db:
        controle = db.execute("PRAGMA integrity_check").fetchone()
        if controle != ("ok",):
            raise ControleInvalide("Index SQLite non intègre.")
        journees = [r[0] for r in db.execute("SELECT jour FROM provenance ORDER BY jour")]
        mois, couverture = mois_civils_attestes(journees)
        admissibles = set(mois)
        for jour, identifiant, objet, acheteur, categorie, etat, url, archive, releve in db.execute(
            "SELECT jour,identifiant,objet,acheteur,categorie,etat,avis,archive_source,releve_le "
            "FROM recherche ORDER BY jour,identifiant"
        ):
            total += 1
            if (jour, identifiant) in ids:
                raise ControleInvalide("Identifiant et date de notice répétés.")
            ids.add((jour, identifiant))
            if not isinstance(objet, str):
                raise ControleInvalide("Objet documentaire non textuel.")
            categories_renseignees += bool(
                isinstance(categorie, str) and categorie.strip()
            )
            classe = classer_etat(etat)
            etats_absents += classe == "NON_RENSEIGNE"
            texte = normaliser(objet)
            motifs = [name for name, rules in regler.items()
                      if any(rule.search(texte) for rule in rules)]
            multithemes += len(motifs) > 1
            if jour[:7] not in admissibles:
                hors_mois += 1
                continue
            for domaine in motifs or [TEMOIN]:
                cle = (jour[:7], classe, domaine)
                per_strate[cle] += 1
                score = empreinte_tirage(semence, cle, jour, identifiant)
                element = {
                    "date_parution": jour, "identifiant": identifiant,
                    "objet": objet[:500],
                    "acheteur_declare": (acheteur or "")[:200],
                    "categorie_declaree": categorie,
                    "etat_documentaire_declare": etat,
                    "lien_officiel": url,
                    "archive_source": archive,
                    "releve_le": releve,
                    "themes_detectes": motifs,
                    "rang_sha256": score,
                    "besoin_scientifique_valide": False,
                    "competence_mobilisable_etablie": False,
                }
                meilleurs(top, cle, (score, jour, identifiant, element), quota)
                for autre, selection in alternatives.items():
                    score_alt = empreinte_tirage(autre, cle, jour, identifiant)
                    meilleurs(selection, cle, (score_alt, jour, identifiant), quota)
    if (total != source.get("avis_indexes")
            or len(journees) != source.get("jours_indexes")
            or total != fichier.get("nombre_avis_examines")
            or hors_mois != fichier.get("nombre_avis_mois_incomplets_exclus")
            or multithemes != fichier.get("nombre_avis_multithemes")
            or categories_renseignees != fichier.get("nombre_categories_marche_renseignees")
            or total - categories_renseignees != fichier.get("nombre_categories_marche_manquantes")
            or etats_absents != fichier.get("nombre_etats_documentaires_absents")
            or fichier.get("stratification_categorie_marche_effective") is not False
            or fichier.get("stratification_effective") != [
                "mois_civil_complet", "etat_documentaire", "domaine_lexical",
            ]
            or mois != fichier.get("mois_complets")
            or couverture != fichier.get("couverture_calendaire")):
        raise ControleInvalide("Dénominateurs ou couverture du tirage incohérents.")
    attendues = []
    for cle in sorted(per_strate):
        candidats = [t[-1] for t in top[cle]]
        n = per_strate[cle]
        attendues.append({
            "mois": cle[0], "etat_documentaire": cle[1], "domaine": cle[2],
            "population_documentaire": n, "nombre_tire": len(candidats),
            "fraction_tirage": {"numerateur": len(candidats), "denominateur": n},
            "avis": candidats,
        })
        per_etat[cle[1]] += n
        per_mois[cle[0]] += n
    total_tirages = sum(x["nombre_tire"] for x in attendues)
    uniques = {(x["date_parution"], x["identifiant"])
               for strate in attendues for x in strate["avis"]}
    if (attendues != fichier.get("strates")
            or len(attendues) != fichier.get("nombre_strates")
            or total_tirages != fichier.get("nombre_tirages")
            or len(uniques) != fichier.get("nombre_avis_distincts")):
        raise ControleInvalide("Tirages, rangs ou notices différentes de la source.")
    sensibilites = []
    for semence_alt, groupes_alt in alternatives.items():
        intersections = 0
        attente = 0.0
        for cle, n in per_strate.items():
            premiers = {(x[1], x[2]) for x in top[cle]}
            autres = {(x[1], x[2]) for x in groupes_alt[cle]}
            intersections += len(premiers & autres)
            k = min(quota, n)
            attente += k * k / n
        sensibilites.append({
            "semence_alternative": semence_alt,
            "tirages_communs_observes": intersections,
            "tirages_communs_attendus_si_rangs_aleatoires_independants":
                round(attente, 3),
            "fraction_de_tirages_communs": round(intersections / total_tirages, 6),
        })
    return {
        "version": VERSION,
        "sha256_index_verifie": p["sha_index"],
        "sha256_echantillon_verifie": empreinte(echantillon),
        "revision_depot_source": source["revision_depot"],
        "nombre_avis_verifies": total,
        "nombre_journees_verifiees": len(journees),
        "mois_civils_complets": len(mois),
        "avis_exclus_mois_incomplets": hors_mois,
        "strates_integralement_rejouees": len(attendues),
        "tirages_integralement_rejoues": total_tirages,
        "avis_distincts_rejoues": len(uniques),
        "avis_multithemes_dans_corpus": multithemes,
        "categories_de_marche_absentes": total - categories_renseignees,
        "categories_de_marche_presentes": categories_renseignees,
        "distribution_documentaire_par_etat_dans_mois_complets":
            dict(sorted(per_etat.items())),
        "effectifs_documentaires_par_mois_avec_recouvrements":
            dict(sorted(per_mois.items())),
        "sensibilite_a_deux_semences": sensibilites,
        "conformite_du_tirage": True,
        "preuve_de_pertinence_operationnelle": False,
        "tirage_independant_de_la_demande_nationale": False,
        "interpretation": (
            "La reconstruction des rangs, effectifs et extraits est indépendante "
            "du code de sélection principal, mais conserve les mêmes règles "
            "lexicales publiées et la même base source. Les différences entre "
            "semences ne mesurent pas la qualité scientifique des avis. "
            "Les avis ne sont pas des marchés distincts."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--preuve-index", type=Path, required=True)
    parser.add_argument("--echantillon", type=Path, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    a = parser.parse_args()
    try:
        rapport = auditer(a.index, a.preuve_index, a.echantillon)
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        a.sortie.write_text(
            json.dumps(rapport, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "version": VERSION, "tirages": rapport["tirages_integralement_rejoues"],
            "strates": rapport["strates_integralement_rejouees"],
            "conforme": rapport["conformite_du_tirage"],
        }, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as e:
        parser.exit(1, f"Contre-vérification BOAMP interrompue : {e}\n")


if __name__ == "__main__":
    main()
