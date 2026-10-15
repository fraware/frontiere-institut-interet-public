"""Vérifier le bilan DECP publié par reconstruction des deux relevés archivés.

Contrôle reproductible hors réseau : contrairement à une date de collecte,
un bilan d'identités et d'empreintes n'est valable que pour l'état précis
des deux relevés ayant servi à sa publication.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import tempfile

if __package__:
    from scripts.consolider_attributions_decp import (
        AIFE, DGFIP, RACINE, construire_index,
    )
else:
    from consolider_attributions_decp import (
        AIFE, DGFIP, RACINE, construire_index,
    )

BILAN = RACINE / "institutionnel/decp/bilan_index_unifie.json"
INDICATEURS = (
    "version",
    "sources",
    "fichiers_documentaires",
    "enregistrements_normalises_par_fichier",
    "identites_distinctes_par_siret_et_id_marche",
    "variantes_documentaires_distinctes",
    "repetitions_de_variantes_deja_observees",
    "identites_avec_plusieurs_variantes",
    "attestations_documentaires",
    "fichiers_sources_distincts",
    "notices_detaillees_manquantes",
    "controle_integrite_sqlite",
    "empreintes_releves_publies",
    "correspondances_boamp_verifiees",
    "besoins_encore_ouverts_demontres",
    "conformite_reglementaire_complete_verifiee",
    "statut",
)


class BilanDECPPerime(ValueError):
    """Un bilan public ne correspond plus aux fichiers réellement archivés."""


def comparer(publie: dict, reconstitue: dict) -> None:
    if not isinstance(publie, dict):
        raise BilanDECPPerime("Bilan documentaire non structuré.")
    for cle in INDICATEURS:
        if cle not in publie or type(publie[cle]) is not type(reconstitue[cle]):
            raise BilanDECPPerime("Champ du bilan absent ou incompatible : " + cle)
        if publie[cle] != reconstitue[cle]:
            raise BilanDECPPerime("Bilan DECP périmé ou incohérent : " + cle)


def verifier(
    *, aife: Path = AIFE, dgfip: Path = DGFIP, bilan: Path = BILAN
) -> dict:
    publie = json.loads(bilan.read_text(encoding="utf-8"))
    a = json.loads(aife.read_text(encoding="utf-8"))
    d = json.loads(dgfip.read_text(encoding="utf-8"))
    horodatage = publie.get("construit_le")
    if not isinstance(horodatage, str):
        raise BilanDECPPerime("Horodatage de construction absent.")
    with tempfile.TemporaryDirectory(prefix="frontiere-verification-decp-") as dossier:
        recalcule = construire_index(
            Path(dossier) / "verification.sqlite3",
            aife=a, dgfip=d, horodatage=horodatage,
        )
    comparer(publie, recalcule)
    return {
        "statut": "coherent_avec_les_deux_releves_archives",
        "index_public": str(bilan),
        "fichiers_documentaires": recalcule["fichiers_documentaires"],
        "identites_distinctes": recalcule[
            "identites_distinctes_par_siret_et_id_marche"
        ],
        "variantes_documentaires": recalcule[
            "variantes_documentaires_distinctes"
        ],
        "besoins_ouverts_demontres": 0,
        "couverture_nationale_exhaustive_demontree": False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aife", type=Path, default=AIFE)
    p.add_argument("--dgfip", type=Path, default=DGFIP)
    p.add_argument("--bilan", type=Path, default=BILAN)
    args = p.parse_args(argv)
    try:
        resultat = verifier(aife=args.aife, dgfip=args.dgfip, bilan=args.bilan)
    except (OSError, ValueError, UnicodeError, sqlite3.Error) as exc:
        p.exit(1, f"Vérification DECP refusée : {type(exc).__name__}: {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
