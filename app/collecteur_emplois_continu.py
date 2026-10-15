"""Actualiser les offres d'emploi public sans publication intermédiaire GitHub.

Le catalogue data.gouv.fr est interrogé à intervalles configurables.
Le CSV de la DGAFP n'est re-téléchargé que si une nouvelle version est
déclarée ou si les partitions locales ne correspondent plus au manifeste.
Les extraits sont ensuite indexés dans la base SQL persistante.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

from app.plateforme_emplois import StockageEmplois
from scripts.collecter_besoins_publics import relever_emplois
from scripts.sonder_structure_offres_publiques import (
    choisir, enregistrer, lire_en_tete,
)
from scripts.extraire_offres_publiques import executer as extraire, partitions_verifiees


def cycle(stockage: StockageEmplois, repertoire: Path, *, maintenant=None,
          relever=relever_emplois, sonder=lire_en_tete, extraction=extraire) -> dict:
    """Exécuter une chaîne catalogue → schéma → extraction → persistance.

    Les anciennes captures SQL et partitions restent en place en cas d'échec
    de collecte. Les changements de version n'effacent pas l'historique.
    """
    maintenant = maintenant or datetime.now(timezone.utc)
    if maintenant.tzinfo is None:
        raise ValueError("Date de collecte sans fuseau horaire.")
    inventaire, releve = relever(maintenant=maintenant)
    if inventaire.get("licence_declaree") not in ("lov1", "lov2"):
        raise ValueError("Licence déclarée non reconnue pour le catalogue officiel.")
    fichier = choisir(inventaire["ressources"])
    manifeste_path = repertoire / "manifest_offres_postes.json"
    ancien = json.loads(manifeste_path.read_text(encoding="utf-8")
                       ) if manifeste_path.is_file() else {}
    inchangé = (
        ancien.get("version") == "emplois-publics-extraits-v1"
        and ancien.get("source_id") == fichier["id"]
        and ancien.get("source_modifie_le") == fichier.get("modifie_le")
        and ancien.get("source_url") == fichier["url"]
        and partitions_verifiees(repertoire, ancien)
    )
    if inchangé:
        bilan_extraction = {"etat": "inchangé"}
    else:
        entete = sonder(fichier["url"])
        if entete.get("separateur") != "point-virgule":
            raise ValueError("Le format officiel CSV attendu a changé.")
        # Les deux fichiers sont conservés localement pour réutiliser le
        # processus d'extraction éprouvé dans le dépôt.
        schema = {
            **entete,
            "source_id": fichier["id"],
            "titre_fichier": fichier.get("titre"),
            "date_modification_declaree": fichier.get("modifie_le"),
            "source": inventaire.get("jeu"),
        }
        enregistrer(repertoire / "ressources_emplois_publics.json", inventaire)
        enregistrer(repertoire / "schema_emplois_publics.json", schema)
        bilan_extraction = extraction(repertoire)
    # Si le catalogue n'a pas changé, le manifeste et les partitions sont
    # suffisants pour rattraper une ingestion SQL interrompue.
    bilan_sql = stockage.importer(repertoire)
    return {
        "source": "Choisir le service public",
        "consulte_le": maintenant.astimezone(timezone.utc).replace(microsecond=0).isoformat(),
        "fichier_officiel": fichier["id"],
        "extraction": bilan_extraction.get("etat", "actualisée"),
        "base": bilan_sql["etat"],
        "offres_du_dernier_cliche": bilan_sql["offres_du_dernier_cliche"],
        "captures_persistantes": bilan_sql["captures"],
        "modification_source_declaree": fichier.get("modifie_le"),
        "catalogue_controle_le": releve.get("controle_le"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="URL SQLAlchemy durable")
    parser.add_argument("--repertoire", type=Path, required=True,
                        help="Dossier privé d'extraction des offres")
    parser.add_argument("--suivre", action="store_true",
                        help="Interroger régulièrement le catalogue officiel")
    parser.add_argument("--intervalle", type=int, default=21600,
                        help="Secondes entre les passages, défaut six heures")
    args = parser.parse_args(argv)
    if args.suivre and not 3600 <= args.intervalle <= 604800:
        parser.error("La période de suivi doit être comprise entre une heure et sept jours.")
    stockage = StockageEmplois(args.base)
    while True:
        try:
            resultat = cycle(stockage, args.repertoire)
            print(json.dumps(resultat, ensure_ascii=False, sort_keys=True), flush=True)
        except (ValueError, OSError, KeyError, TypeError, UnicodeError,
                csv.Error, json.JSONDecodeError) as exc:
            print(json.dumps({
                "source": "emplois_publics", "collecte_reussie": False,
                "erreur": type(exc).__name__, "detail": str(exc),
                "observe_le": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False), file=sys.stderr, flush=True)
            if not args.suivre:
                return 1
        if not args.suivre:
            return 0
        time.sleep(args.intervalle)


if __name__ == "__main__":
    sys.exit(main())
