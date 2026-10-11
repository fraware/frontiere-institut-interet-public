"""Vérifier les clichés BOAMP corrigés avant toute indexation documentaire.

Une révision désigne un état de l'interface à un autre instant. Sa présence
ne constitue pas une qualification juridique de la modification d'un avis.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re

try:
    from scripts.rechercher_historique_boamp import (
        ArchiveIncoherente, empreinte, LIMITE_COMPRESSEE,
        LIMITE_DECOMPRESSEE, LIMITE_LIGNE, SHA_RE, DATE_RE,
    )
    from scripts.surveiller_revisions_boamp import VERSION as VERSION_REVISIONS
except ModuleNotFoundError:
    from rechercher_historique_boamp import (
        ArchiveIncoherente, empreinte, LIMITE_COMPRESSEE,
        LIMITE_DECOMPRESSEE, LIMITE_LIGNE, SHA_RE, DATE_RE,
    )
    from surveiller_revisions_boamp import VERSION as VERSION_REVISIONS

IDENTIFIANT = re.compile(r"[\w.-]{1,150}")


def horodatage(valeur: str, nom: str) -> datetime:
    if not isinstance(valeur, str):
        raise ArchiveIncoherente(f"Horodatage de {nom} absent.")
    try:
        resultat = datetime.fromisoformat(valeur)
    except ValueError as erreur:
        raise ArchiveIncoherente(f"Horodatage de {nom} illisible.") from erreur
    if resultat.tzinfo is None or resultat.utcoffset() is None:
        raise ArchiveIncoherente(f"Horodatage de {nom} sans fuseau.")
    return resultat.astimezone(timezone.utc)


def fichiers_revision(dossier: Path, jour: str) -> list[Path]:
    """Refuser les couples archive/manifeste isolés et les noms inhabituels."""
    if not DATE_RE.fullmatch(jour):
        raise ArchiveIncoherente("Date de version historique incorrecte.")
    racine = dossier / "revisions_boamp" / jour[:4] / jour[5:7] / jour
    if not racine.exists():
        return []
    if not racine.is_dir() or racine.is_symlink():
        raise ArchiveIncoherente("Répertoire des révisions incohérent.")
    manifestes = set()
    archives = set()
    for fichier in racine.iterdir():
        if not fichier.is_file() or fichier.is_symlink():
            raise ArchiveIncoherente("Entrée de révision non autorisée.")
        nom = fichier.name
        if nom.endswith(".jsonl.gz") and SHA_RE.fullmatch(nom[:-9]):
            archives.add(nom[:-9])
        elif nom.endswith(".json") and SHA_RE.fullmatch(nom[:-5]):
            manifestes.add(nom[:-5])
        else:
            raise ArchiveIncoherente("Nom d'archive de révision inhabituel.")
    if manifestes != archives:
        raise ArchiveIncoherente("Cliché de révision sans manifeste ou réciproquement.")
    return [racine / (sha + ".json") for sha in sorted(manifestes)]


def lire_revision(fiche_path: Path, dossier: Path, jour: str,
                  empreinte_initiale: str, notices_initiales: list[dict],
                  date_initiale: datetime) -> tuple[datetime, str, str, list[dict]]:
    """Vérification complète des octets, des champs et du delta au cliché initial."""
    chemin = fiche_path.relative_to(dossier)
    if (len(chemin.parts) != 6 or chemin.parts[:1] != ("revisions_boamp",)
            or chemin.parts[1] != jour[:4] or chemin.parts[2] != jour[5:7]
            or chemin.parts[3] != jour):
        raise ArchiveIncoherente("Arborescence de révision incorrecte.")
    if fiche_path.is_symlink() or not fiche_path.is_file():
        raise ArchiveIncoherente("Manifeste de révision non régulier.")
    sha_nom = fiche_path.name[:-5]
    if not SHA_RE.fullmatch(sha_nom) or not fiche_path.name.endswith(".json"):
        raise ArchiveIncoherente("Identifiant de révision incorrect.")
    fiche = json.loads(fiche_path.read_text(encoding="utf-8"))
    if (not isinstance(fiche, dict) or fiche.get("version") != VERSION_REVISIONS
            or fiche.get("jour_parution") != jour
            or fiche.get("cliche_initial_sha256_gzip") != empreinte_initiale
            or fiche.get("nombre_initial") != len(notices_initiales)
            or fiche.get("completude_historique_etablie") is not False):
        raise ArchiveIncoherente("Provenance initiale du cliché corrigé incohérente.")
    date_revision = horodatage(fiche.get("recontrole_le"), "révision")
    date_originale_manifest = horodatage(fiche.get("releve_initial_le"), "relevé initial")
    if date_originale_manifest != date_initiale or date_revision <= date_initiale:
        raise ArchiveIncoherente("Chronologie de révision incohérente.")
    archive = fiche_path.with_suffix(".jsonl.gz")
    attendu = archive.relative_to(dossier).as_posix()
    sha_gzip = fiche.get("cliche_revise_sha256_gzip")
    sha_decompresse = fiche.get("cliche_revise_sha256_decompresse")
    if (fiche.get("archive_relative") != attendu
            or not isinstance(sha_gzip, str) or not SHA_RE.fullmatch(sha_gzip)
            or not isinstance(sha_decompresse, str) or not SHA_RE.fullmatch(sha_decompresse)
            or sha_nom != sha_decompresse):
        raise ArchiveIncoherente("Manifestation ou empreinte de version incohérente.")
    if not archive.is_file() or archive.is_symlink():
        raise ArchiveIncoherente("Fichier de version manquant.")
    taille = archive.stat().st_size
    if (not 0 < taille <= LIMITE_COMPRESSEE
            or fiche.get("cliche_revise_octets") != taille):
        raise ArchiveIncoherente("Taille de version incorrecte.")
    if empreinte(archive) != sha_gzip:
        raise ArchiveIncoherente("Empreinte comprimée de la révision incorrecte.")
    h = hashlib.sha256()
    total_octets, nouveaux = 0, {}
    try:
        with gzip.open(archive, "rb") as lecture:
            while ligne := lecture.readline(LIMITE_LIGNE + 1):
                if len(ligne) > LIMITE_LIGNE:
                    raise ArchiveIncoherente("Ligne de révision trop longue.")
                total_octets += len(ligne)
                if total_octets > LIMITE_DECOMPRESSEE:
                    raise ArchiveIncoherente("Révision décompressée trop volumineuse.")
                h.update(ligne)
                n = json.loads(ligne)
                if (not isinstance(n, dict) or not isinstance(n.get("id"), str)
                        or not IDENTIFIANT.fullmatch(n["id"])
                        or n["id"] in nouveaux
                        or not isinstance(n.get("date_parution"), str)
                        or n["date_parution"][:10] != jour
                        or not isinstance(n.get("objet"), str)
                        or not isinstance(n.get("acheteur"), str)
                        or n.get("contenu_integral_copie") is not False):
                    raise ArchiveIncoherente("Notice de révision incorrecte ou dupliquée.")
                nouveaux[n["id"]] = n
    except (OSError, EOFError, UnicodeError, json.JSONDecodeError) as erreur:
        raise ArchiveIncoherente("Révision comprimée illisible.") from erreur
    if h.hexdigest() != sha_decompresse or fiche.get("nombre_revise") != len(nouveaux):
        raise ArchiveIncoherente("Empreinte ou nombre de notices de révision incorrect.")
    anciens = {x["id"]: x for x in notices_initiales}
    ajoutes = sorted(nouveaux.keys() - anciens.keys())
    absents = sorted(anciens.keys() - nouveaux.keys())
    modifies = sorted(k for k in nouveaux.keys() & anciens.keys()
                     if nouveaux[k] != anciens[k])
    if (fiche.get("identifiants_ajoutes") != ajoutes
            or fiche.get("identifiants_absents_du_releve") != absents
            or fiche.get("identifiants_modifies") != modifies
            or not (ajoutes or absents or modifies)):
        raise ArchiveIncoherente("Détail des variations incohérent avec les notices.")
    return date_revision, attendu, sha_gzip, [nouveaux[k] for k in sorted(nouveaux)]
