"""Copier et attester les fichiers sources bruts conservés par FRONTIÈRE.

Les fichiers sont copiés en flux et contrôlés par SHA-256. Un instantané
n'est publié qu'après vérification complète. Le contenu doit être copié
sur un autre stockage pour protéger contre la perte du serveur d'origine.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
from uuid import uuid4

VERSION = "frontiere-archives-brutes-v1"
BLOC = 1024 * 1024
EXTENSIONS = {".json", ".jsonl", ".gz", ".xml", ".csv", ".ndjson", ".txt"}
ETIQUETTE = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")


class ArchiveBruteInvalide(ValueError):
    """Inventaire documentaire incohérent ou copie non vérifiable."""


def _hachage(chemin: Path) -> tuple[int, str]:
    empreinte, taille = hashlib.sha256(), 0
    with chemin.open("rb") as fichier:
        for bloc in iter(lambda: fichier.read(BLOC), b""):
            taille += len(bloc)
            empreinte.update(bloc)
    return taille, empreinte.hexdigest()


def _relatif(texte: str) -> Path:
    if not isinstance(texte, str) or "\\" in texte:
        raise ArchiveBruteInvalide("Chemin d'archive non admissible.")
    p = PurePosixPath(texte)
    if (p.is_absolute() or not p.parts or
            any(x in ("", ".", "..") for x in p.parts) or
            p.as_posix() != texte):
        raise ArchiveBruteInvalide("Chemin d'archive non admissible.")
    return Path(*p.parts)


def _inventaire(source: Path) -> list[Path]:
    if source.is_symlink() or not source.is_dir():
        raise ArchiveBruteInvalide("Répertoire source absent ou lié.")
    candidats = []
    for racine, sous_dossiers, fichiers in os.walk(source, followlinks=False):
        sous_dossiers.sort()
        fichiers.sort()
        base = Path(racine)
        for nom in sous_dossiers:
            if (base / nom).is_symlink():
                raise ArchiveBruteInvalide("Lien symbolique dans les sources.")
        for nom in fichiers:
            chemin = base / nom
            if chemin.is_symlink():
                raise ArchiveBruteInvalide("Lien symbolique dans les sources.")
            if (nom.startswith(".") or nom.endswith(("-wal", "-shm", ".tmp",
                ".sqlite3", ".db"))):
                continue
            if chemin.suffix.lower() not in EXTENSIONS:
                raise ArchiveBruteInvalide(
                    "Fichier source de format inattendu : " + nom
                )
            if not stat.S_ISREG(chemin.stat().st_mode):
                raise ArchiveBruteInvalide("Fichier spécial parmi les sources.")
            candidats.append(chemin)
    return candidats


def _copier(source: Path, destination: Path) -> tuple[int, str]:
    initial = source.stat()
    if not stat.S_ISREG(initial.st_mode):
        raise ArchiveBruteInvalide("Source non régulière.")
    taille, digest = 0, hashlib.sha256()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as entree, destination.open("xb") as sortie:
        for bloc in iter(lambda: entree.read(BLOC), b""):
            taille += len(bloc)
            digest.update(bloc)
            sortie.write(bloc)
        sortie.flush()
        os.fsync(sortie.fileno())
    final = source.stat()
    if (final.st_size != initial.st_size or
            final.st_mtime_ns != initial.st_mtime_ns or
            final.st_ino != initial.st_ino or
            taille != initial.st_size):
        raise ArchiveBruteInvalide("Source modifiée pendant sa copie.")
    if _hachage(destination) != (taille, digest.hexdigest()):
        raise ArchiveBruteInvalide("Copie locale incorrecte.")
    return taille, digest.hexdigest()


def sauvegarder(sources: dict[str, Path], destination: Path) -> Path:
    if not sources or any(not ETIQUETTE.fullmatch(x) for x in sources):
        raise ArchiveBruteInvalide("Étiquettes de sources incorrectes.")
    destination = destination.resolve()
    for chemin in sources.values():
        racine = chemin.resolve()
        if destination.is_relative_to(racine) or racine.is_relative_to(destination):
            raise ArchiveBruteInvalide("Destination imbriquée avec les sources.")
    destination.mkdir(parents=True, exist_ok=True)
    provisoire = destination / (".en-cours-" + uuid4().hex)
    provisoire.mkdir(exist_ok=False)
    try:
        fichiers = []
        for nom in sorted(sources):
            racine = sources[nom]
            for original in _inventaire(racine):
                relatif = original.relative_to(racine).as_posix()
                p = _relatif(relatif)
                cible = provisoire / "originaux" / nom / p
                taille, sha = _copier(original, cible)
                fichiers.append({
                    "source": nom, "chemin": relatif,
                    "octets": taille, "sha256": sha,
                })
        instant = datetime.now(timezone.utc).replace(microsecond=0)
        manifeste = {
            "version": VERSION, "sauvegarde_le": instant.isoformat(),
            "repertoires_attendus": sorted(sources),
            "fichiers": fichiers, "nombre_fichiers": len(fichiers),
            "octets_bruts": sum(x["octets"] for x in fichiers),
            "copies_sqlite_incluses": False,
        }
        (provisoire / "manifest.json").write_text(
            json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        verifier(provisoire)
        cible = destination / (
            "frontiere-bruts-" + instant.strftime("%Y%m%dT%H%M%SZ") +
            "-" + uuid4().hex[:8]
        )
        provisoire.rename(cible)
        return cible
    except Exception:
        shutil.rmtree(provisoire)
        raise


def verifier(dossier: Path) -> dict:
    fiche = dossier / "manifest.json"
    if fiche.is_symlink() or not fiche.is_file():
        raise ArchiveBruteInvalide("Manifeste absent.")
    doc = json.loads(fiche.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("version") != VERSION:
        raise ArchiveBruteInvalide("Version documentaire inconnue.")
    noms = doc.get("repertoires_attendus")
    if not isinstance(noms, list) or not noms or len(noms) != len(set(noms)):
        raise ArchiveBruteInvalide("Liste de sources manquante ou répétée.")
    if any(not isinstance(n, str) or not ETIQUETTE.fullmatch(n) for n in noms):
        raise ArchiveBruteInvalide("Étiquettes invalides dans le manifeste.")
    fichiers = doc.get("fichiers")
    if not isinstance(fichiers, list) or len(fichiers) != doc.get("nombre_fichiers"):
        raise ArchiveBruteInvalide("Inventaire documentaire incohérent.")
    trouves, octets = set(), 0
    for enregistrement in fichiers:
        if not isinstance(enregistrement, dict):
            raise ArchiveBruteInvalide("Description de fichier invalide.")
        nom = enregistrement.get("source")
        if nom not in noms:
            raise ArchiveBruteInvalide("Source d'archive inconnue.")
        relatif = _relatif(enregistrement.get("chemin"))
        cle = (nom, relatif.as_posix())
        if cle in trouves:
            raise ArchiveBruteInvalide("Même fichier déclaré deux fois.")
        trouves.add(cle)
        chemin = dossier / "originaux" / nom / relatif
        if chemin.is_symlink() or not chemin.is_file():
            raise ArchiveBruteInvalide("Copie documentaire absente ou liée.")
        taille, sha = _hachage(chemin)
        if (taille != enregistrement.get("octets") or
                sha != enregistrement.get("sha256")):
            raise ArchiveBruteInvalide("Empreinte ou taille documentaire incorrecte.")
        octets += taille
    if octets != doc.get("octets_bruts"):
        raise ArchiveBruteInvalide("Total d'octets incohérent.")
    return {
        "etat": "verifiee", "nombre_fichiers": len(fichiers),
        "octets_bruts": octets, "repertoires": noms,
        "originaux_verifies": True, "bases_sqlite_incluses": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", default=[],
                        help="Répéter etiquette=/chemin/repertoire")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--verifier", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.verifier is not None:
            if args.source or args.destination is not None:
                parser.error("--verifier doit être utilisé seul.")
            etat = verifier(args.verifier)
        else:
            if args.destination is None:
                parser.error("--destination nécessaire.")
            sources = {}
            for element in args.source:
                if "=" not in element:
                    raise ArchiveBruteInvalide("Syntaxe source=chemin attendue.")
                nom, chemin = element.split("=", 1)
                if nom in sources:
                    raise ArchiveBruteInvalide("Source déclarée deux fois.")
                sources[nom] = Path(chemin)
            dossier = sauvegarder(sources, args.destination)
            etat = {"dossier": str(dossier), **verifier(dossier)}
        print(json.dumps(etat, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ArchiveBruteInvalide, json.JSONDecodeError) as exc:
        print(f"Sources brutes non sauvegardées : {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
