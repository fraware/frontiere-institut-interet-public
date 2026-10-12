"""Tirer un échantillon documentaire distinct des pilotes sans consulter les résultats.

Le tirage est déterministe, réparti sur des mois fixés et vérifié contre
l'empreinte de l'index. Il prépare un examen indépendant ; il ne le simule pas.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

VERSION = "tirage-independant-boamp-technique-v1"
MOIS = ("2025-08", "2025-10", "2025-12", "2026-02", "2026-04", "2026-06")
QUOTA = 6
SEMENCE = "frontiere-ecarts-marches-techniques-2026-10-12-v1"
EXCLUS = frozenset((
    "26-77392", "26-81972", "26-74896", "26-30147",
    "26-83870", "25-71164", "26-81640", "24-119544",
    "26-55633", "25-67330",
))
TERMES = (
    "radar", "algorith", "cybersecurite", "informatique", "simulation",
    "calcul intensif", "traitement du signal", "intelligence artificielle",
    "supercalcul", "telede tection".replace(" ", ""), "robotique",
    "electronique", "quantique", "genom", "science des donnees",
    "systeme d'information", "analyse scientifique", "modelisation",
    "bioinformatique", "automatisation",
)


class TirageInvalide(ValueError):
    """L'index ou un quota scientifique ne respecte pas le préenregistrement."""


def normaliser(texte):
    texte = unicodedata.normalize("NFKD", texte).casefold()
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texte).strip()


def candidat(texte):
    n = normaliser(texte)
    return any(mot in n for mot in TERMES)


def tirer(index: Path, preuve: Path):
    source = json.loads(preuve.read_text(encoding="utf-8"))
    empreinte = hashlib.sha256(index.read_bytes()).hexdigest()
    if empreinte != source.get("sha256_index"):
        raise TirageInvalide("Index différent de son manifeste SHA-256.")
    if source.get("completude_historique_etablie") is not False:
        raise TirageInvalide("Attestation de couverture historique inattendue.")
    with sqlite3.connect(f"file:{index.resolve()}?mode=ro", uri=True) as con:
        validite = con.execute("PRAGMA integrity_check").fetchone()[0]
        if validite != "ok":
            raise TirageInvalide("Contrôle d'intégrité SQLite en échec.")
        # Le choix des mois et du sous-ensemble technique précède la lecture
        # des résultats d'attribution. Ne pas consulter les champs résultat.
        lignes = con.execute(
            "SELECT jour, identifiant, objet, acheteur FROM recherche "
            "WHERE substr(jour,1,7) IN (" + ",".join("?" for _ in MOIS) + ")",
            MOIS,
        ).fetchall()
    possibles = {m: [] for m in MOIS}
    for jour, identifiant, objet, acheteur in lignes:
        if (not all(isinstance(v, str) for v in (jour, identifiant, objet, acheteur))
                or identifiant in EXCLUS or len(objet.strip()) < 20
                or not candidat(objet)):
            continue
        mois = jour[:7]
        # Une même publication ou un doublon issu d'un même titre et acheteur
        # ne crée pas deux cas d'évaluation.
        cle_serie = normaliser(acheteur) + "\0" + normaliser(objet)
        score = hashlib.sha256(
            (SEMENCE + "\0" + mois + "\0" + identifiant).encode()
        ).hexdigest()
        possibles[mois].append({
            "avis": identifiant,
            "date_parution": jour,
            "acheteur": acheteur,
            "objet": objet,
            "serie": hashlib.sha256(cle_serie.encode()).hexdigest(),
            "_score": score,
        })
    choisis, series = [], set()
    pour_mois = {}
    for mois in MOIS:
        vus = set()
        for item in sorted(possibles[mois], key=lambda i: (i["_score"], i["avis"])):
            if item["avis"] in EXCLUS or item["serie"] in series or item["serie"] in vus:
                continue
            if len(vus) >= QUOTA:
                break
            vus.add(item["serie"])
            series.add(item["serie"])
            choisis.append({k: v for k, v in item.items() if k != "_score"})
        pour_mois[mois] = len(vus)
        if len(vus) != QUOTA:
            raise TirageInvalide(
                f"Quota préenregistré impossible pour {mois} : {len(vus)}/{QUOTA}."
            )
    if len({v["avis"] for v in choisis}) != QUOTA * len(MOIS):
        raise TirageInvalide("Identifiants de contrôle dupliqués.")
    empreinte_tirage = hashlib.sha256(json.dumps(
        [i["avis"] for i in choisis], ensure_ascii=False,
        separators=(",", ":"),
    ).encode()).hexdigest()
    return {
        "version": VERSION,
        "source_index_sha256": empreinte,
        "semence_pre_enregistree": SEMENCE,
        "mois": list(MOIS),
        "quota_par_mois": QUOTA,
        "effectifs_par_mois": pour_mois,
        "nombre_cas": len(choisis),
        "sha256_identifiants_ordonnes": empreinte_tirage,
        "cas": [{
            **x,
            "resultat_de_marche_indetermine_au_tirage": True,
            "mecanisme_de_competences_non_evalue": True,
        } for x in choisis],
        "etude_independante_effectuee": False,
        "etiquettes_officielles_verifiees": False,
        "comparaison_de_methodes_effectuee": False,
        "selection_representative_de_la_france": False,
        "limitations": (
            "Échantillon technique lexical, enrichi et non représentatif. "
            "La sélection est indépendante des résultats de lot. Les classes "
            "attribué, sans offre, et indéterminé restent à coder par double "
            "lecture des sources primaires, avant toute comparaison de méthodes."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--preuve-index", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    if a.sortie.exists():
        p.exit(1, "Sortie déjà existante : ne pas écraser le tirage.\n")
    try:
        resultat = tirer(a.index, a.preuve_index)
    except (ValueError, OSError, sqlite3.DatabaseError) as exc:
        p.exit(1, f"Tirage non validé : {exc}\n")
    a.sortie.parent.mkdir(parents=True, exist_ok=True)
    with a.sortie.open("x", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps({
        "cas": resultat["nombre_cas"],
        "effectifs_par_mois": resultat["effectifs_par_mois"],
        "empreinte": resultat["sha256_identifiants_ordonnes"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
