"""Archiver des exports publics en conservant exactement leurs octets.

Cette archive locale adressée par SHA-256 prépare un stockage externe à
conservation verrouillée. Elle n'est pas immuable face à l'administrateur local.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
from urllib.parse import urlsplit

TAILLE_BLOC = 1024 * 1024
SHA256 = re.compile(r"^[a-f0-9]{64}$")
IDENTIFIANT = re.compile(r"^[a-z][a-z0-9_-]{1,79}$")


class ErreurArchive(ValueError):
    """Échec de validation ou d'intégrité d'une source archivée."""


def _json(donnees: dict) -> bytes:
    """Octets canoniques d'une fiche de capture."""
    return (json.dumps(donnees, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _dossier(racine: Path) -> Path:
    """Ouvrir la racine sans suivre de lien symbolique direct."""
    if racine.is_symlink():
        raise ErreurArchive("La racine de l'archive est un lien symbolique.")
    racine.mkdir(parents=True, exist_ok=True)
    if not racine.is_dir():
        raise ErreurArchive("La racine de l'archive doit être un répertoire.")
    return racine.resolve()


def _sous_dossier(racine: Path, relatif: str) -> Path:
    """Créer des répertoires et rejeter leurs liens symboliques."""
    chemin = racine
    for morceau in Path(relatif).parts:
        if morceau in {"", ".", ".."}:
            raise ErreurArchive("Chemin interne incorrect.")
        chemin = chemin / morceau
        if chemin.is_symlink():
            raise ErreurArchive("Lien symbolique interdit dans l'archive.")
        chemin.mkdir(exist_ok=True)
        if not chemin.is_dir():
            raise ErreurArchive("Chemin interne non répertoire.")
    return chemin


def _fichier_existant(chemin: Path) -> bool:
    """Refuser un fichier non régulier ou référencé par un autre lien matériel."""
    try:
        info = chemin.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ErreurArchive("Objet ou fiche d'archive non régulier, ou lié ailleurs.")
    return True


def _empreinte(chemin: Path) -> tuple[str, int]:
    """Empreinte et longueur d'un objet d'archive."""
    if not _fichier_existant(chemin):
        raise ErreurArchive("Objet archivé absent.")
    h, longueur = hashlib.sha256(), 0
    with chemin.open("rb") as fichier:
        while bloc := fichier.read(TAILLE_BLOC):
            h.update(bloc)
            longueur += len(bloc)
    return h.hexdigest(), longueur


def _synchroniser_repertoire(dossier: Path) -> None:
    """Synchroniser les métadonnées de répertoire sur POSIX."""
    if os.name == "posix":
        fd = os.open(dossier, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _installer_immuable(dossier: Path, nom: str, ecrire) -> Path:
    """Créer sans remplacement, par publication atomique sur le même disque."""
    chemin = dossier / nom
    temporaire = dossier / (".ecriture-" + secrets.token_hex(16))
    fd = os.open(temporaire, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as flux:
            ecrire(flux)
            flux.flush()
            os.fsync(flux.fileno())
        try:
            os.link(temporaire, chemin, follow_symlinks=False)
        except FileExistsError:
            if not _fichier_existant(chemin):
                raise ErreurArchive("Chemin concurrent inattendu.")
        temporaire.unlink(missing_ok=True)
        _synchroniser_repertoire(dossier)
    finally:
        temporaire.unlink(missing_ok=True)
    return chemin


def _date(valeur: str) -> str:
    """Normaliser une date déclarée avec fuseau horaire."""
    try:
        date = datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ErreurArchive("Date de capture ISO 8601 incorrecte.") from exc
    if date.utcoffset() is None:
        raise ErreurArchive("Date de capture sans fuseau horaire.")
    return date.astimezone(timezone.utc).isoformat()


def archiver(racine: Path, source: Path, *, source_id: str, url: str,
             licence: str, observe_le: str, etag: str | None = None,
             derniere_modification: str | None = None) -> dict:
    """Archiver un fichier public et ses métadonnées déclarées, sans correction."""
    if not IDENTIFIANT.fullmatch(source_id):
        raise ErreurArchive("Identifiant de source invalide.")
    url_parts = urlsplit(url)
    if url_parts.scheme not in {"http", "https"} or not url_parts.netloc or url_parts.username or url_parts.password:
        raise ErreurArchive("Adresse source publique HTTP(S) incorrecte.")
    if not licence.strip():
        raise ErreurArchive("Licence ou statut de réutilisation obligatoire.")
    instant = _date(observe_le)
    if source.is_symlink() or not source.is_file():
        raise ErreurArchive("Le fichier à archiver doit être régulier, sans lien symbolique.")
    racine = _dossier(racine)
    objects = _sous_dossier(racine, "objets/sha256")
    temporaire = objects / (".source-" + secrets.token_hex(16))
    try:
        h, octets = hashlib.sha256(), 0
        avant = source.stat()
        fd = os.open(temporaire, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with source.open("rb") as entree, os.fdopen(fd, "wb") as sortie:
            while bloc := entree.read(TAILLE_BLOC):
                h.update(bloc)
                octets += len(bloc)
                sortie.write(bloc)
            sortie.flush()
            os.fsync(sortie.fileno())
        apres = source.stat()
        if (avant.st_ino, avant.st_size, avant.st_mtime_ns) != (apres.st_ino, apres.st_size, apres.st_mtime_ns):
            raise ErreurArchive("La source a changé pendant la copie.")
        digest = h.hexdigest()
        objet_dir = _sous_dossier(racine, f"objets/sha256/{digest[:2]}")
        objet = objet_dir / digest
        try:
            os.link(temporaire, objet, follow_symlinks=False)
        except FileExistsError:
            if not _fichier_existant(objet):
                raise ErreurArchive("Objet préexistant non régulier.")
        temporaire.unlink(missing_ok=True)
        empreinte, taille = _empreinte(objet)
        if (empreinte, taille) != (digest, octets):
            raise ErreurArchive("L'archive contient un objet altéré sous cette empreinte.")
        _synchroniser_repertoire(objet_dir)
    finally:
        temporaire.unlink(missing_ok=True)

    fiche = {
        "version_schema": "capture-source-brute-v1",
        "source_id": source_id,
        "url_source": url,
        "licence_declaree": licence,
        "observe_le_declare": instant,
        "entetes_http_declares": {"etag": etag, "derniere_modification": derniere_modification},
        "sha256_octets_bruts": digest,
        "nombre_octets": octets,
        "chemin_objet": f"objets/sha256/{digest[:2]}/{digest}",
        "limite": "Identité des octets locaux, sans attestation d'origine ni verrouillage externe.",
    }
    donnees = _json(fiche)
    capture_sha = hashlib.sha256(donnees).hexdigest()
    fiches_dir = _sous_dossier(racine, "captures")
    fichier = _installer_immuable(fiches_dir, capture_sha + ".json", lambda f: f.write(donnees))
    if fichier.read_bytes() != donnees:
        raise ErreurArchive("Une fiche existante ne correspond pas aux métadonnées attendues.")
    return {"capture": capture_sha, "objet": digest, "octets": octets,
            "fiche": str(fichier.relative_to(racine)), "stockage": str(racine)}


def verifier(racine: Path, capture: str) -> dict:
    """Revérifier à la lecture la fiche et les octets qu'elle désigne."""
    if not SHA256.fullmatch(capture):
        raise ErreurArchive("Empreinte de capture incorrecte.")
    racine = _dossier(racine)
    chemin = racine / "captures" / (capture + ".json")
    if not _fichier_existant(chemin):
        raise ErreurArchive("Fiche de capture introuvable.")
    donnees = chemin.read_bytes()
    if hashlib.sha256(donnees).hexdigest() != capture:
        raise ErreurArchive("Fiche de capture modifiée.")
    try:
        fiche = json.loads(donnees)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ErreurArchive("Fiche de capture illisible.") from exc
    digest = fiche.get("sha256_octets_bruts")
    if fiche.get("version_schema") != "capture-source-brute-v1" or not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ErreurArchive("Fiche de capture sans référence valide.")
    relatif = f"objets/sha256/{digest[:2]}/{digest}"
    if fiche.get("chemin_objet") != relatif:
        raise ErreurArchive("Chemin de l'objet incompatible avec son empreinte.")
    objet = racine / relatif
    if any(p.is_symlink() for p in (racine / "objets", racine / "objets/sha256", objet.parent)):
        raise ErreurArchive("Lien symbolique dans le chemin d'archive.")
    empreinte, octets = _empreinte(objet)
    if empreinte != digest or octets != fiche.get("nombre_octets"):
        raise ErreurArchive("Objet archivé corrompu ou modifié.")
    return {"capture": capture, "objet": digest, "octets": octets, "conforme": True}


def restaurer(racine: Path, capture: str, destination: Path) -> dict:
    """Restaurer vers un nouveau fichier sans effacer un fichier préexistant."""
    constat = verifier(racine, capture)
    if destination.is_symlink():
        raise ErreurArchive("Destination symbolique interdite.")
    objet = _dossier(racine) / "objets/sha256" / constat["objet"][:2] / constat["objet"]
    if not destination.parent.is_dir():
        raise ErreurArchive("Le dossier de destination doit déjà exister.")
    cree = False
    try:
        with destination.open("xb") as sortie:
            cree = True
            h = hashlib.sha256()
            with objet.open("rb") as entree:
                while bloc := entree.read(TAILLE_BLOC):
                    h.update(bloc)
                    sortie.write(bloc)
            sortie.flush()
            os.fsync(sortie.fileno())
        if h.hexdigest() != constat["objet"]:
            raise ErreurArchive("L'objet a changé pendant sa restauration.")
    except Exception:
        if cree:
            destination.unlink(missing_ok=True)
        raise
    return {"capture": capture, "destination": str(destination), "octets": constat["octets"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sous = parser.add_subparsers(dest="action", required=True)
    a = sous.add_parser("archiver", help="Copier un export public sans le modifier.")
    a.add_argument("--archive", type=Path, required=True)
    a.add_argument("--fichier", type=Path, required=True)
    a.add_argument("--source-id", required=True)
    a.add_argument("--url", required=True)
    a.add_argument("--licence", required=True)
    a.add_argument("--observe-le", required=True, help="Date de capture déclarée ISO 8601.")
    a.add_argument("--etag")
    a.add_argument("--derniere-modification")
    v = sous.add_parser("verifier", help="Vérifier une capture et ses octets.")
    v.add_argument("--archive", type=Path, required=True)
    v.add_argument("--capture", required=True)
    r = sous.add_parser("restaurer", help="Restaurer sans écraser un fichier existant.")
    r.add_argument("--archive", type=Path, required=True)
    r.add_argument("--capture", required=True)
    r.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "archiver":
            resultat = archiver(args.archive, args.fichier, source_id=args.source_id,
                                url=args.url, licence=args.licence, observe_le=args.observe_le,
                                etag=args.etag, derniere_modification=args.derniere_modification)
        elif args.action == "verifier":
            resultat = verifier(args.archive, args.capture)
        else:
            resultat = restaurer(args.archive, args.capture, args.destination)
    except (ErreurArchive, OSError, ValueError) as exc:
        parser.exit(1, f"Archivage refusé : {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
