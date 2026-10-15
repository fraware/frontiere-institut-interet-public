"""Acquisition DECP AIFE/DGFiP vers un index local persistant.

Réemploie exclusivement les interfaces, extractions et vérificateurs déjà
présents dans le dépôt. Les inventaires et les relevés sont conservés sur
volume persistant, indépendamment des propositions de fusion GitHub.

Portée : ressources publiques de taille bornée, sans prétention à la
couverture complète des contrats français. SQLite FTS5 reste requis.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from typing import Callable

from scripts.collecter_catalogues_decp import (
    executer as actualiser_catalogues,
    telecharger as telecharger_catalogue,
)
from scripts.consolider_attributions_decp import rapports_dgfip
from scripts.indexer_attributions_decp_sqlite import (
    IndexDECPInvalide, importer as importer_rapport,
    rechercher as rechercher_marches, verifier_rapport,
)
from scripts.sonder_ressource_decp_aife import (
    choisir_ressource as choisir_aife,
    executer as sonder_aife,
)
from scripts.sonder_lot_decp_dgfip import executer as sonder_dgfip

AIFE_URL = "https://www.data.gouv.fr/api/1/datasets/api-decp/"
DGFIP_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024/"
)
NOMS = ("etat_ressources.json", "sonde_aife_json.json", "lot_dgfip_xml.json")
MAX_FICHIER_JSON = 60 * 1024 * 1024


class CycleDECPInvalide(ValueError):
    """Un élément nécessaire au cycle de collecte manque ou est incohérent."""


def _charger(chemin: Path) -> dict:
    if not chemin.exists():
        return {}
    if chemin.stat().st_size > MAX_FICHIER_JSON:
        raise CycleDECPInvalide("Fichier de suivi DECP supérieur à la limite.")
    resultat = json.loads(chemin.read_text(encoding="utf-8"))
    if not isinstance(resultat, dict):
        raise CycleDECPInvalide("Document JSON de suivi non structuré.")
    return resultat


def _enregistrer(chemin: Path, document: dict) -> None:
    """Écriture atomique locale de l'état d'un collecteur."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    donnees = (json.dumps(document, ensure_ascii=False, sort_keys=True,
                          indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(donnees) > MAX_FICHIER_JSON:
        raise CycleDECPInvalide("État DECP trop volumineux pour être publié.")
    temporaire: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=chemin.parent, prefix=".decp-", delete=False
        ) as flux:
            temporaire = flux.name
            flux.write(donnees)
            flux.flush()
            os.fsync(flux.fileno())
        os.replace(temporaire, chemin)
    finally:
        if temporaire and os.path.exists(temporaire):
            os.unlink(temporaire)


def _identite_rapport(releve: dict) -> tuple[str, str, str]:
    return (
        releve["source_catalogue"],
        releve["ressource_id"],
        releve["sha256_fichier_brut"],
    )


def importer_archives(base: Path, archives: Path, dossier: Path) -> dict:
    """Amorcer la base et l'état local à partir des relevés déjà publiés.

    Une ancienne archive n'écrase jamais un état local préexistant : cela
    éviterait de revenir en arrière sur un curseur d'acquisition autonome.
    Les fichiers sources archivés sont lus sans jamais les modifier.
    """
    avant = etat_index(base)["fichiers"]
    for nom in NOMS:
        original = archives / nom
        cible = dossier / nom
        if not cible.is_file() and not original.is_file():
            continue
        # Préférer un état local déjà actualisé au corpus historique monté.
        # Réimporter dans la base les relevés déjà présents pour réparer une
        # interruption entre l'écriture d'un état et sa projection SQL.
        existait = cible.is_file()
        doc = _charger(cible if existait else original)
        if nom == "sonde_aife_json.json":
            verifier_rapport(doc)
            importer_rapport(base, doc)
        elif nom == "lot_dgfip_xml.json":
            for releve in rapports_dgfip(doc):
                importer_rapport(base, releve)
        elif doc.get("version") != "decp-metadonnees-v1":
            raise CycleDECPInvalide("État du catalogue historique incompatible.")
        if not existait:
            _enregistrer(cible, doc)
    final = etat_index(base)
    return {"releves_documentaires_importes": final["fichiers"] - avant, **final}


def etat_index(base: Path) -> dict:
    """Comptages de l'index SQL, même avant sa première alimentation."""
    if not base.is_file():
        return {"marches_distincts": 0, "versions": 0, "fichiers": 0,
                "attestations": 0}
    with sqlite3.connect(base) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        attendues = {"marches", "versions", "fichiers_sources", "attestations"}
        if not attendues.issubset(tables):
            raise CycleDECPInvalide("Schéma de l'index DECP absent ou incomplet.")
        return {
            "marches_distincts": conn.execute(
                "SELECT COUNT(*) FROM marches"
            ).fetchone()[0],
            "versions": conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0],
            "fichiers": conn.execute(
                "SELECT COUNT(*) FROM fichiers_sources"
            ).fetchone()[0],
            "attestations": conn.execute(
                "SELECT COUNT(*) FROM attestations"
            ).fetchone()[0],
        }


def cycle(
    base: Path,
    dossier: Path,
    config: dict,
    *,
    actualiser: Callable = actualiser_catalogues,
    telecharger: Callable = telecharger_catalogue,
    aife: Callable = sonder_aife,
    dgfip: Callable = sonder_dgfip,
    selectionner_aife: Callable = choisir_aife,
) -> dict:
    """Interroger les catalogues puis ingérer les nouveaux fichiers accessibles.

    Une source peut échouer sans effacer le dernier état des autres.
    L'avancement d'un curseur intervient après importation de ses notices.
    """
    dossier.mkdir(parents=True, exist_ok=True)
    if (etat_index(base)["fichiers"] == 0
            and any((dossier / nom).is_file() for nom in NOMS[1:])):
        # Restaurer d'abord les derniers relevés locaux si le fichier SQLite
        # a disparu, avant de consulter les sources.
        importer_archives(base, dossier, dossier)
    catalogues_chemin = dossier / NOMS[0]
    precedent_catalogues = _charger(catalogues_chemin)
    etat = actualiser(config, precedent_catalogues, recuperer=telecharger)
    _enregistrer(catalogues_chemin, etat)

    resultats = {"source": "DECP", "catalogues_actualises": etat.get("sources_reussies"),
                 "catalogues_indisponibles": etat.get("sources_echouees", []),
                 "ressources_nouvelles": 0, "erreurs_sources": []}
    # Chaque fichier est attesté par les vérifications internes des collecteurs.
    essais = (
        ("AIFE", AIFE_URL, NOMS[1]),
        ("DGFiP", DGFIP_URL, NOMS[2]),
    )
    for nom, url, fichier_nom in essais:
        chemin = dossier / fichier_nom
        ancien = _charger(chemin)
        try:
            fiche = telecharger({"url": url})
            if nom == "AIFE":
                selection = selectionner_aife(etat, fiche)
                source_aife = next(
                    (x for x in etat.get("catalogues", [])
                     if x.get("source_id") == "aife_api_decp"), {}
                )
                metadonnee = next(
                    (x for x in source_aife.get("ressources_recentes", [])
                     if x.get("id") == selection["id"]), {}
                )
                signature = (
                    selection["id"], selection.get("taille_octets_declaree"),
                    metadonnee.get("modifie_le"),
                )
                ancien_selection = ancien.get("_selection_source")
                # Les collecteurs ne téléchargent pas une ressource inchangée
                # à chaque passage. Une relecture forcée reste réalisable
                # en supprimant uniquement la sélection mémorisée.
                if isinstance(ancien_selection, list) and tuple(ancien_selection) == signature:
                    # Rejouer au besoin cette source si la base n'en contient
                    # plus l'attestation, indépendamment du dernier curseur.
                    verifier_rapport(ancien)
                    importer_rapport(base, ancien)
                    continue
                nouveau = aife(etat, fiche)
                verifier_rapport(nouveau)
                avant = etat_index(base)["fichiers"]
                importer_rapport(base, nouveau)
                nouveau["_selection_source"] = list(signature)
                _enregistrer(chemin, nouveau)
                resultats["ressources_nouvelles"] += (
                    etat_index(base)["fichiers"] - avant
                )
            else:
                nouveau = dgfip(etat, fiche, ancien)
                if nouveau == ancien:
                    continue
                if not isinstance(nouveau, dict) or not nouveau.get("fichiers"):
                    raise CycleDECPInvalide("Aucun fichier DGFiP complet dans l'état reçu.")
                anciennes_versions = {
                    _identite_rapport(x): json.dumps(
                        x["marches_extraits"], ensure_ascii=False,
                        sort_keys=True, separators=(",", ":")
                    )
                    for x in rapports_dgfip(ancien)
                } if ancien.get("fichiers") else {}
                rapports = rapports_dgfip(nouveau)
                nouvelle_liste = [
                    x for x in rapports
                    if anciennes_versions.get(_identite_rapport(x)) != json.dumps(
                        x["marches_extraits"], ensure_ascii=False,
                        sort_keys=True, separators=(",", ":")
                    )
                ]
                avant = etat_index(base)["fichiers"]
                for releve in nouvelle_liste:
                    importer_rapport(base, releve)
                _enregistrer(chemin, nouveau)
                resultats["ressources_nouvelles"] += (
                    etat_index(base)["fichiers"] - avant
                )
        except (OSError, ValueError, KeyError, TypeError, UnicodeError,
                json.JSONDecodeError) as exc:
            resultats["erreurs_sources"].append({
                "source": nom, "erreur": type(exc).__name__,
            })
    resultats.update(etat_index(base))
    resultats["observe_le"] = datetime.now(timezone.utc).replace(
        microsecond=0).isoformat()
    return resultats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path,
                        help="Fichier SQLite persistant, distinct des bases BOAMP/CSP")
    parser.add_argument("--repertoire", required=True, type=Path,
                        help="Répertoire de suivi en écriture sur volume persistant")
    parser.add_argument("--config", type=Path,
                        default=Path("institutionnel/decp/sources_v1.json"))
    parser.add_argument("--archives", type=Path,
                        help="Relevés historiques montés en lecture seule")
    sous = parser.add_subparsers(dest="action", required=True)
    sous.add_parser("amorcer")
    sous.add_parser("collecter")
    suivi = sous.add_parser("suivre")
    suivi.add_argument("--intervalle", type=int, default=21600)
    sous.add_parser("etat")
    recherche = sous.add_parser("rechercher")
    recherche.add_argument("expression")
    recherche.add_argument("--limite", type=int, default=25)
    args = parser.parse_args(argv)
    try:
        if args.action == "amorcer":
            if args.archives is None:
                parser.error("L'option --archives est nécessaire pour amorcer.")
            sortie = importer_archives(args.base, args.archives, args.repertoire)
        elif args.action == "etat":
            sortie = etat_index(args.base)
        elif args.action == "rechercher":
            sortie = rechercher_marches(args.base, args.expression, args.limite)
        else:
            if args.action == "suivre" and not 3600 <= args.intervalle <= 604800:
                parser.error("Intervalle autorisé : de 1 heure à 7 jours.")
            config = _charger(args.config)
            if args.archives:
                importer_archives(args.base, args.archives, args.repertoire)
            while True:
                sortie = cycle(args.base, args.repertoire, config)
                print(json.dumps(sortie, ensure_ascii=False, sort_keys=True), flush=True)
                if args.action != "suivre":
                    return 0 if not sortie["erreurs_sources"] else 1
                time.sleep(args.intervalle)
        print(json.dumps(sortie, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"DECP : {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
