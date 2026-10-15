"""Sauvegarder les trois bases persistantes par le mécanisme SQLite backup.

Chaque base est copiée au moyen d'une transaction de lecture cohérente même
si le collecteur continue à écrire. Une empreinte SHA-256, les tables
essentielles et l'intégrité SQLite sont vérifiées avant publication du
manifeste final. La sauvegarde n'inclut pas les fichiers sources bruts.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import sys

SOURCES = ("boamp", "emplois", "decp")
TABLES = {
    "boamp": {"avis_boamp", "versions_avis_boamp", "captures_boamp"},
    "emplois": {"versions_emplois_publics", "captures_emplois_publics"},
    "decp": {"marches", "versions", "fichiers_sources"},
}
VERSION = "frontiere-sauvegarde-sqlite-v1"
TAILLE_BLOC = 1024 * 1024


class SauvegardeInvalide(ValueError):
    """Archive incomplète, corrompue ou présentant un schéma inattendu."""


def empreinte(chemin: Path) -> str:
    sha = hashlib.sha256()
    with chemin.open("rb") as entree:
        for bloc in iter(lambda: entree.read(TAILLE_BLOC), b""):
            sha.update(bloc)
    return sha.hexdigest()


def _ouvrir_readonly(chemin: Path) -> sqlite3.Connection:
    if chemin.is_symlink() or not chemin.is_file():
        raise SauvegardeInvalide("Base source absente ou liée symboliquement.")
    conn = sqlite3.connect(
        chemin.resolve().as_uri() + "?mode=ro", uri=True, timeout=90
    )
    conn.execute("PRAGMA busy_timeout=90000")
    return conn


def _verifier_base(chemin: Path, nom: str) -> dict:
    with closing(_ouvrir_readonly(chemin)) as conn:
        resultat = conn.execute("PRAGMA integrity_check").fetchone()
        if not resultat or resultat[0] != "ok":
            raise SauvegardeInvalide(f"Intégrité SQLite non confirmée pour {nom}.")
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not TABLES[nom].issubset(tables):
            raise SauvegardeInvalide(f"Schéma incompatible pour {nom}.")
    return {"octets": chemin.stat().st_size, "sha256": empreinte(chemin)}


def _copier_sqlite(source: Path, cible: Path, nom: str) -> dict:
    temporaire = cible.with_suffix(".en_cours")
    try:
        with closing(_ouvrir_readonly(source)) as entree:
            with closing(sqlite3.connect(temporaire, timeout=90)) as sortie:
                entree.backup(sortie, pages=256, sleep=0.1)
        resultat = _verifier_base(temporaire, nom)
        temporaire.replace(cible)
        return resultat
    finally:
        temporaire.unlink(missing_ok=True)


def _analyser_sources(sources: dict[str, Path]) -> None:
    if set(sources) != set(SOURCES):
        raise SauvegardeInvalide(
            "Les trois sources boamp, emplois et decp sont obligatoires."
        )
    for nom, chemin in sources.items():
        if not isinstance(chemin, Path):
            raise SauvegardeInvalide(f"Chemin incorrect pour {nom}.")
        if not chemin.is_file() or chemin.is_symlink():
            raise SauvegardeInvalide(f"Source SQLite introuvable pour {nom}.")


def sauvegarder(
    sources: dict[str, Path], destination: Path, *,
    maintenant: datetime | None = None,
) -> Path:
    """Publier une sauvegarde complète ou ne laisser aucun dossier partiel."""
    _analyser_sources(sources)
    horloge = maintenant or datetime.now(timezone.utc)
    if horloge.tzinfo is None:
        raise SauvegardeInvalide("Date de sauvegarde sans fuseau.")
    instant = horloge.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    destination.mkdir(parents=True, exist_ok=True)
    dossier = destination / (
        "frontiere-" + horloge.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-" + secrets.token_hex(4)
    )
    dossier.mkdir(exist_ok=False)
    try:
        bases: dict[str, dict] = {}
        for nom in SOURCES:
            sortie = dossier / f"{nom}.sqlite3"
            bases[nom] = {
                "fichier": sortie.name,
                **_copier_sqlite(sources[nom], sortie, nom),
            }
        manifeste = {
            "version": VERSION,
            "sauvegarde_le": instant,
            "bases": bases,
            "fichiers_sources_bruts_inclus": False,
            "copies_reprises_en_lecture_coherente_individuelle": True,
            "instantane_multi_bases_global": False,
        }
        # Le manifeste ne paraît qu'une fois tous les fichiers contrôlés.
        (dossier / "manifest.json").write_text(
            json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        verifier(dossier)
        return dossier
    except Exception:
        shutil.rmtree(dossier)
        raise


def verifier(dossier: Path) -> dict:
    """Contrôler octets, schémas et intégrité SQLite d'une copie autonome."""
    manifeste_path = dossier / "manifest.json"
    if not manifeste_path.is_file() or manifeste_path.is_symlink():
        raise SauvegardeInvalide("Manifeste de sauvegarde absent.")
    manifeste = json.loads(manifeste_path.read_text(encoding="utf-8"))
    if not isinstance(manifeste, dict) or manifeste.get("version") != VERSION:
        raise SauvegardeInvalide("Version de sauvegarde non reconnue.")
    bases = manifeste.get("bases")
    if not isinstance(bases, dict) or set(bases) != set(SOURCES):
        raise SauvegardeInvalide("Liste de bases incomplète.")
    for nom in SOURCES:
        attendu = bases[nom]
        if not isinstance(attendu, dict) or attendu.get("fichier") != f"{nom}.sqlite3":
            raise SauvegardeInvalide(f"Fichier de sauvegarde inattendu : {nom}.")
        chemin = dossier / attendu["fichier"]
        reel = _verifier_base(chemin, nom)
        if reel != {k: attendu.get(k) for k in ("octets", "sha256")}:
            raise SauvegardeInvalide(f"Empreinte ou taille modifiée : {nom}.")
    return {
        "etat": "verifiee",
        "sauvegarde_le": manifeste.get("sauvegarde_le"),
        "bases_verifiees": len(bases),
        "archives_brutes_incluses": False,
        "dossier": str(dossier),
    }


def _entrees(valeurs: list[str]) -> dict[str, Path]:
    resultats: dict[str, Path] = {}
    for entree in valeurs:
        if "=" not in entree:
            raise SauvegardeInvalide("L'argument --source attend nom=chemin.")
        nom, chemin = entree.split("=", 1)
        if nom not in SOURCES or nom in resultats or not chemin:
            raise SauvegardeInvalide("Nom de source inconnu ou répété.")
        resultats[nom] = Path(chemin)
    return resultats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", default=[],
                        help="Répéter nom=chemin pour les trois bases")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--verifier", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.verifier is not None:
            if args.source or args.destination is not None:
                parser.error("--verifier doit être utilisé seul.")
            resultat = verifier(args.verifier)
        else:
            if args.destination is None:
                parser.error("--destination est obligatoire.")
            dossier = sauvegarder(_entrees(args.source), args.destination)
            resultat = verifier(dossier)
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
        return 0
    except (SauvegardeInvalide, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"Sauvegarde FRONTIÈRE non validée : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
