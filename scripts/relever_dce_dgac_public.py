"""Vérifier sans identification une archive DCE publique citée par un tiers.

Ne rediffuse pas le contenu du DCE ; enregistre exclusivement des empreintes
et des métadonnées bornées. La provenance première et les droits restent à vérifier.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import BadZipFile, ZipFile

URL_ARCHIVE = "https://betterplace.info/files/3013529-dce.zip"
URL_NOTICE_SOURCE = "https://betterplace.info/dce/3013529"
URL_PROFIL_OFFICIEL = (
    "https://www.marches-publics.gouv.fr/app.php/entreprise/consultation/3013529"
    "?orgAcronyme=d4t"
)
TAILLE_MAX_ARCHIVE = 5 * 1024 * 1024
TAILLE_MAX_DOCUMENT = 16 * 1024 * 1024
TAILLE_MAX_DECOMPRESSEE_DECLAREE = 32 * 1024 * 1024
NOMBRE_MAX_ENTREES = 100
CIBLES_PDF = {
    "2026-SNARP-001 CCTP.pdf",
    "RAPC 2026-SNARP-001.pdf",
}


class CollecteRefusee(ValueError):
    """L'archive n'est pas contrôlable dans les bornes publiées."""


def _verifier_adresse(adresse: str) -> None:
    try:
        u = urlsplit(adresse)
        correcte = (
            u.scheme == "https" and u.hostname == "betterplace.info"
            and u.port in (None, 443) and not u.username and not u.password
            and not u.fragment
        )
    except ValueError:
        correcte = False
    if not correcte:
        raise CollecteRefusee("Adresse de téléchargement en dehors du domaine autorisé")


class RedirectionsRestreintes(HTTPRedirectHandler):
    """Rejeter une redirection sortant de l'origine publique retenue."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _verifier_adresse(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def obtenir_archive() -> bytes:
    """Télécharger dans une mémoire bornée, sans authentification ni cookies fournis."""
    _verifier_adresse(URL_ARCHIVE)
    requete = Request(URL_ARCHIVE, headers={
        "User-Agent": "FRONTIERE-documentation-publique/1.0",
        "Accept": "application/zip, application/octet-stream",
    })
    with build_opener(RedirectionsRestreintes()).open(requete, timeout=25) as rep:
        _verifier_adresse(rep.geturl())
        octets = rep.read(TAILLE_MAX_ARCHIVE + 1)
    if len(octets) > TAILLE_MAX_ARCHIVE:
        raise CollecteRefusee("Archive supérieure à la limite de sécurité")
    if len(octets) < 4 or octets[:2] != b"PK":
        raise CollecteRefusee("Réponse dépourvue de structure ZIP")
    return octets


def _nom_admissible(nom: str) -> bool:
    p = PurePosixPath(nom)
    return (
        bool(nom) and len(nom) <= 300 and "\\" not in nom
        and "\x00" not in nom and not nom.startswith("/")
        and not any(part in {"", ".", ".."} for part in nom.split("/"))
        and ":" not in p.parts[0]
    )


def analyser_archive(octets: bytes) -> dict:
    """Valider les bornes ZIP et les deux PDF attendus, CRC compris."""
    if not 0 < len(octets) <= TAILLE_MAX_ARCHIVE:
        raise CollecteRefusee("Longueur de l'archive invalide")
    try:
        archive = ZipFile(io.BytesIO(octets))
    except BadZipFile as exc:
        raise CollecteRefusee("Archive ZIP corrompue") from exc
    with archive:
        entrees = archive.infolist()
        if not 0 < len(entrees) <= NOMBRE_MAX_ENTREES:
            raise CollecteRefusee("Nombre d'entrées ZIP hors limite")
        if any(not _nom_admissible(x.filename) or x.flag_bits & 1 for x in entrees):
            raise CollecteRefusee("Nom ZIP dangereux ou contenu chiffré")
        if sum(x.file_size for x in entrees) > TAILLE_MAX_DECOMPRESSEE_DECLAREE:
            raise CollecteRefusee("Volume décompressé annoncé excessif")
        if any(x.file_size > TAILLE_MAX_DOCUMENT for x in entrees):
            raise CollecteRefusee("Document annoncé supérieur à la limite")
        fichiers = [x for x in entrees if not x.is_dir()]
        cibles = {}
        for info in fichiers:
            nom = PurePosixPath(info.filename).name
            if nom not in CIBLES_PDF:
                continue
            if nom in cibles:
                raise CollecteRefusee("Noms de pièces attendues dupliqués")
            with archive.open(info) as flux:
                contenu = flux.read(TAILLE_MAX_DOCUMENT + 1)
            if len(contenu) > TAILLE_MAX_DOCUMENT or not contenu.startswith(b"%PDF-"):
                raise CollecteRefusee("Pièce attendue non conforme au format PDF")
            cibles[nom] = {
                "nom": nom,
                "octets": len(contenu),
                "sha256": hashlib.sha256(contenu).hexdigest(),
                "verification_crc_zip": True,
            }
        if set(cibles) != CIBLES_PDF:
            raise CollecteRefusee("Deux pièces PDF attendues non retrouvées")
        return {
            "version": "controle-dce-dgac-public-v1",
            "url_archive_tiers": URL_ARCHIVE,
            "page_annonce_tiers": URL_NOTICE_SOURCE,
            "profil_officiel": URL_PROFIL_OFFICIEL,
            "identifiant_place": "3013529",
            "reference_acheteur_annoncee": "2026-SNARP-001",
            "source_archivage": "miroir_tiers_non_authentifie_comme_origine",
            "authenticite_de_la_version_place_verifiee": False,
            "concordance_identifiant_dans_les_noms": True,
            "octets_archive": len(octets),
            "sha256_archive": hashlib.sha256(octets).hexdigest(),
            "nombre_entrees_zip": len(entrees),
            "nombre_documents_pdf_controles": len(cibles),
            "documents_pdf": [cibles[nom] for nom in sorted(cibles)],
            "contenus_des_pieces_republies": False,
            "acte_contractuel_signe_verifie": False,
            "execution_de_prestation_etablie": False,
        }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.sortie.exists() or a.sortie.is_symlink():
            raise CollecteRefusee("Refus d'écraser un relevé")
        doc = analyser_archive(obtenir_archive())
        doc["collecte_effectuee_le"] = datetime.now(timezone.utc).isoformat()
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        a.sortie.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "controle": "réussi",
            "identifiant_place": doc["identifiant_place"],
            "sha256_archive": doc["sha256_archive"],
            "pdfs_controles": doc["nombre_documents_pdf_controles"],
            "origine_place_authentifiee": False,
        }, ensure_ascii=False))
    except (OSError, ValueError, BadZipFile) as exc:
        p.exit(1, f"Contrôle de pièce refusé : {exc}\n")


if __name__ == "__main__":
    main()
