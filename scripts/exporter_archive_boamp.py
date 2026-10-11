"""Exporter un ensemble BOAMP vérifié et portable sans dépendance réseau.

Le paquet contient les archives quotidiennes, les états corrigés, les
manifestes et un inventaire SHA-256. Il ne constitue pas une copie hors site
tant qu'il n'a pas été transféré vers un stockage indépendant.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from zipfile import ZIP_STORED, ZipFile, ZipInfo, BadZipFile

try:
    from scripts.rechercher_historique_boamp import (
        DOSSIER, ArchiveIncoherente, indexer,
    )
except ModuleNotFoundError:
    from rechercher_historique_boamp import (
        DOSSIER, ArchiveIncoherente, indexer,
    )

VERSION = "export-boamp-verifiable-v1"
DATE = r"20\d{2}-\d{2}-\d{2}"
SHA = r"[a-f0-9]{64}"
AUTORISES = (
    re.compile(rf"historique_boamp/20\d{{2}}/\d{{2}}/{DATE}\.(?:json|jsonl\.gz)"),
    re.compile(rf"revisions_boamp/20\d{{2}}/\d{{2}}/{DATE}/{SHA}\.(?:json|jsonl\.gz)"),
    re.compile(r"etat_historique_boamp\.json"),
    re.compile(r"etat_revisions_boamp\.json"),
)
MAX_FICHIERS = 30000
MAX_OCTETS_PAR_FICHIER = 12_000_000
PREFIXE = "boamp/"


def autorise(relatif: str) -> bool:
    return any(m.fullmatch(relatif) for m in AUTORISES)


def empreinte(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def fichiers_autorises(dossier: Path) -> list[tuple[str, Path]]:
    membres = []
    for emplacement in (dossier / "historique_boamp", dossier / "revisions_boamp"):
        if not emplacement.exists():
            continue
        if not emplacement.is_dir() or emplacement.is_symlink():
            raise ArchiveIncoherente("Répertoire d'archives non régulier.")
        for fichier in emplacement.rglob("*"):
            if fichier.is_symlink():
                raise ArchiveIncoherente("Lien symbolique interdit dans le paquet.")
            if fichier.is_dir():
                continue
            rel = fichier.relative_to(dossier).as_posix()
            if not fichier.is_file() or not autorise(rel):
                raise ArchiveIncoherente("Chemin d'archive non autorisé.")
            membres.append((rel, fichier))
    for nom in ("etat_historique_boamp.json", "etat_revisions_boamp.json"):
        fichier = dossier / nom
        if fichier.exists():
            if not fichier.is_file() or fichier.is_symlink():
                raise ArchiveIncoherente("Fichier d'état non régulier.")
            membres.append((nom, fichier))
    membres.sort(key=lambda x: x[0])
    if not membres or len(membres) > MAX_FICHIERS:
        raise ArchiveIncoherente("Nombre d'archives incorrect ou excessif.")
    noms = [x[0] for x in membres]
    if len(noms) != len(set(noms)):
        raise ArchiveIncoherente("Chemin répété.")
    for dossier_source in ("historique_boamp", "revisions_boamp"):
        bases = set()
        notices = set()
        for nom in noms:
            if not nom.startswith(dossier_source + "/"):
                continue
            if nom.endswith(".jsonl.gz"):
                notices.add(nom[:-9])
            elif nom.endswith(".json"):
                bases.add(nom[:-5])
        if bases != notices:
            raise ArchiveIncoherente("Archives ou manifestes sans contrepartie.")
    return membres


def entree_zip(nom: str) -> ZipInfo:
    info = ZipInfo(PREFIXE + nom, (1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_STORED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    return info


def verifier_paquet(chemin: Path) -> dict:
    if not chemin.is_file():
        raise ArchiveIncoherente("Paquet introuvable.")
    try:
        with ZipFile(chemin, "r") as paquet:
            infos = paquet.infolist()
            noms = [x.filename for x in infos]
            if (len(infos) > MAX_FICHIERS + 1 or len(noms) != len(set(noms))
                    or PREFIXE + "inventaire.json" not in noms):
                raise ArchiveIncoherente("Inventaire absent ou noms répétés.")
            inventaire = json.loads(paquet.read(PREFIXE + "inventaire.json"))
            if inventaire.get("version") != VERSION or not isinstance(inventaire.get("fichiers"), list):
                raise ArchiveIncoherente("Version d'inventaire non reconnue.")
            entrees = inventaire["fichiers"]
            attendus = {PREFIXE + e["chemin"] for e in entrees}
            if set(noms) != attendus | {PREFIXE + "inventaire.json"}:
                raise ArchiveIncoherente("Composition du paquet différente de l'inventaire.")
            if len(entrees) != len(attendus):
                raise ArchiveIncoherente("Chemins répétés dans l'inventaire.")
            for entree in entrees:
                relatif = entree["chemin"]
                if not isinstance(relatif, str) or not autorise(relatif):
                    raise ArchiveIncoherente("Entrée d'inventaire non autorisée.")
                meta = paquet.getinfo(PREFIXE + relatif)
                if (meta.is_dir() or meta.compress_type != ZIP_STORED
                        or not 0 <= meta.file_size <= MAX_OCTETS_PAR_FICHIER
                        or meta.file_size != entree.get("octets")):
                    raise ArchiveIncoherente("Taille ou type d'entrée incorrect.")
                if empreinte(paquet.read(PREFIXE + relatif)) != entree.get("sha256"):
                    raise ArchiveIncoherente("Empreinte d'un fichier exporté incohérente.")
    except (BadZipFile, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as erreur:
        raise ArchiveIncoherente("Archive ZIP illisible ou inventaire mal formé.") from erreur
    return {
        "version": VERSION,
        "fichiers_verifies": len(entrees),
        "sha256_paquet": empreinte(chemin.read_bytes()),
        "jours_indexes_au_depart": inventaire["bilan_index"]["nombre_jours_indexes"],
        "avis_indexes_au_depart": inventaire["bilan_index"]["nombre_avis_indexes"],
        "copie_hors_site_effectuee": False,
    }


def exporter(dossier: Path, destination: Path, revision_depot: str | None = None) -> dict:
    if revision_depot is not None and not re.fullmatch(r"[0-9a-f]{40}", revision_depot):
        raise ArchiveIncoherente("Révision Git source invalide.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="validation-boamp-") as temporaire:
        bilan = indexer(dossier, Path(temporaire) / "validation.sqlite3")
    fichiers = fichiers_autorises(dossier)
    inventaire = {
        "version": VERSION,
        "revision_depot": revision_depot,
        "bilan_index": {k: v for k, v in bilan.items() if k != "index"},
        "fichiers": [],
        "copie_hors_site_effectuee": False,
    }
    memoire = []
    for nom, chemin in fichiers:
        if chemin.stat().st_size > MAX_OCTETS_PAR_FICHIER:
            raise ArchiveIncoherente("Fichier trop volumineux pour le paquet.")
        octets = chemin.read_bytes()
        inventaire["fichiers"].append({
            "chemin": nom, "octets": len(octets), "sha256": empreinte(octets),
        })
        memoire.append((nom, octets))
    contenu_inventaire = (json.dumps(
        inventaire, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ) + "\n").encode("utf-8")
    fd, nom_temp = tempfile.mkstemp(prefix=".archive-boamp-", suffix=".zip",
                                   dir=destination.parent)
    os.close(fd)
    tmp = Path(nom_temp)
    try:
        with ZipFile(tmp, "w", allowZip64=True) as zip:
            for nom, octets in memoire:
                zip.writestr(entree_zip(nom), octets)
            zip.writestr(entree_zip("inventaire.json"), contenu_inventaire)
        preuve = verifier_paquet(tmp)
        os.replace(tmp, destination)
        return {
            **preuve, "chemin": str(destination),
            "revision_depot": revision_depot,
        }
    finally:
        tmp.unlink(missing_ok=True)


def main() -> None:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("action", choices=("exporter", "verifier"))
    parseur.add_argument("--dossier", type=Path, default=DOSSIER)
    parseur.add_argument("--paquet", type=Path, required=True)
    parseur.add_argument("--revision", default=None)
    options = parseur.parse_args()
    try:
        resultat = (exporter(options.dossier, options.paquet, options.revision)
                    if options.action == "exporter"
                    else verifier_paquet(options.paquet))
    except (OSError, ValueError) as erreur:
        parseur.exit(1, f"Export BOAMP interrompu : {type(erreur).__name__}: {erreur}\n")
    print(json.dumps(resultat, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
