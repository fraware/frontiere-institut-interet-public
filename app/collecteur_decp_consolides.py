"""Importer les fichiers mensuels DECP consolidés en flux dans la base persistante.

Parcourt le catalogue national officiel, télécharge chaque fichier JSON vers
une archive locale durable, puis indexe les marchés par transaction de fichier.
Mémoire bornée par la taille d'une seule notice ; aucune liste nationale de
marchés n'est matérialisée en Python. Réutilise le parseur et l'index FTS5
existants. Les données sources brutes restent disponibles pour les reprises.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import time
from urllib.request import Request, build_opener

from scripts.collecter_catalogues_decp import telecharger as telecharger_catalogue
from scripts.ingerer_fichier_decp_json import (
    DocumentDECPInvalide, iterer_documents, normaliser_marche,
)
from scripts.indexer_attributions_decp_sqlite import SCHEMA, rechercher
from scripts.sonder_ressource_decp_aife import (
    RedirectionsRestreintes, _url_officielle,
)

CATALOGUE = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "donnees-essentielles-de-la-commande-publique-fichiers-consolides/"
)
PAGE = "https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides"
SOURCE = "mef_decp_consolides"
MENSUEL = re.compile(r"^decp-(20[0-9]{2})-(0[1-9]|1[0-2])\.json$")
UUID = re.compile(r"^[a-fA-F0-9-]{36}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_FICHIER = 2_000_000_000
MAX_NOTICES_PAR_FICHIER = 2_000_000
TAILLE_BLOC = 1_048_576
META = """
CREATE TABLE IF NOT EXISTS ressources_consolidees_decp (
    ressource_id TEXT PRIMARY KEY,
    titre TEXT NOT NULL,
    octets INTEGER NOT NULL,
    modification_declaree TEXT,
    empreinte_fichier TEXT NOT NULL,
    indexe_le TEXT NOT NULL,
    notices_lues INTEGER NOT NULL,
    notices_admises INTEGER NOT NULL,
    notices_rejetees INTEGER NOT NULL,
    concessions_omises INTEGER NOT NULL
);
"""


class CollecteConsolideeInvalide(ValueError):
    """Source absente, fichier tronqué ou structure de données non reconnue."""


def _maintenant() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connexion(base: Path) -> sqlite3.Connection:
    base.parent.mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(base, timeout=90)
    connexion.execute("PRAGMA foreign_keys=ON")
    connexion.execute("PRAGMA busy_timeout=90000")
    connexion.executescript(SCHEMA)
    connexion.executescript(META)
    return connexion


def _sha256(path: Path) -> str:
    resultat = hashlib.sha256()
    with path.open("rb") as flux:
        for bloc in iter(lambda: flux.read(TAILLE_BLOC), b""):
            resultat.update(bloc)
    return resultat.hexdigest()


def selectionner(fiche: dict, *, maximum_octets: int = MAX_FICHIER) -> tuple[list[dict], int]:
    """Découvrir tous les fichiers mensuels répertoriés, pas un échantillon."""
    if not isinstance(fiche, dict) or not isinstance(fiche.get("resources"), list):
        raise CollecteConsolideeInvalide("Catalogue officiel dépourvu de ressources.")
    if type(maximum_octets) is not int or maximum_octets < 1:
        raise ValueError("Limite de fichier incorrecte.")
    sorties, vus, exclus = [], set(), 0
    for element in fiche["resources"]:
        if not isinstance(element, dict):
            raise CollecteConsolideeInvalide("Ressource de catalogue non structurée.")
        titre = element.get("title")
        if not isinstance(titre, str) or not MENSUEL.fullmatch(titre):
            continue
        identifiant, taille = element.get("id"), element.get("filesize")
        if not isinstance(identifiant, str) or not UUID.fullmatch(identifiant):
            raise CollecteConsolideeInvalide("Identifiant de fichier mensuel invalide.")
        if identifiant in vus:
            raise CollecteConsolideeInvalide("Identifiant de ressource répété.")
        vus.add(identifiant)
        if str(element.get("format", "")).lower() != "json":
            raise CollecteConsolideeInvalide("Format du fichier mensuel inattendu.")
        if type(taille) is not int or taille <= 0:
            raise CollecteConsolideeInvalide("Taille officielle de fichier inconnue.")
        if taille > maximum_octets:
            exclus += 1
            continue
        url = _url_officielle(element.get("url"))
        sorties.append({
            "id": identifiant, "titre": titre, "taille": taille,
            "modifie_le": element.get("last_modified"),
            "url": url,
        })
    sorties.sort(key=lambda x: (x["titre"], x["modifie_le"] or "", x["id"]), reverse=True)
    return sorties, exclus


def _actuel(conn: sqlite3.Connection, selection: dict) -> bool:
    ancien = conn.execute(
        "SELECT octets, modification_declaree FROM ressources_consolidees_decp "
        "WHERE ressource_id=?", (selection["id"],)
    ).fetchone()
    return ancien == (selection["taille"], selection["modifie_le"])


def recevoir(selection: dict, repertoire: Path) -> tuple[Path, str]:
    """Télécharger en flux et garder les octets immuables par empreinte."""
    repertoire.mkdir(parents=True, exist_ok=True)
    fichier_partiel = None
    try:
        requete = Request(_url_officielle(selection["url"]), headers={
            "User-Agent": "FRONTIERE-consolides-DECP/1.0",
            "Accept-Encoding": "identity",
        })
        empreinte, taille = hashlib.sha256(), 0
        with build_opener(RedirectionsRestreintes()).open(requete, timeout=90) as response:
            if response.status != 200:
                raise CollecteConsolideeInvalide("Téléchargement officiel non abouti.")
            _url_officielle(response.geturl())
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=repertoire, prefix=".decp-", delete=False
            ) as sortie:
                fichier_partiel = Path(sortie.name)
                while bloc := response.read(TAILLE_BLOC):
                    taille += len(bloc)
                    if taille > selection["taille"] or taille > MAX_FICHIER:
                        raise CollecteConsolideeInvalide("Fichier plus grand que déclaré.")
                    empreinte.update(bloc)
                    sortie.write(bloc)
                sortie.flush()
                os.fsync(sortie.fileno())
        if taille != selection["taille"]:
            raise CollecteConsolideeInvalide("Fichier incomplet par rapport au catalogue.")
        sha = empreinte.hexdigest()
        destination = repertoire / f'{selection["id"]}-{sha}.json'
        if destination.exists() and _sha256(destination) != sha:
            raise CollecteConsolideeInvalide("Archive persistante déjà présente, mais altérée.")
        os.replace(fichier_partiel, destination)
        fichier_partiel = None
        return destination, sha
    finally:
        if fichier_partiel is not None:
            fichier_partiel.unlink(missing_ok=True)


def _version(ligne: dict) -> str:
    canon = json.dumps(
        ligne, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def importer(
    base: Path, selection: dict, fichier: Path, *,
    sha: str | None = None,
    plafond_notices: int = MAX_NOTICES_PAR_FICHIER,
) -> dict:
    """Insérer sans mémoire proportionnelle au fichier. Tout ou rien par source."""
    if not isinstance(selection.get("id"), str) or not UUID.fullmatch(selection["id"]):
        raise CollecteConsolideeInvalide("Identifiant de ressource absent.")
    if (not isinstance(selection.get("taille"), int)
        or not 0 < selection["taille"] <= MAX_FICHIER
        or fichier.stat().st_size != selection["taille"]):
        raise CollecteConsolideeInvalide("Taille du fichier différente du catalogue.")
    empreinte = _sha256(fichier)
    if sha is not None and sha != empreinte:
        raise CollecteConsolideeInvalide("Empreinte brute du fichier différente.")
    if type(plafond_notices) is not int or not 1 <= plafond_notices <= 5_000_000:
        raise CollecteConsolideeInvalide("Limite des notices incorrecte.")
    compte = Counter()
    connection = _connexion(base)
    try:
        connection.execute("BEGIN IMMEDIATE")
        cle = connection.execute(
            "SELECT 1 FROM fichiers_sources WHERE empreinte_fichier=? "
            "AND source_catalogue=? AND ressource_id=?",
            (empreinte, SOURCE, selection["id"]),
        ).fetchone()
        if cle is None:
            connection.execute(
                "INSERT INTO fichiers_sources(empreinte_fichier,source_catalogue,"
                "ressource_id,page_catalogue,date_premiere_importation) "
                "VALUES(?,?,?,?,?)",
                (empreinte, SOURCE, selection["id"], PAGE, _maintenant()),
            )
            with fichier.open("r", encoding="utf-8-sig") as flux:
                for categorie, notice in iterer_documents(
                    flux, plafond_notices=plafond_notices,
                    plafond_source_max=5_000_000,
                ):
                    compte["objets_lus"] += 1
                    if categorie != "marche":
                        compte["concessions_omises"] += 1
                        continue
                    compte["marches_lus"] += 1
                    try:
                        marche = normaliser_marche(notice)
                    except DocumentDECPInvalide:
                        compte["rejets"] += 1
                        continue
                    compte["notices_admises"] += 1
                    siret, identifiant = marche["acheteur_siret"], marche["id_marche"]
                    version = _version(marche)
                    connection.execute(
                        "INSERT OR IGNORE INTO marches (acheteur_siret,id_marche) "
                        "VALUES (?,?)", (siret, identifiant),
                    )
                    ajout = connection.execute(
                        "INSERT OR IGNORE INTO versions "
                        "(acheteur_siret,id_marche,empreinte_version,objet,code_cpv,"
                        "date_notification,date_publication_declaree,montant_euros_ht,nature) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (siret, identifiant, version, marche["objet"], marche["code_cpv"],
                         marche["date_notification"], marche["date_publication_declaree"],
                         marche["montant_euros_ht_declare"], marche["nature"]),
                    )
                    if ajout.rowcount:
                        recherche_id = "\x1f".join((siret, identifiant, version))
                        connection.execute(
                            "INSERT INTO recherche_marches(cle,objet) VALUES(?,?)",
                            (recherche_id, marche["objet"]),
                        )
                        compte["versions_nouvelles"] += 1
                    resultat = connection.execute(
                        "INSERT OR IGNORE INTO attestations "
                        "(acheteur_siret,id_marche,empreinte_version,empreinte_fichier,"
                        "source_catalogue,ressource_id,observe_le) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (siret, identifiant, version, empreinte,
                         SOURCE, selection["id"], _maintenant()),
                    )
                    compte["attestations_nouvelles"] += resultat.rowcount
            if not compte["notices_admises"]:
                raise CollecteConsolideeInvalide("Aucun marché exploitable dans le fichier.")
            compte["fichiers_nouveaux"] = 1
        connection.execute(
            "INSERT INTO ressources_consolidees_decp "
            "(ressource_id,titre,octets,modification_declaree,empreinte_fichier,indexe_le,"
            "notices_lues,notices_admises,notices_rejetees,concessions_omises) "
            "VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(ressource_id) DO UPDATE SET "
            "titre=excluded.titre,octets=excluded.octets,"
            "modification_declaree=excluded.modification_declaree,"
            "empreinte_fichier=excluded.empreinte_fichier,indexe_le=excluded.indexe_le,"
            "notices_lues=excluded.notices_lues,"
            "notices_admises=excluded.notices_admises,"
            "notices_rejetees=excluded.notices_rejetees,"
            "concessions_omises=excluded.concessions_omises",
            (selection["id"], selection["titre"], selection["taille"],
             selection["modifie_le"], empreinte, _maintenant(),
             compte["marches_lus"], compte["notices_admises"],
             compte["rejets"], compte["concessions_omises"]),
        )
        connection.commit()
        return {"ressource_id": selection["id"], "titre": selection["titre"],
                "empreinte_sha256": empreinte, **dict(compte)}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def etat(base: Path) -> dict:
    if not base.is_file():
        return {"ressources_mensuelles": 0, "identites_marche": 0, "versions": 0}
    with _connexion(base) as conn:
        return {
            "ressources_mensuelles": conn.execute(
                "SELECT COUNT(*) FROM ressources_consolidees_decp"
            ).fetchone()[0],
            "identites_marche": conn.execute(
                "SELECT COUNT(*) FROM marches"
            ).fetchone()[0],
            "versions": conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0],
            "attestations": conn.execute(
                "SELECT COUNT(*) FROM attestations"
            ).fetchone()[0],
        }


def cycle(base: Path, repertoire: Path, *, maximum: int = 2,
          catalogue=None, telecharge=recevoir) -> dict:
    if type(maximum) is not int or not 1 <= maximum <= 20:
        raise ValueError("Nombre de fichiers par cycle incorrect.")
    fiche = catalogue if catalogue is not None else telecharger_catalogue(
        {"url": CATALOGUE}
    )
    selections, exclus = selectionner(fiche)
    with _connexion(base) as conn:
        restantes = [s for s in selections if not _actuel(conn, s)]
    bilan = {"sources_detectees": len(selections), "hors_plafond": exclus,
             "fichiers_tentes": 0, "fichiers_importes": 0, "erreurs": [],
             "octets_importes": 0, "notices_lues": 0,
             "notices_admises": 0, "rejets": 0}
    for selection in restantes[:maximum]:
        bilan["fichiers_tentes"] += 1
        try:
            archive, sha = telecharge(selection, repertoire)
            resultat = importer(base, selection, archive, sha=sha)
            bilan["fichiers_importes"] += resultat.get("fichiers_nouveaux", 0)
            bilan["octets_importes"] += selection["taille"]
            bilan["notices_lues"] += resultat.get("marches_lus", 0)
            bilan["notices_admises"] += resultat.get("notices_admises", 0)
            bilan["rejets"] += resultat.get("rejets", 0)
        except (ValueError, OSError, sqlite3.Error, UnicodeError) as exc:
            bilan["erreurs"].append({
                "titre": selection["titre"],
                "ressource_id": selection["id"],
                "erreur": type(exc).__name__,
            })
    bilan["fichiers_restants"] = max(0, len(restantes) - maximum)
    bilan.update(etat(base))
    bilan["controle_le"] = _maintenant()
    return bilan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--repertoire", required=True, type=Path)
    sous = parser.add_subparsers(dest="action", required=True)
    run = sous.add_parser("collecter")
    run.add_argument("--maximum", type=int, default=2)
    run = sous.add_parser("suivre")
    run.add_argument("--maximum", type=int, default=2)
    run.add_argument("--intervalle", type=int, default=21600)
    sous.add_parser("etat")
    recherche = sous.add_parser("rechercher")
    recherche.add_argument("expression")
    recherche.add_argument("--limite", type=int, default=25)
    args = parser.parse_args(argv)
    try:
        if args.action == "etat":
            resultat = etat(args.base)
        elif args.action == "rechercher":
            resultat = rechercher(args.base, args.expression, args.limite)
        else:
            if args.action == "suivre" and not 3600 <= args.intervalle <= 604800:
                parser.error("L'intervalle doit être compris entre 1 heure et 7 jours.")
            while True:
                resultat = cycle(args.base, args.repertoire, maximum=args.maximum)
                print(json.dumps(resultat, ensure_ascii=False, sort_keys=True), flush=True)
                if args.action != "suivre":
                    return 0 if not resultat["erreurs"] else 1
                time.sleep(args.intervalle)
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error, UnicodeError) as exc:
        print(f"DECP consolidés : {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
