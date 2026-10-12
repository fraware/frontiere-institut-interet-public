"""Matérialiser les signaux publics versionnés dans SQLite et les rechercher.

L'importation est locale, transactionnelle, idempotente et hors réseau.
Les publications demeurent des signaux non qualifiés, distincts des épisodes
d'exécution. Le fichier SQLite n'est jamais publié dans le dépôt.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

RACINE = Path(__file__).resolve().parents[1]
FLUX = RACINE / "institutionnel" / "flux_publics"
INDEX = FLUX / "observations.json"
CATALOGUE = FLUX / "sources_v1.json"
IDENTIFIANT = re.compile(r"^[a-f0-9]{64}$")


class IndexInvalide(ValueError):
    """Refuser une ingestion susceptible de corrompre les données d'origine."""


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY, nom TEXT NOT NULL, categorie TEXT NOT NULL,
    type_source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS publications (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    titre TEXT NOT NULL,
    description TEXT NOT NULL,
    lien TEXT,
    date_publication TEXT,
    nature_signal TEXT NOT NULL,
    observe_initialement_le TEXT NOT NULL,
    mis_a_jour_le TEXT NOT NULL,
    empreinte_contenu TEXT NOT NULL,
    nombre_revisions_documentees INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_publications_source_date
    ON publications (source_id, date_publication);
CREATE TABLE IF NOT EXISTS versions_observees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_id TEXT NOT NULL REFERENCES publications(id),
    empreinte_contenu TEXT NOT NULL,
    observe_le TEXT NOT NULL,
    titre TEXT NOT NULL,
    UNIQUE (publication_id, empreinte_contenu)
);
CREATE VIRTUAL TABLE IF NOT EXISTS recherche_fts
    USING fts5(id UNINDEXED, titre, description, tokenize='unicode61 remove_diacritics 2');
"""


def _date(valeur: object, champ: str, *, optionnel: bool = False) -> str | None:
    if valeur is None and optionnel:
        return None
    if not isinstance(valeur, str):
        raise IndexInvalide(f"Date incorrecte : {champ}")
    try:
        resultat = datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IndexInvalide(f"Date illisible : {champ}") from exc
    if resultat.tzinfo is None:
        raise IndexInvalide(f"Date sans fuseau : {champ}")
    return valeur


def _texte(valeur: object, nom: str, maximum: int) -> str:
    if not isinstance(valeur, str) or not valeur.strip() or len(valeur) > maximum:
        raise IndexInvalide(f"Valeur textuelle incorrecte : {nom}")
    return valeur


def verifier_donnees(catalogue: dict, index: dict) -> tuple[list[dict], list[dict]]:
    """Établir l'intégrité et la référentialité avant d'ouvrir une transaction."""
    if catalogue.get("version") != 1 or index.get("version") != 1:
        raise IndexInvalide("Version de document incorrecte")
    sources = catalogue.get("sources")
    lignes = index.get("observations")
    if not isinstance(sources, list) or not isinstance(lignes, list):
        raise IndexInvalide("Catalogue ou observations non structurés")
    sources_par_id = {}
    for source in sources:
        if not isinstance(source, dict):
            raise IndexInvalide("Source non structurée")
        sid = _texte(source.get("id"), "source", 80)
        if sid in sources_par_id:
            raise IndexInvalide("Identifiant de source répété")
        _texte(source.get("nom"), "nom de source", 250)
        _texte(source.get("categorie"), "catégorie", 90)
        if source.get("type") not in {"rss", "bluesky"}:
            raise IndexInvalide("Type de source inconnu")
        sources_par_id[sid] = source
    ids = set()
    for publication in lignes:
        if not isinstance(publication, dict):
            raise IndexInvalide("Publication non structurée")
        pid = publication.get("identifiant_publication")
        if not isinstance(pid, str) or not IDENTIFIANT.fullmatch(pid):
            raise IndexInvalide("Identifiant de publication non conforme")
        if pid in ids:
            raise IndexInvalide("Publication présente plusieurs fois")
        ids.add(pid)
        if publication.get("source_id") not in sources_par_id:
            raise IndexInvalide("Source de publication absente du catalogue")
        if publication.get("nature_signal") != "publication_publique_non_qualifiee":
            raise IndexInvalide("Qualification automatique non autorisée")
        _texte(publication.get("titre"), "titre", 260)
        if not isinstance(publication.get("description"), str) or len(publication["description"]) > 500:
            raise IndexInvalide("Description trop longue")
        lien = publication.get("lien")
        if lien is not None:
            if not isinstance(lien, str) or len(lien) > 2048:
                raise IndexInvalide("Lien invalide")
            url = urlsplit(lien)
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                raise IndexInvalide("Lien non public ou non sécurisé")
        _date(publication.get("date_publication"), "publication", optionnel=True)
        premier = _date(publication.get("observe_initialement_le"), "première observation")
        dernier = _date(publication.get("mis_a_jour_le"), "dernière observation")
        if datetime.fromisoformat(premier) > datetime.fromisoformat(dernier):
            raise IndexInvalide("Chronologie inversée")
        if not isinstance(publication.get("empreinte_contenu"), str) or not IDENTIFIANT.fullmatch(publication["empreinte_contenu"]):
            raise IndexInvalide("Empreinte de version invalide")
        revisions = publication.get("nombre_revisions")
        if type(revisions) is not int or revisions < 0:
            raise IndexInvalide("Nombre de révisions incorrect")
    return list(sources_par_id.values()), lignes


def ouvrir(base: Path, *, creer: bool) -> sqlite3.Connection:
    """Ouvrir une base existante ou préparer un index SQLite hors du dépôt."""
    if not creer and not base.is_file():
        raise IndexInvalide("Base de données absente")
    if creer:
        base.parent.mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(base)
    connexion.row_factory = sqlite3.Row
    connexion.execute("PRAGMA foreign_keys=ON")
    if creer:
        try:
            connexion.executescript(SCHEMA)
        except sqlite3.OperationalError as exc:
            connexion.close()
            raise IndexInvalide("SQLite avec FTS5 requis") from exc
    return connexion


def importer(base: Path, catalogue: dict, index: dict) -> dict:
    """Importer chaque publication sans supprimer celles disparues d'un flux."""
    sources, publications = verifier_donnees(catalogue, index)
    connexion = ouvrir(base, creer=True)
    ajouts = modifications = inchanges = 0
    try:
        with connexion:
            for source in sources:
                connexion.execute(
                    """INSERT INTO sources(id, nom, categorie, type_source)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                         nom=excluded.nom, categorie=excluded.categorie,
                         type_source=excluded.type_source""",
                    (source["id"], source["nom"], source["categorie"], source["type"]),
                )
            for publication in publications:
                identifiant = publication["identifiant_publication"]
                precedent = connexion.execute(
                    """SELECT empreinte_contenu, mis_a_jour_le, observe_initialement_le
                       FROM publications WHERE id=?""", (identifiant,),
                ).fetchone()
                if precedent is not None:
                    if precedent["empreinte_contenu"] == publication["empreinte_contenu"]:
                        inchanges += 1
                        continue
                    date_avant = datetime.fromisoformat(precedent["mis_a_jour_le"])
                    date_apres = datetime.fromisoformat(publication["mis_a_jour_le"])
                    if date_apres < date_avant:
                        raise IndexInvalide("Tentative de remplacer une version plus récente")
                ligne = (
                    identifiant, publication["source_id"], publication["titre"],
                    publication["description"], publication["lien"],
                    publication["date_publication"], publication["nature_signal"],
                    precedent["observe_initialement_le"] if precedent is not None
                    else publication["observe_initialement_le"],
                    publication["mis_a_jour_le"], publication["empreinte_contenu"],
                    publication["nombre_revisions"],
                )
                connexion.execute(
                    """INSERT INTO publications
                       (id, source_id, titre, description, lien, date_publication,
                        nature_signal, observe_initialement_le, mis_a_jour_le,
                        empreinte_contenu, nombre_revisions_documentees)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         titre=excluded.titre, description=excluded.description,
                         lien=excluded.lien, date_publication=excluded.date_publication,
                         mis_a_jour_le=excluded.mis_a_jour_le,
                         empreinte_contenu=excluded.empreinte_contenu,
                         nombre_revisions_documentees=excluded.nombre_revisions_documentees""",
                    ligne,
                )
                connexion.execute("DELETE FROM recherche_fts WHERE id=?", (identifiant,))
                connexion.execute(
                    "INSERT INTO recherche_fts(id, titre, description) VALUES (?,?,?)",
                    (identifiant, publication["titre"], publication["description"]),
                )
                connexion.execute(
                    """INSERT OR IGNORE INTO versions_observees
                       (publication_id, empreinte_contenu, observe_le, titre)
                       VALUES (?,?,?,?)""",
                    (identifiant, publication["empreinte_contenu"],
                     publication["mis_a_jour_le"], publication["titre"]),
                )
                if precedent is None:
                    ajouts += 1
                else:
                    modifications += 1
        total = connexion.execute("SELECT COUNT(*) FROM publications").fetchone()[0]
        return {"ajouts": ajouts, "modifications": modifications,
                "inchanges": inchanges, "publications_indexees": total,
                "source_distinctes": len(sources),
                "couverture_exhaustive": False}
    finally:
        connexion.close()


def rechercher(base: Path, expression: str, source: str | None = None, limite: int = 30) -> list[dict]:
    """Interroger l'index textuel, avec paramètres SQL séparés des données."""
    if not isinstance(expression, str) or not 1 <= len(expression.strip()) <= 120:
        raise IndexInvalide("Expression de recherche incorrecte")
    if type(limite) is not int or not 1 <= limite <= 100:
        raise IndexInvalide("Limite de résultats incorrecte")
    phrase = '"' + expression.strip().replace('"', '""') + '"'
    connexion = ouvrir(base, creer=False)
    try:
        curseur = connexion.execute(
            """SELECT p.id, p.source_id, p.titre, p.description,
                      p.lien, p.date_publication, p.observe_initialement_le
               FROM recherche_fts JOIN publications p ON p.id = recherche_fts.id
               WHERE recherche_fts MATCH ? AND (? IS NULL OR p.source_id=?)
               ORDER BY COALESCE(p.date_publication, p.observe_initialement_le) DESC
               LIMIT ?""",
            (phrase, source, source, limite),
        )
        return [dict(ligne) for ligne in curseur.fetchall()]
    except sqlite3.OperationalError as exc:
        raise IndexInvalide("Expression de recherche non exploitable") from exc
    finally:
        connexion.close()


def main() -> None:
    """Exécuter une importation ou une recherche reproductible en ligne de commande."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["importer", "rechercher"])
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--catalogue", type=Path, default=CATALOGUE)
    parser.add_argument("--observations", type=Path, default=INDEX)
    parser.add_argument("--expression")
    parser.add_argument("--source")
    parser.add_argument("--limite", type=int, default=30)
    args = parser.parse_args()
    try:
        if args.action == "importer":
            resultat = importer(
                args.base,
                json.loads(args.catalogue.read_text(encoding="utf-8")),
                json.loads(args.observations.read_text(encoding="utf-8")),
            )
        else:
            resultat = rechercher(args.base, args.expression or "", args.source, args.limite)
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
    except (IndexInvalide, OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"Base de signaux non disponible : {type(exc).__name__} : {exc}\n")


if __name__ == "__main__":
    main()
