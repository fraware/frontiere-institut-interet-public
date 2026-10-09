"""Indexer et rechercher les avis historiques BOAMP à partir d'archives vérifiées.

L'index est une représentation locale des avis archivés, non une validation
de besoins scientifiques, ni une garantie de complétude historique.
Aucun accès réseau. Aucune donnée de contact n'est importée.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import unicodedata

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "institutionnel" / "besoins_publics"
INDEX = RACINE / "data" / "boamp_historique.sqlite3"
VERSION = "recherche-boamp-historique-v1"
DATE_RE = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
LIMITE_COMPRESSEE = 10_000_000
LIMITE_DECOMPRESSEE = 50_000_000
LIMITE_LIGNE = 100_000


class ArchiveIncoherente(ValueError):
    """Provenance, structure ou contenu d'une archive non conforme."""


def empreinte(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as source:
        while bloc := source.read(1_048_576):
            h.update(bloc)
    return h.hexdigest()


def avis_archive(chemin_fiche: Path, dossier: Path):
    """Valider l'archive et produire ses notices, avec leur chemin source."""
    fiche = json.loads(chemin_fiche.read_text(encoding="utf-8"))
    jour = chemin_fiche.stem
    if (not DATE_RE.fullmatch(jour)
            or chemin_fiche.parent.name != jour[5:7]
            or chemin_fiche.parent.parent.name != jour[:4]
            or fiche.get("jour_parution") != jour
            or fiche.get("pages_completes") is not True):
        raise ArchiveIncoherente("Date, arborescence ou pagination incohérentes.")
    archive = chemin_fiche.with_suffix(".jsonl.gz")
    attendu = archive.relative_to(dossier).as_posix()
    if fiche.get("archive_relative") != attendu:
        raise ArchiveIncoherente("Chemin annoncé différent du fichier réellement utilisé.")
    a, b = fiche.get("sha256_archive_gzip"), fiche.get("sha256_octets_decompresses")
    if not isinstance(a, str) or not isinstance(b, str) or not SHA_RE.fullmatch(a) or not SHA_RE.fullmatch(b):
        raise ArchiveIncoherente("Empreintes absentes ou incorrectes.")
    if not archive.is_file() or archive.is_symlink():
        raise ArchiveIncoherente("Archive manquante ou lien symbolique.")
    taille = archive.stat().st_size
    if not 0 < taille <= LIMITE_COMPRESSEE or fiche.get("octets_archive") != taille:
        raise ArchiveIncoherente("Taille d'archive non conforme.")
    if empreinte(archive) != a:
        raise ArchiveIncoherente("Empreinte des octets comprimés différente.")

    lignes, total, h, codes = [], 0, hashlib.sha256(), set()
    with gzip.open(archive, "rb") as flux:
        while ligne := flux.readline(LIMITE_LIGNE + 1):
            if len(ligne) > LIMITE_LIGNE:
                raise ArchiveIncoherente("Notice anormalement volumineuse.")
            total += len(ligne)
            if total > LIMITE_DECOMPRESSEE:
                raise ArchiveIncoherente("Archive dépassant le volume décompressé autorisé.")
            h.update(ligne)
            try:
                notice = json.loads(ligne)
            except (UnicodeError, json.JSONDecodeError) as erreur:
                raise ArchiveIncoherente("Notice JSON illisible.") from erreur
            if not isinstance(notice, dict) or not isinstance(notice.get("id"), str):
                raise ArchiveIncoherente("Identifiant d'avis absent.")
            identifiant = notice["id"]
            if (not re.fullmatch(r"[\w.-]{1,150}", identifiant)
                    or identifiant in codes
                    or not isinstance(notice.get("date_parution"), str)
                    or notice["date_parution"][:10] != jour):
                raise ArchiveIncoherente("Identifiant répété ou date de parution incorrecte.")
            if (not isinstance(notice.get("objet"), str)
                    or not isinstance(notice.get("acheteur"), str)
                    or not isinstance(notice.get("contenu_integral_copie"), bool)
                    or notice["contenu_integral_copie"] is not False):
                raise ArchiveIncoherente("Champs attendus ou périmètre documentaire incorrects.")
            codes.add(identifiant)
            lignes.append(notice)
    if h.hexdigest() != b:
        raise ArchiveIncoherente("Empreinte du contenu décompressé différente.")
    if (type(fiche.get("avis_distincts")) is not int
            or type(fiche.get("avis_recus")) is not int
            or len(lignes) != fiche["avis_distincts"]
            or len(lignes) != fiche["avis_recus"]):
        raise ArchiveIncoherente("Nombre d'avis différent de la source déclarée.")
    return jour, attendu, a, lignes


def preparer_base(connexion: sqlite3.Connection) -> None:
    connexion.executescript("""
        CREATE TABLE provenance (
            jour TEXT PRIMARY KEY, archive TEXT NOT NULL, sha256 TEXT NOT NULL,
            nombre_avis INTEGER NOT NULL
        );
        CREATE VIRTUAL TABLE recherche USING fts5(
            jour UNINDEXED, identifiant UNINDEXED, objet, acheteur,
            avis UNINDEXED, categorie UNINDEXED, etat UNINDEXED,
            tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TABLE informations(cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
    """)


def indexer(dossier: Path, cible: Path) -> dict:
    racine = dossier / "historique_boamp"
    if not racine.is_dir() or racine.is_symlink():
        raise ArchiveIncoherente("Répertoire d'archives historiques absent.")
    fiches = sorted(racine.glob("20??/??/20??-??-??.json"))
    if not fiches:
        raise ArchiveIncoherente("Aucune journée historique vérifiable.")
    cible.parent.mkdir(parents=True, exist_ok=True)
    fd, nom = tempfile.mkstemp(prefix=".boamp-index-", suffix=".sqlite3", dir=cible.parent)
    os.close(fd)
    temporaire = Path(nom)
    total = 0
    try:
        with closing(sqlite3.connect(temporaire)) as connexion:
            preparer_base(connexion)
            for fiche in fiches:
                jour, archive, sha, lignes = avis_archive(fiche, dossier)
                connexion.execute(
                    "INSERT INTO provenance VALUES(?,?,?,?)",
                    (jour, archive, sha, len(lignes)),
                )
                connexion.executemany(
                    "INSERT INTO recherche VALUES(?,?,?,?,?,?,?)",
                    [(jour, x["id"], x["objet"], x["acheteur"], x.get("avis"),
                      x.get("categorie_marche"), x.get("etat_avis")) for x in lignes],
                )
                total += len(lignes)
            connexion.executemany("INSERT INTO informations VALUES(?,?)", [
                ("version", VERSION),
                ("nombre_jours", str(len(fiches))),
                ("nombre_avis", str(total)),
                ("completude_historique_etablie", "false"),
            ])
            connexion.commit()
            controle = connexion.execute("PRAGMA integrity_check").fetchone()[0]
            if controle != "ok":
                raise ArchiveIncoherente("Index SQLite incohérent.")
        os.replace(temporaire, cible)
    finally:
        temporaire.unlink(missing_ok=True)
    return {
        "version": VERSION,
        "nombre_jours_indexes": len(fiches),
        "nombre_avis_indexes": total,
        "completude_historique_etablie": False,
        "index": str(cible),
    }


def mots(terme: str) -> str:
    if not isinstance(terme, str) or not 2 <= len(terme.strip()) <= 250:
        raise ValueError("Recherche vide ou excessive.")
    s = "".join(c for c in unicodedata.normalize("NFKD", terme.casefold())
                if not unicodedata.combining(c))
    tokens = list(dict.fromkeys(re.findall(r"[a-z0-9]{2,}", s)))
    if not tokens or len(tokens) > 12:
        raise ValueError("De un à douze termes distinctifs sont admis.")
    return " AND ".join('"' + x + '"' for x in tokens)


def chercher(index: Path, terme: str, limite: int = 30, page: int = 1) -> dict:
    if not index.is_file() or not 1 <= limite <= 100 or not 1 <= page <= 1000:
        raise ValueError("Index manquant ou pagination incorrecte.")
    requete = mots(terme)
    with closing(sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)) as connexion:
        version = connexion.execute(
            "SELECT valeur FROM informations WHERE cle = 'version'"
        ).fetchone()
        if version is None or version[0] != VERSION:
            raise ValueError("Version de l'index historique non reconnue.")
        nombre = connexion.execute(
            "SELECT COUNT(*) FROM recherche WHERE recherche MATCH ?", (requete,)
        ).fetchone()[0]
        curseur = connexion.execute(
            "SELECT jour,identifiant,objet,acheteur,avis,categorie,etat "
            "FROM recherche WHERE recherche MATCH ? ORDER BY rank LIMIT ? OFFSET ?",
            (requete, limite, (page - 1) * limite),
        )
        resultats = [{
            "date_parution": x[0], "identifiant": x[1], "objet": x[2],
            "acheteur": x[3], "avis": x[4],
            "categorie_marche": x[5], "etat_avis": x[6],
        } for x in curseur]
    return {
        "version": VERSION, "expression": terme, "total_candidats": nombre,
        "page": page, "resultats": resultats,
        "preuve_de_besoin_scientifique": False,
        "completude_historique_etablie": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("indexer", "chercher"))
    parser.add_argument("--dossier", type=Path, default=DOSSIER)
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--terme", default="")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limite", type=int, default=30)
    args = parser.parse_args()
    try:
        resultat = (indexer(args.dossier, args.index) if args.action == "indexer"
                    else chercher(args.index, args.terme, args.limite, args.page))
    except (OSError, ValueError, sqlite3.Error, EOFError) as erreur:
        parser.exit(1, f"Recherche historique interrompue : {type(erreur).__name__}: {erreur}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
