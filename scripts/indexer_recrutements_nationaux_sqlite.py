"""Indexer toutes les variantes CSP archivées dans une base SQLite FTS5.

La base est une projection locale des seize partitions déjà versionnées,
sans serveur, sans appel réseau et sans textes longs de compétences.
Une variante et une référence d'offre sont des unités distinctes.
Les dates sont celles du document et ne prouvent pas une offre ouverte.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from scripts.preparer_relecture_besoins_explicites import (
    PARTITIONS, REPERTOIRE, SHA, date_publique, filtrer_texte
)

VERSION = "frontiere-index-integral-recrutements-v1"
RACINE = Path(__file__).resolve().parents[1]
MANIFESTE = REPERTOIRE / "manifest_offres_postes.json"
SHARD = re.compile(r"^lot_([0-9a-f]{2})\.jsonl$")
TERMES = re.compile(r"\w+", flags=re.UNICODE)
LIMITE_LIGNE = 24_000

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE offres (
 id INTEGER PRIMARY KEY,
 cle_enregistrement TEXT NOT NULL UNIQUE,
 reference TEXT NOT NULL,
 titre TEXT NOT NULL,
 entite TEXT NOT NULL,
 metier TEXT NOT NULL,
 specialisation TEXT NOT NULL,
 date_index TEXT,
 nature_date TEXT NOT NULL,
 date_fin_publication TEXT,
 chemin_source TEXT NOT NULL,
 ligne_source INTEGER NOT NULL,
 sha256_ligne TEXT NOT NULL
);
CREATE INDEX ix_offres_reference ON offres(reference, date_index DESC, cle_enregistrement);
CREATE INDEX ix_offres_date ON offres(date_index DESC, reference);
CREATE TABLE references_offres (
 reference TEXT PRIMARY KEY,
 variantes INTEGER NOT NULL CHECK(variantes>0)
);
CREATE TABLE meta (nom TEXT PRIMARY KEY, valeur TEXT NOT NULL);
CREATE VIRTUAL TABLE recherche_fts USING fts5(
 titre, entite, metier, specialisation,
 content='offres', content_rowid='id',
 tokenize='unicode61 remove_diacritics 2'
);
"""


class IndexRecrutementsInvalide(ValueError):
    pass


def imposer(condition: bool, message: str) -> None:
    if not condition:
        raise IndexRecrutementsInvalide(message)


def verifier_manifeste(octets: bytes) -> dict:
    try:
        m = json.loads(octets)
    except (UnicodeError, ValueError) as exc:
        raise IndexRecrutementsInvalide("Manifeste JSON illisible.") from exc
    noms = set(PARTITIONS)
    empreintes = m.get("empreintes_partitions")
    imposer(m.get("version") == "emplois-publics-extraits-v1"
            and isinstance(empreintes, dict)
            and set(empreintes) == noms
            and all(isinstance(v, str) and SHA.fullmatch(v)
                    for v in empreintes.values())
            and isinstance(m.get("sha256_csv"), str)
            and SHA.fullmatch(m["sha256_csv"]) is not None
            and all(type(m.get(k)) is int and m[k] >= 0 for k in (
                "offres_distinctes", "references_distinctes",
                "references_avec_plusieurs_variantes",
                "variantes_supplementaires_de_reference"))
            and m["offres_distinctes"] > 0
            and m["references_distinctes"] > 0
            and m["offres_distinctes"] - m["references_distinctes"] ==
                m["variantes_supplementaires_de_reference"],
            "Population ou empreintes incompatibles avec le manifeste CSP.")
    return m


def version_exacte(d: dict) -> tuple[str, str]:
    cle = d.get("cle_enregistrement")
    ref = d.get("reference")
    imposer(isinstance(cle, str) and SHA.fullmatch(cle) is not None
            and isinstance(ref, str) and 3 <= len(ref) <= 180
            and not any(ord(c) < 32 for c in ref),
            "Identité de variante ou référence invalide.")
    contenu = {k: v for k, v in d.items() if k != "cle_enregistrement"}
    canonique = json.dumps(contenu, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    imposer(hashlib.sha256(canonique).hexdigest() == cle,
            "Empreinte de la variante incompatible avec la projection source.")
    return cle, ref


def extraire(d: dict, chemin: str, ligne: int, brut: bytes) -> tuple:
    cle, ref = version_exacte(d)
    tronques = d.get("champs_tronques")
    imposer(isinstance(tronques, list) and
            all(isinstance(x, str) for x in tronques),
            "Liste des champs tronqués absente.")
    def champ(nom: str, taille: int) -> str:
        if nom in tronques:
            return ""
        return filtrer_texte(d.get(nom), taille) or ""

    titre = champ("intitule", 400)
    entite = champ("organisme", 240) or champ("employeur", 250)
    metier = champ("metier", 220)
    specialisation = champ("specialisation", 350)
    dates = (("publication_debut", date_publique(d.get("publication_debut"))),
             ("premiere_publication", date_publique(d.get("premiere_publication"))),
             ("date_vacance", date_publique(d.get("date_vacance"))))
    nature, date_index = next(((n, val) for n, val in dates if val),
                              ("absente", None))
    date_fin = date_publique(d.get("publication_fin"))
    return (cle, ref, titre, entite, metier, specialisation,
            date_index, nature, date_fin, chemin, ligne,
            hashlib.sha256(brut).hexdigest())


def _chemin_base(racine: Path, base: Path) -> Path:
    root = racine.resolve()
    cible = base.absolute()
    imposer(cible.suffix in (".sqlite", ".sqlite3", ".db") and
            not cible.is_symlink() and
            not cible.resolve().is_relative_to(root),
            "La base doit être placée hors du dépôt source.")
    return cible


def construire(racine: Path, base: Path, *, remplacer: bool = False) -> dict:
    """Créer entièrement une base dans un fichier temporaire, puis la publier.

    Un manifeste incomplet, un seul lot altéré, une variante corrompue,
    une collision ou un écart d'effectifs interrompt la reconstruction.
    La base existante est conservée si le traitement échoue.
    """
    racine = racine.resolve()
    base = _chemin_base(racine, base)
    imposer(remplacer or not base.exists(), "Base existante : utiliser --remplacer.")
    donnees_manifest = (racine / MANIFESTE).read_bytes()
    m = verifier_manifeste(donnees_manifest)
    base.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".frontiere-csp-", suffix=".sqlite3",
                                     dir=base.parent, delete=False) as f:
        provisoire = Path(f.name)
    connexion = None
    try:
        connexion = sqlite3.connect(provisoire)
        connexion.executescript(SCHEMA)
        connexion.execute("PRAGMA synchronous=NORMAL")
        connexion.execute("BEGIN")
        nombre = 0
        supprimes = 0
        for nom in PARTITIONS:
            chemin = REPERTOIRE / "offres_postes" / nom
            h = hashlib.sha256()
            numero_part = int(SHARD.fullmatch(nom).group(1), 16)
            with (racine / chemin).open("rb") as fp:
                for n, line in enumerate(fp, start=1):
                    h.update(line)
                    imposer(line.endswith(b"\n") and 1 < len(line) <= LIMITE_LIGNE,
                            "Ligne source trop longue ou sans fin de ligne.")
                    try:
                        doc = json.loads(line)
                        imposer(isinstance(doc, dict), "Document non structuré.")
                        valeurs = extraire(doc, chemin.as_posix(), n, line)
                    except (UnicodeError, ValueError, TypeError) as exc:
                        raise IndexRecrutementsInvalide(
                            f"Document invalide dans {nom}, ligne {n}.") from exc
                    reference = valeurs[1]
                    imposer(int(hashlib.sha256(reference.encode("utf-8"))
                                .hexdigest()[0], 16) == numero_part,
                            f"Référence dans la mauvaise partition : {nom}.")
                    cursor = connexion.execute("""
                        INSERT INTO offres (
                            cle_enregistrement, reference, titre, entite, metier,
                            specialisation, date_index, nature_date,
                            date_fin_publication, chemin_source,
                            ligne_source, sha256_ligne
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """, valeurs)
                    connexion.execute("""
                        INSERT INTO recherche_fts (
                            rowid, titre, entite, metier, specialisation
                        ) VALUES (?,?,?,?,?)
                    """, (cursor.lastrowid, valeurs[2], valeurs[3],
                          valeurs[4], valeurs[5]))
                    if not any(valeurs[i] for i in (2, 3, 4, 5)):
                        supprimes += 1
                    nombre += 1
            imposer(h.hexdigest() == m["empreintes_partitions"][nom],
                    f"Empreinte de lot incohérente : {nom}")
        imposer(nombre == m["offres_distinctes"],
                "Nombre de variantes différent du manifeste.")
        connexion.execute("""
            INSERT INTO references_offres(reference, variantes)
            SELECT reference, COUNT(*) FROM offres GROUP BY reference
        """)
        references = connexion.execute(
            "SELECT COUNT(*) FROM references_offres").fetchone()[0]
        avec_variantes = connexion.execute(
            "SELECT COUNT(*) FROM references_offres WHERE variantes > 1").fetchone()[0]
        imposer(references == m["references_distinctes"] and
                avec_variantes == m["references_avec_plusieurs_variantes"],
                "Nombre de références ou de versions différent du manifeste.")
        meta = {
            "version": VERSION,
            "sha256_manifeste": hashlib.sha256(donnees_manifest).hexdigest(),
            "sha256_csv_original_non_conserve": m["sha256_csv"],
            "variantes_indexees": str(nombre),
            "references_distinctes": str(references),
            "references_multivariantes": str(avec_variantes),
            "partitions_verifiees": str(len(PARTITIONS)),
            "entrees_sans_texte_recherchable": str(supprimes),
            "couverture_nationale_demontree": "false",
            "recrutements_actuels_confirmes": "0",
            "texte_competences_long_indexe": "false",
        }
        connexion.executemany("INSERT INTO meta(nom,valeur) VALUES(?,?)",
                              sorted(meta.items()))
        connexion.commit()
        imposer(connexion.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "Structure SQLite incohérente.")
        connexion.execute("INSERT INTO recherche_fts(recherche_fts) VALUES('integrity-check')")
        connexion.close()
        connexion = None
        os.replace(provisoire, base)
        return {
            "version": VERSION, "variantes_indexees": nombre,
            "references_distinctes": references,
            "references_multivariantes": avec_variantes,
            "partitions_verifiees": 16,
            "entrees_sans_texte_recherchable": supprimes,
            "octets_base": base.stat().st_size,
            "couverture_nationale_demontree": False,
            "recrutements_actuels_confirmes": 0,
        }
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise IndexRecrutementsInvalide("Construction refusée : " + str(exc)) from exc
    finally:
        if connexion is not None:
            connexion.close()
        provisoire.unlink(missing_ok=True)


def _ouvrir(base: Path) -> sqlite3.Connection:
    imposer(base.is_file() and not base.is_symlink(),
            "Index absent ou chemin non admis.")
    connexion = sqlite3.connect(f"file:{base.resolve()}?mode=ro", uri=True)
    connexion.row_factory = sqlite3.Row
    version = connexion.execute(
        "SELECT valeur FROM meta WHERE nom='version'").fetchone()
    imposer(version is not None and version["valeur"] == VERSION,
            "Index d'une version inconnue.")
    return connexion


def _expression(texte: str) -> str:
    imposer(isinstance(texte, str) and
            1 <= len(texte) <= 160 and
            not any(ord(c) < 32 for c in texte) and ";" not in texte,
            "Expression de recherche invalide.")
    mots = TERMES.findall(texte)
    imposer(1 <= len(mots) <= 12 and all(len(m) <= 45 for m in mots),
            "Expression trop longue ou sans termes.")
    return " AND ".join('"' + w.replace('"', "") + '"' for w in mots)


def rechercher(base: Path, *, expression: str | None = None,
               reference: str | None = None,
               depuis: str | None = None, jusqua: str | None = None,
               limite: int = 30, decalage: int = 0) -> dict:
    """Retourner les références uniques et le nombre de variantes correspondantes.

    Le tri est documentaire : date de la variante correspondante la plus
    récente, puis référence stable, et non une estimation d'actualité.
    """
    imposer(expression is not None or reference is not None,
            "Expression ou référence nécessaire.")
    imposer(type(limite) is int and 1 <= limite <= 100
            and type(decalage) is int and 0 <= decalage <= 10000,
            "Pagination hors limites.")
    if reference is not None:
        imposer(isinstance(reference, str) and
                3 <= len(reference) <= 180 and
                not any(ord(c) < 32 for c in reference),
                "Référence invalide.")
    def date_filtre(v: str, champ: str) -> None:
        imposer(isinstance(v, str) and len(v) == 10,
                "Date incorrecte : " + champ)
        try:
            correcte = date.fromisoformat(v).isoformat() == v
        except ValueError:
            correcte = False
        imposer(correcte, "Date incorrecte : " + champ)

    if depuis is not None:
        date_filtre(depuis, "début")
    if jusqua is not None:
        date_filtre(jusqua, "fin")
    imposer(depuis is None or jusqua is None or depuis <= jusqua,
            "Intervalle de dates inversé.")
    filtres, args = [], []
    if expression is not None:
        filtres.append("recherche_fts MATCH ?")
        args.append(_expression(expression))
    if reference is not None:
        filtres.append("o.reference = ?")
        args.append(reference)
    if depuis is not None:
        filtres.append("o.date_index >= ?")
        args.append(depuis)
    if jusqua is not None:
        filtres.append("o.date_index <= ?")
        args.append(jusqua)
    jointure = ("JOIN recherche_fts ON recherche_fts.rowid=o.id"
                if expression is not None else "")
    where = " AND ".join(filtres)
    sql = f"""
        WITH correspondances AS (
          SELECT o.id, o.reference, o.titre, o.entite, o.metier,
                 o.specialisation, o.date_index, o.nature_date,
                 o.date_fin_publication, o.chemin_source,
                 o.ligne_source, o.sha256_ligne, o.cle_enregistrement,
                 COUNT(*) OVER (PARTITION BY o.reference) AS variantes_correspondantes,
                 ROW_NUMBER() OVER (
                    PARTITION BY o.reference
                    ORDER BY o.date_index DESC, o.cle_enregistrement ASC
                 ) AS numero
          FROM offres AS o {jointure}
          WHERE {where}
        )
        SELECT correspondances.*, r.variantes AS variantes_archivees
        FROM correspondances
        JOIN references_offres AS r USING(reference)
        WHERE numero = 1
        ORDER BY date_index DESC, reference ASC
        LIMIT ? OFFSET ?
    """
    connexion = _ouvrir(base)
    try:
        lignes = connexion.execute(sql, args + [limite, decalage]).fetchall()
        return {
            "version": VERSION,
            "references_retournees": len(lignes),
            "couverture_nationale_demontree": False,
            "resultats": [{
                k: row[k] for k in (
                    "reference", "titre", "entite", "metier",
                    "specialisation", "date_index", "nature_date",
                    "date_fin_publication", "chemin_source", "ligne_source",
                    "sha256_ligne", "cle_enregistrement",
                    "variantes_correspondantes", "variantes_archivees"
                )
            } for row in lignes]
        }
    finally:
        connexion.close()


def bilan(base: Path) -> dict:
    connexion = _ouvrir(base)
    try:
        m = dict(connexion.execute("SELECT nom,valeur FROM meta"))
        return {
            "version": m["version"],
            "variantes_indexees": int(m["variantes_indexees"]),
            "references_distinctes": int(m["references_distinctes"]),
            "references_multivariantes": int(m["references_multivariantes"]),
            "partitions_verifiees": int(m["partitions_verifiees"]),
            "sha256_manifeste": m["sha256_manifeste"],
            "couverture_nationale_demontree": False,
            "recrutements_actuels_confirmes": 0
        }
    finally:
        connexion.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="commande", required=True)
    creer = sub.add_parser("construire")
    creer.add_argument("--racine", type=Path, default=RACINE)
    creer.add_argument("--base", type=Path, required=True)
    creer.add_argument("--remplacer", action="store_true")
    chercher = sub.add_parser("rechercher")
    chercher.add_argument("--base", type=Path, required=True)
    chercher.add_argument("--expression")
    chercher.add_argument("--reference")
    chercher.add_argument("--depuis")
    chercher.add_argument("--jusqua")
    chercher.add_argument("--limite", type=int, default=30)
    chercher.add_argument("--decalage", type=int, default=0)
    consulter = sub.add_parser("bilan")
    consulter.add_argument("--base", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.commande == "construire":
            resultat = construire(a.racine, a.base, remplacer=a.remplacer)
        elif a.commande == "rechercher":
            resultat = rechercher(a.base, expression=a.expression,
                                 reference=a.reference, depuis=a.depuis,
                                 jusqua=a.jusqua, limite=a.limite,
                                 decalage=a.decalage)
        else:
            resultat = bilan(a.base)
        print(json.dumps(resultat, ensure_ascii=False, sort_keys=True))
    except (OSError, IndexRecrutementsInvalide, sqlite3.Error, ValueError) as exc:
        p.exit(1, f"Index national non exploitable : {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
