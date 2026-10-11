"""Bilan descriptif, borné et reproductible des avis BOAMP déjà indexés.

Les thèmes sont des repérages lexicaux sur le champ « objet » d'avis publics,
sans attribution causale, preuve de pénurie ni décompte de marchés uniques.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import unicodedata

try:
    from scripts.rechercher_historique_boamp import VERSION as VERSION_INDEX
except ModuleNotFoundError:
    from rechercher_historique_boamp import VERSION as VERSION_INDEX

VERSION = "bilan-documentaire-boamp-v1"

# Expressions publiques, préenregistrées : tout ajout constitue une nouvelle
# règle de comptage ; ne pas interpréter leurs fréquences comme une demande.
MOTIFS = {
    "intelligence_artificielle": (
        r"\bintelligence artificielle\b",
        r"\bapprentissage automatique\b",
    ),
    "cybersecurite": (
        r"\bcybersecurite\b",
        r"\bsecurite informatique\b",
    ),
    "robotique": (
        r"\brobotique\b",
        r"\brobots?\b",
    ),
    "calcul_scientifique": (
        r"\bcalcul intensif\b",
        r"\bcalcul haute performance\b",
        r"\bsupercalculateur\b",
    ),
    "imagerie_et_geographie": (
        r"\bteledetection\b",
        r"\bgeomatique\b",
        r"\bimagerie satellitaire\b",
    ),
    "sciences_biologiques": (
        r"\bsequencage\b",
        r"\bgenomique\b",
        r"\bbioinformatique\b",
    ),
    "instrumentation_scientifique": (
        r"\binstrumentation scientifique\b",
        r"\bequipement de laboratoire\b",
        r"\bequipements de laboratoire\b",
    ),
}


class BilanInvalide(ValueError):
    """L'index, sa provenance ou le bilan ne satisfont pas les vérifications."""


def normaliser(texte: str) -> str:
    if not isinstance(texte, str):
        raise BilanInvalide("Texte documentaire invalide.")
    s = texte.casefold().replace("œ", "oe").replace("æ", "ae")
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as flux:
        while bloc := flux.read(1_048_576):
            h.update(bloc)
    return h.hexdigest()


def intervalles(jours: list[str]) -> dict:
    if not jours:
        raise BilanInvalide("Aucune journée indexée.")
    dates = []
    for j in jours:
        try:
            d = date.fromisoformat(j)
        except (TypeError, ValueError) as erreur:
            raise BilanInvalide("Date de parution invalide.") from erreur
        if d.isoformat() != j:
            raise BilanInvalide("Date de parution non canonique.")
        dates.append(d)
    if len(dates) != len(set(dates)):
        raise BilanInvalide("Journée dupliquée.")
    debut, fin = min(dates), max(dates)
    ecarts, courante, connus = [], debut, set(dates)
    while courante <= fin:
        if courante not in connus:
            ecarts.append(courante.isoformat())
        courante += timedelta(days=1)
    return {
        "premier_jour": debut.isoformat(),
        "dernier_jour": fin.isoformat(),
        "jours_archives": len(jours),
        "jours_calendaires_dans_intervalle": (fin - debut).days + 1,
        "jours_non_archives_dans_intervalle": len(ecarts),
        "exemples_jours_non_archives": ecarts[:20],
    }


def produire(index: Path, preuve: Path) -> dict:
    if not index.is_file() or not preuve.is_file():
        raise BilanInvalide("Index ou preuve source introuvable.")
    fiche = json.loads(preuve.read_text(encoding="utf-8"))
    if not isinstance(fiche, dict) or fiche.get("version") != "publication-index-boamp-v1":
        raise BilanInvalide("Provenance d'index non reconnue.")
    digest = sha256(index)
    if digest != fiche.get("sha256_index"):
        raise BilanInvalide("Empreinte de l'index différente de la preuve.")
    if not re.fullmatch(r"[a-f0-9]{40}", str(fiche.get("revision_depot", ""))):
        raise BilanInvalide("Révision du dépôt source absente ou incorrecte.")

    with closing(sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)) as con:
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BilanInvalide("Index SQLite incohérent.")
        version = con.execute(
            "SELECT valeur FROM informations WHERE cle = 'version'"
        ).fetchone()
        if version is None or version[0] != VERSION_INDEX:
            raise BilanInvalide("Version de l'index de recherche inattendue.")
        jours = [j for (j,) in con.execute("SELECT jour FROM provenance ORDER BY jour")]
        couverture = intervalles(jours)
        nombre = con.execute("SELECT COUNT(*) FROM recherche").fetchone()[0]
        if (couverture["jours_archives"] != fiche.get("jours_indexes")
                or nombre != fiche.get("avis_indexes")):
            raise BilanInvalide("Décomptes différents de la preuve de construction.")
        dates = [
            {"jour": j, "avis": n}
            for j, n in con.execute(
                "SELECT jour, COUNT(*) FROM recherche GROUP BY jour ORDER BY jour"
            )
        ]
        jours_par_mois = Counter(j[:7] for j in jours)
        avis_par_mois = Counter()
        for item in dates:
            avis_par_mois[item["jour"][:7]] += item["avis"]
        mois = [
            {"mois": m, "jours_archives": jours_par_mois[m],
             "avis": avis_par_mois[m]}
            for m in sorted(jours_par_mois)
        ]
        categories = [
            {"categorie": (c or "NON_RENSEIGNEE"), "avis": n}
            for c, n in con.execute(
                "SELECT categorie, COUNT(*) FROM recherche "
                "GROUP BY categorie ORDER BY COUNT(*) DESC, categorie ASC"
            )
        ]
        acheteurs = [
            {"nom_declare": nom, "avis": n}
            for nom, n in con.execute(
                "SELECT acheteur, COUNT(*) FROM recherche "
                "WHERE acheteur IS NOT NULL AND TRIM(acheteur) != '' "
                "GROUP BY acheteur ORDER BY COUNT(*) DESC, acheteur ASC LIMIT 20"
            )
        ]
        prepares = {k: [re.compile(x) for x in ps] for k, ps in MOTIFS.items()}
        themes = {k: {"avis": 0, "exemples": []} for k in MOTIFS}
        total_examines = 0
        for jour, identifiant, objet, acheteur, url in con.execute(
            "SELECT jour, identifiant, objet, acheteur, avis FROM recherche"
        ):
            total_examines += 1
            expression = normaliser(objet)
            for nom, regles in prepares.items():
                if any(r.search(expression) for r in regles):
                    indicateur = themes[nom]
                    indicateur["avis"] += 1
                    exemple = {
                        "jour": jour, "identifiant": identifiant,
                        "objet": objet[:240], "acheteur": (acheteur or "")[:180],
                        "lien_avis": url,
                    }
                    # Retenir trois exemples récents déterministes et non
                    # représentatifs ; l'ensemble des avis reste accessible.
                    exemples = indicateur["exemples"]
                    exemples.append(exemple)
                    exemples.sort(key=lambda x: (x["jour"], x["identifiant"]), reverse=True)
                    del exemples[3:]
        if total_examines != nombre:
            raise BilanInvalide("Nombre de lignes examinées incohérent.")
        nombre_thematise = sum(v["avis"] for v in themes.values())
    return {
        "version": VERSION,
        "revision_depot": fiche["revision_depot"],
        "sha256_index": digest,
        "version_index": VERSION_INDEX,
        "nombre_avis": nombre,
        "couverture": couverture,
        "par_jour": dates,
        "par_mois": mois,
        "categories_declarees": categories,
        "principaux_acheteurs_declares": acheteurs,
        "themes_lexicaux": {
            k: {
                "regles": list(MOTIFS[k]),
                "avis": v["avis"],
                "exemples_non_representatifs": v["exemples"],
            } for k, v in themes.items()
        },
        "total_correspondances_avec_recouvrements": nombre_thematise,
        "champs_analyses": ["objet", "jour", "acheteur", "categorie"],
        "ensemble_des_avis_examines": True,
        "completude_historique_etablie": False,
        "avis_distincts_de_marches_distincts": True,
        "preuve_de_penurie_de_competences": False,
        "inference_sur_le_delai_de_mobilisation": False,
        "interpretation": (
            "Comptages descriptifs des avis accessibles dans l'index au commit indiqué. "
            "Un avis ne désigne pas nécessairement un marché distinct. Les thèmes sont "
            "des correspondances lexicales sur l'objet, non des besoins validés ; "
            "un avis peut appartenir à plusieurs thèmes. Les exemples sont "
            "illustratifs et ne démontrent aucune difficulté de mobilisation."
        ),
    }


def ecrire(resultat: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, nom = tempfile.mkstemp(prefix=".bilan-boamp-", suffix=".json",
                               dir=destination.parent)
    os.close(fd)
    temp = Path(nom)
    try:
        temp.write_text(
            json.dumps(resultat, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--preuve-index", type=Path, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    a = parser.parse_args()
    try:
        bilan = produire(a.index, a.preuve_index)
        ecrire(bilan, a.sortie)
        print(json.dumps({
            "revision_depot": bilan["revision_depot"],
            "jours": bilan["couverture"]["jours_archives"],
            "avis": bilan["nombre_avis"],
            "themes": {k: v["avis"] for k, v in bilan["themes_lexicaux"].items()},
            "fichier": str(a.sortie),
        }, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as erreur:
        parser.exit(1, f"Bilan documentaire interrompu : {type(erreur).__name__}: {erreur}\n")


if __name__ == "__main__":
    main()
