"""Indexer localement les marchés DECP observés sans les assimiler à des besoins.

L'importateur rejette tout relevé réduit qui prétendrait représenter le fichier
complet. Les versions sont immuables et chaque provenance de fichier est
conservée. SQLite FTS5 donne une recherche locale, sans service hébergé.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

RACINE = Path(__file__).resolve().parents[1]
RELEVE = RACINE / "institutionnel/decp/sonde_aife_json.json"
SHA = re.compile(r"^[0-9a-f]{64}$")
SIRET = re.compile(r"^[0-9]{14}$")
MAX_MARCHES = 1000
CATALOGUES = {
    ("decp-fichier-json-v1", "aife_api_decp"):
        "https://www.data.gouv.fr/datasets/api-decp",
    ("decp-fichier-xml-v1", "dgfip_pes_marche"):
        ("https://www.data.gouv.fr/datasets/"
         "donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024"),
}


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS marches (
    acheteur_siret TEXT NOT NULL,
    id_marche TEXT NOT NULL,
    PRIMARY KEY (acheteur_siret, id_marche)
);
CREATE TABLE IF NOT EXISTS versions (
    acheteur_siret TEXT NOT NULL,
    id_marche TEXT NOT NULL,
    empreinte_version TEXT NOT NULL,
    objet TEXT NOT NULL,
    code_cpv TEXT,
    date_notification TEXT,
    date_publication_declaree TEXT,
    montant_euros_ht REAL,
    nature TEXT,
    PRIMARY KEY (acheteur_siret, id_marche, empreinte_version),
    FOREIGN KEY (acheteur_siret, id_marche)
      REFERENCES marches (acheteur_siret, id_marche)
);
CREATE TABLE IF NOT EXISTS fichiers_sources (
    empreinte_fichier TEXT NOT NULL,
    source_catalogue TEXT NOT NULL,
    ressource_id TEXT NOT NULL,
    page_catalogue TEXT NOT NULL,
    date_premiere_importation TEXT NOT NULL,
    PRIMARY KEY (empreinte_fichier, source_catalogue, ressource_id)
);
CREATE TABLE IF NOT EXISTS attestations (
    acheteur_siret TEXT NOT NULL,
    id_marche TEXT NOT NULL,
    empreinte_version TEXT NOT NULL,
    empreinte_fichier TEXT NOT NULL,
    source_catalogue TEXT NOT NULL,
    ressource_id TEXT NOT NULL,
    observe_le TEXT NOT NULL,
    PRIMARY KEY (acheteur_siret, id_marche, empreinte_version,
                 empreinte_fichier, source_catalogue, ressource_id),
    FOREIGN KEY (acheteur_siret, id_marche, empreinte_version)
      REFERENCES versions (acheteur_siret, id_marche, empreinte_version),
    FOREIGN KEY (empreinte_fichier, source_catalogue, ressource_id)
      REFERENCES fichiers_sources (empreinte_fichier, source_catalogue, ressource_id)
);
CREATE INDEX IF NOT EXISTS idx_versions_cpv ON versions (code_cpv);
CREATE INDEX IF NOT EXISTS idx_versions_notification ON versions (date_notification);
CREATE VIRTUAL TABLE IF NOT EXISTS recherche_marches
    USING fts5(cle UNINDEXED, objet, tokenize='unicode61 remove_diacritics 2');
"""


class IndexDECPInvalide(ValueError):
    """Dossier incomplet, valeur incohérente ou traitement hors limites."""


def _date(valeur: object, champ: str, *, absent: bool = False) -> str | None:
    if absent and valeur is None:
        return None
    if not isinstance(valeur, str):
        raise IndexDECPInvalide(f"Date incorrecte : {champ}")
    try:
        return date.fromisoformat(valeur).isoformat()
    except ValueError as exc:
        raise IndexDECPInvalide(f"Date impossible : {champ}") from exc


def verifier_rapport(rapport: dict) -> list[dict]:
    """Vérifier origine, intégrité du décompte et non-troncature des notices."""
    if not isinstance(rapport, dict):
        raise IndexDECPInvalide("Relevé non structuré")
    identite_catalogue = (rapport.get("version"), rapport.get("source_catalogue"))
    page_attendue = CATALOGUES.get(identite_catalogue)
    if page_attendue is None or rapport.get("page_catalogue") != page_attendue:
        raise IndexDECPInvalide("Version, source ou page de provenance incompatible")
    if not isinstance(rapport.get("sha256_fichier_brut"), str) or not SHA.fullmatch(
        rapport["sha256_fichier_brut"]
    ):
        raise IndexDECPInvalide("Empreinte du fichier invalide")
    if not isinstance(rapport.get("ressource_id"), str) or not re.fullmatch(
        r"[0-9a-f-]{36}", rapport["ressource_id"]
    ):
        raise IndexDECPInvalide("Identifiant de ressource non conforme")
    if rapport.get("extraits_plafonnes") is not False:
        raise IndexDECPInvalide("Extrait incomplet : aucun index présenté comme exhaustif")
    compte = rapport.get("releves")
    lignes = rapport.get("marches_extraits")
    if not isinstance(compte, dict) or not isinstance(lignes, list) or len(lignes) > MAX_MARCHES:
        raise IndexDECPInvalide("Notices manquantes ou dépassant le plafond")
    if type(compte.get("marches_uniques_valides")) is not int or (
        compte["marches_uniques_valides"] != len(lignes)
    ):
        raise IndexDECPInvalide("Écart entre le bilan et les notices disponibles")
    instant = rapport.get("releve_le")
    if not isinstance(instant, str):
        raise IndexDECPInvalide("Date du relevé absente")
    try:
        if datetime.fromisoformat(instant).tzinfo is None:
            raise ValueError("Fuseau requis")
    except ValueError as exc:
        raise IndexDECPInvalide("Date du relevé non datée") from exc
    vus = set()
    for ligne in lignes:
        if not isinstance(ligne, dict):
            raise IndexDECPInvalide("Notice non structurée")
        siret = ligne.get("acheteur_siret")
        mid = ligne.get("id_marche")
        objet = ligne.get("objet")
        if not isinstance(siret, str) or not SIRET.fullmatch(siret):
            raise IndexDECPInvalide("SIRET de l'acheteur invalide")
        if not isinstance(mid, str) or not 0 < len(mid.strip()) <= 100:
            raise IndexDECPInvalide("Identifiant de marché absent")
        if not isinstance(objet, str) or not 0 < len(objet.strip()) <= 1000:
            raise IndexDECPInvalide("Objet du marché absent")
        if (siret, mid) in vus:
            raise IndexDECPInvalide("Identité de marché répétée dans l'extrait")
        vus.add((siret, mid))
        for field in ("date_notification", "date_publication_declaree"):
            _date(ligne.get(field), field, absent=True)
        cpv = ligne.get("code_cpv")
        if cpv is not None and (
            not isinstance(cpv, str) or not re.fullmatch(r"[0-9]{8}(?:-[0-9])?", cpv)
        ):
            raise IndexDECPInvalide("Code CPV incorrect")
        montant = ligne.get("montant_euros_ht_declare")
        if montant is not None and (
            type(montant) not in (int, float)
            or not (0 <= montant < float("inf"))
        ):
            raise IndexDECPInvalide("Montant non numérique fini ou négatif")
        if ligne.get("besoin_encore_ouvert_demontre") is not False:
            raise IndexDECPInvalide("Une attribution n'établit pas un besoin ouvert")
    return lignes


def importer(base: Path, rapport: dict) -> dict:
    """Insérer uniquement de nouvelles versions ou nouvelles attestations."""
    lignes = verifier_rapport(rapport)
    base.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(base)
    nouvelles_identites = nouvelles_versions = nouvelles_attestations = 0
    try:
        con.executescript(SCHEMA)
        with con:
            empreinte_fichier = rapport["sha256_fichier_brut"]
            con.execute(
                """INSERT OR IGNORE INTO fichiers_sources
                   (empreinte_fichier, source_catalogue, ressource_id,
                    page_catalogue, date_premiere_importation)
                   VALUES (?, ?, ?, ?, ?)""",
                (empreinte_fichier, rapport["source_catalogue"], rapport["ressource_id"],
                 rapport["page_catalogue"], rapport["releve_le"]),
            )
            for ligne in lignes:
                siret = ligne["acheteur_siret"]
                mid = ligne["id_marche"]
                identite = con.execute(
                    "INSERT OR IGNORE INTO marches (acheteur_siret,id_marche) VALUES (?,?)",
                    (siret, mid),
                )
                nouvelles_identites += identite.rowcount
                empreinte = hashlib.sha256(json.dumps(
                    ligne, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")).hexdigest()
                version = con.execute(
                    """INSERT OR IGNORE INTO versions
                    (acheteur_siret, id_marche, empreinte_version, objet, code_cpv,
                     date_notification, date_publication_declaree, montant_euros_ht, nature)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (siret, mid, empreinte, ligne["objet"], ligne["code_cpv"],
                     ligne["date_notification"], ligne["date_publication_declaree"],
                     ligne["montant_euros_ht_declare"], ligne["nature"]),
                )
                if version.rowcount:
                    nouvelles_versions += 1
                    cle = siret + "\x1f" + mid + "\x1f" + empreinte
                    con.execute(
                        "INSERT INTO recherche_marches (cle, objet) VALUES (?,?)",
                        (cle, ligne["objet"]),
                    )
                attestation = con.execute(
                    """INSERT OR IGNORE INTO attestations
                       (acheteur_siret, id_marche, empreinte_version,
                        empreinte_fichier, source_catalogue, ressource_id, observe_le)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (siret, mid, empreinte, empreinte_fichier,
                     rapport["source_catalogue"], rapport["ressource_id"],
                     rapport["releve_le"]),
                )
                nouvelles_attestations += attestation.rowcount
        comptes = {
            "identites_marche": con.execute("SELECT COUNT(*) FROM marches").fetchone()[0],
            "versions_conservees": con.execute("SELECT COUNT(*) FROM versions").fetchone()[0],
            "fichiers_suivis": con.execute("SELECT COUNT(*) FROM fichiers_sources").fetchone()[0],
            "attestations_de_fichier": con.execute("SELECT COUNT(*) FROM attestations").fetchone()[0],
        }
        return {
            **comptes, "nouvelles_identites": nouvelles_identites,
            "nouvelles_versions": nouvelles_versions,
            "nouvelles_attestations": nouvelles_attestations,
            "indicateur_de_besoin_ouvert": False,
            "correspondances_boamp_verifiees": 0,
        }
    finally:
        con.close()


def rechercher(base: Path, expression: str, limite: int = 25) -> list[dict]:
    """Retrouver des attributions documentées sans générer d'épisodes de besoins."""
    if not isinstance(expression, str) or not 1 <= len(expression.strip()) <= 120:
        raise IndexDECPInvalide("Expression incorrecte")
    if type(limite) is not int or not 1 <= limite <= 100:
        raise IndexDECPInvalide("Limite de recherche incorrecte")
    if not base.is_file():
        raise IndexDECPInvalide("Base locale absente")
    phrase = '"' + expression.strip().replace('"', '""') + '"'
    con = sqlite3.connect(base)
    con.row_factory = sqlite3.Row
    try:
        resultats = con.execute(
            """SELECT v.acheteur_siret, v.id_marche, v.objet, v.code_cpv,
                      v.date_notification, v.montant_euros_ht,
                      COUNT(a.empreinte_fichier) AS sources_documentaires
               FROM recherche_marches r
               JOIN versions v ON r.cle = (
                    v.acheteur_siret || char(31) || v.id_marche ||
                    char(31) || v.empreinte_version
               )
               JOIN attestations a ON
                    a.acheteur_siret=v.acheteur_siret AND a.id_marche=v.id_marche
                    AND a.empreinte_version=v.empreinte_version
               WHERE recherche_marches MATCH ?
               GROUP BY v.acheteur_siret, v.id_marche, v.empreinte_version
               ORDER BY v.date_notification DESC, v.acheteur_siret, v.id_marche
               LIMIT ?""",
            (phrase, limite),
        )
        return [dict(row) for row in resultats]
    finally:
        con.close()


def main() -> None:
    """Importer un relevé complet ou consulter des attributions en texte intégral."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["importer", "rechercher"])
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--releve", type=Path, default=RELEVE)
    p.add_argument("--expression")
    p.add_argument("--limite", type=int, default=25)
    args = p.parse_args()
    try:
        if args.action == "importer":
            resultat = importer(args.base, json.loads(args.releve.read_text(encoding="utf-8")))
        else:
            resultat = rechercher(args.base, args.expression or "", args.limite)
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
    except (OSError, ValueError, sqlite3.Error) as exc:
        p.exit(1, f"Index DECP refusé : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
