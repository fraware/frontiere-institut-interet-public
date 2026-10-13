"""Construire un index local, reproductible et inter-sources de marchés AIFE/DGFiP.

Tous les relevés doivent être intégralement conservés et satisfaire le profil
réduit. Le fichier SQLite est entièrement reconstruit puis remplacé d'un coup :
un relevé tronqué ou invalide ne modifie pas l'index précédent. Les identités
sont des couples SIRET de l'acheteur + identifiant du marché ; des descriptions
différentes de même identité restent des variantes documentaires, sans être
qualifiées automatiquement d'avenants contractuels.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

if __package__:
    from scripts.indexer_attributions_decp_sqlite import (
        RACINE, IndexDECPInvalide, importer, verifier_rapport,
    )
else:
    from indexer_attributions_decp_sqlite import (
        RACINE, IndexDECPInvalide, importer, verifier_rapport,
    )

AIFE = RACINE / "institutionnel/decp/sonde_aife_json.json"
DGFIP = RACINE / "institutionnel/decp/lot_dgfip_xml.json"
VERSION_REGISTRE = "lot-decp-dgfip-xml-v1"
PAGE_DGFIP = (
    "https://www.data.gouv.fr/datasets/"
    "donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024"
)
MAX_FICHIERS = 2000


def rapports_dgfip(registre: dict) -> list[dict]:
    """Adapter chaque XML historique à une attestation source, sans perdre les manques."""
    if not isinstance(registre, dict) or (
        registre.get("version") != VERSION_REGISTRE
        or registre.get("source_catalogue") != "dgfip_pes_marche"
        or registre.get("page_catalogue") != PAGE_DGFIP
    ):
        raise IndexDECPInvalide("Registre DGFiP ou provenance invalide")
    horodatage = registre.get("controle_le")
    if not isinstance(horodatage, str):
        raise IndexDECPInvalide("Horodatage du registre absent")
    fichiers = registre.get("fichiers")
    if not isinstance(fichiers, list) or not 0 < len(fichiers) <= MAX_FICHIERS:
        raise IndexDECPInvalide("Liste des fichiers hors limites")
    rapports: list[dict] = []
    cles = set()
    for fichier in fichiers:
        if not isinstance(fichier, dict):
            raise IndexDECPInvalide("Métadonnées de fichier non structurées")
        releve = {
            "version": "decp-fichier-xml-v1",
            "source_catalogue": "dgfip_pes_marche",
            "page_catalogue": PAGE_DGFIP,
            "ressource_id": fichier.get("id"),
            "sha256_fichier_brut": fichier.get("empreinte_sha256"),
            "releve_le": horodatage,
            "extraits_plafonnes": fichier.get("extraits_plafonnes"),
            "releves": fichier.get("releves"),
            "marches_extraits": fichier.get("marches_extraits"),
        }
        verifier_rapport(releve)
        cle = (releve["ressource_id"], releve["sha256_fichier_brut"])
        if cle in cles:
            raise IndexDECPInvalide("Attestation de fichier identique répétée")
        cles.add(cle)
        rapports.append(releve)
    return rapports


def construire_index(
    base: Path, *, aife: dict, dgfip: dict, horodatage: str | None = None
) -> dict:
    """Reconstruire la base dans un fichier temporaire, puis la publier atomiquement."""
    if not isinstance(aife, dict):
        raise IndexDECPInvalide("Relevé AIFE non structuré")
    verifier_rapport(aife)
    rapports = [aife] + rapports_dgfip(dgfip)
    comptes_sources = {
        "aife_api_decp": 1,
        "dgfip_pes_marche": len(rapports) - 1,
    }
    nombre_enregistrements = sum(
        len(releve["marches_extraits"]) for releve in rapports
    )
    date_generation = horodatage or datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        if datetime.fromisoformat(date_generation).tzinfo is None:
            raise ValueError("Fuseau horaire absent")
    except (ValueError, TypeError) as exc:
        raise IndexDECPInvalide("Horodatage de génération incorrect") from exc
    if not base.parent.exists():
        base.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".decp-index-", dir=base.parent) as dossier:
        temporaire = Path(dossier) / "index.sqlite3"
        for releve in rapports:
            importer(temporaire, releve)
        con = sqlite3.connect(temporaire)
        try:
            nombre_identites = con.execute("SELECT COUNT(*) FROM marches").fetchone()[0]
            nombre_versions = con.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
            fichiers_suivis = con.execute(
                "SELECT COUNT(*) FROM fichiers_sources"
            ).fetchone()[0]
            identites_variantes = con.execute(
                """SELECT COUNT(*) FROM (
                    SELECT acheteur_siret, id_marche
                    FROM versions GROUP BY acheteur_siret, id_marche
                    HAVING COUNT(*) > 1
                )"""
            ).fetchone()[0]
            attestations = con.execute(
                "SELECT COUNT(*) FROM attestations"
            ).fetchone()[0]
            integrite = con.execute("PRAGMA integrity_check").fetchone()[0]
            if integrite != "ok":
                raise IndexDECPInvalide("Contrôle d'intégrité SQLite incorrect")
            if con.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise IndexDECPInvalide("Lien de provenance SQLite invalide")
        finally:
            con.close()
        if nombre_versions > nombre_enregistrements or nombre_identites > nombre_versions:
            raise IndexDECPInvalide("Comptages d'identités et de versions incompatibles")
        rapport = {
            "version": "index-unifie-decp-v1",
            "construit_le": date_generation,
            "sources": comptes_sources,
            "fichiers_documentaires": len(rapports),
            "enregistrements_normalises_par_fichier": nombre_enregistrements,
            "identites_distinctes_par_siret_et_id_marche": nombre_identites,
            "variantes_documentaires_distinctes": nombre_versions,
            "repetitions_de_variantes_deja_observees":
                nombre_enregistrements - nombre_versions,
            "identites_avec_plusieurs_variantes": identites_variantes,
            "attestations_documentaires": attestations,
            "fichiers_sources_distincts": fichiers_suivis,
            "notices_detaillees_manquantes": 0,
            "controle_integrite_sqlite": integrite,
            "empreintes_releves_publies": {
                "aife": hashlib.sha256(json.dumps(
                    aife, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False
                ).encode("utf-8")).hexdigest(),
                "dgfip": hashlib.sha256(json.dumps(
                    dgfip, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False
                ).encode("utf-8")).hexdigest(),
            },
            "correspondances_boamp_verifiees": 0,
            "besoins_encore_ouverts_demontres": 0,
            "conformite_reglementaire_complete_verifiee": False,
            "statut": "deux_releves_publics_complets_sans_couverture_nationale",
        }
        os.replace(temporaire, base)
    return rapport


def main() -> None:
    """Assembler en local les données de marchés publiques déjà archivées."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aife", type=Path, default=AIFE)
    parser.add_argument("--dgfip", type=Path, default=DGFIP)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--rapport", type=Path)
    args = parser.parse_args()
    try:
        aife = json.loads(args.aife.read_text(encoding="utf-8"))
        dgfip = json.loads(args.dgfip.read_text(encoding="utf-8"))
        rapport = construire_index(args.base, aife=aife, dgfip=dgfip)
        if args.rapport:
            args.rapport.parent.mkdir(parents=True, exist_ok=True)
            tmp = args.rapport.with_name(args.rapport.name + ".tmp")
            tmp.write_text(json.dumps(rapport, ensure_ascii=False, sort_keys=True,
                                      indent=2, allow_nan=False) + "\n", encoding="utf-8")
            tmp.replace(args.rapport)
        print(json.dumps(rapport, ensure_ascii=False, sort_keys=True, indent=2))
    except (ValueError, OSError, UnicodeError, sqlite3.Error) as exc:
        parser.exit(1, f"Index inter-sources refusé : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
