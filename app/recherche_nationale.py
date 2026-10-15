"""Recherche fédérée dans quatre bases persistantes de FRONTIÈRE.

Chaque flux conserve son identité documentaire. Les bases sont ouvertes en
lecture seule, sans copie ni fusion factice des acheteurs, avis et contrats.
API locale FastAPI et interface en ligne de commande sur les mêmes requêtes.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException, Query

SOURCES = ("boamp", "emplois", "decp", "ted")
TYPES = {
    "boamp": "avis de marché",
    "emplois": "offre d'emploi public",
    "decp": "marché attribué",
    "ted": "avis européen",
}
CHEMINS_ENV = {
    "boamp": "FRONTIERE_BOAMP_DB",
    "emplois": "FRONTIERE_EMPLOIS_DB",
    "decp": "FRONTIERE_DECP_DB",
    "ted": "FRONTIERE_TED_DB",
}
CATALOGUES = {
    "decp": "https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides",
}


@dataclass(frozen=True)
class Chemins:
    boamp: Path | None = None
    emplois: Path | None = None
    decp: Path | None = None
    ted: Path | None = None

    @classmethod
    def environnement(cls) -> "Chemins":
        return cls(**{
            cle: Path(valeur) if (valeur := os.environ.get(nom)) else None
            for cle, nom in CHEMINS_ENV.items()
        })

    def chemin(self, source: str) -> Path | None:
        return getattr(self, source)


@contextmanager
def _connecter(path: Path | None):
    if path is None or not path.is_file():
        yield None
        return
    connexion = sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro", uri=True, timeout=20
    )
    try:
        connexion.row_factory = sqlite3.Row
        connexion.execute("PRAGMA query_only=ON")
        connexion.execute("PRAGMA busy_timeout=20000")
        yield connexion
    finally:
        connexion.close()


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}


ATTENDUES = {
    "boamp": {"avis_boamp", "captures_boamp"},
    "emplois": {"versions_emplois_publics", "apparitions_emplois_publics",
                "captures_emplois_publics"},
    "decp": {"versions", "attestations", "recherche_marches"},
    "ted": {"avis_ted", "captures_ted"},
}


def _ecrire_resultat(source: str, row: sqlite3.Row) -> dict:
    item = dict(row)
    return {
        "source": source,
        "nature": TYPES[source],
        "identifiant": str(item["identifiant"]),
        "titre": item["titre"] or "",
        "organisme": item["organisme"] or "",
        "date_publication": item["date_publication"],
        "url_document": item["url_document"],
        "code_cpv": item.get("code_cpv"),
        "montant_euros_ht": item.get("montant_euros_ht"),
        "empreinte_version": item.get("empreinte_version"),
    }


def _lire_boamp(conn: sqlite3.Connection, motif: str, limite: int):
    return conn.execute(
        "SELECT identifiant, objet AS titre, acheteur AS organisme, "
        "date_parution AS date_publication, avis AS url_document, "
        "NULL AS code_cpv,NULL AS montant_euros_ht,"
        "empreinte AS empreinte_version FROM avis_boamp WHERE "
        "objet LIKE ? ESCAPE '\\' OR acheteur LIKE ? ESCAPE '\\' "
        "ORDER BY date_parution DESC, identifiant LIMIT ?",
        (motif, motif, limite),
    )


def _lire_emplois(conn: sqlite3.Connection, motif: str, limite: int):
    return conn.execute(
        "SELECT v.reference AS identifiant, v.intitule AS titre,"
        "COALESCE(v.organisme,v.employeur) AS organisme,"
        "NULL AS date_publication, NULL AS url_document,"
        "NULL AS code_cpv,NULL AS montant_euros_ht,"
        "v.empreinte AS empreinte_version "
        "FROM versions_emplois_publics v JOIN apparitions_emplois_publics a "
        "ON a.empreinte=v.empreinte "
        "JOIN (SELECT source_id,sha256_csv FROM captures_emplois_publics "
        "ORDER BY observe_le DESC, source_id DESC,sha256_csv DESC LIMIT 1) recent "
        "ON a.source_id=recent.source_id AND a.sha256_csv=recent.sha256_csv "
        "WHERE (v.intitule LIKE ? ESCAPE '\\' "
        "OR v.organisme LIKE ? ESCAPE '\\' "
        "OR v.metier LIKE ? ESCAPE '\\' "
        "OR v.competences LIKE ? ESCAPE '\\') "
        "ORDER BY v.reference, v.empreinte LIMIT ?",
        (motif, motif, motif, motif, limite),
    )


def _lire_decp(conn: sqlite3.Connection, expression: str, limite: int):
    # L'index DECP existant est FTS5 : un suffixe de préfixe permet
    # de retrouver « informatiques » avec la requête « informati ».
    recherche = '"' + expression.strip().replace('"', '""') + '"*'
    return conn.execute(
        "SELECT v.acheteur_siret || ':' || v.id_marche AS identifiant,"
        "v.objet AS titre,v.acheteur_siret AS organisme,"
        "v.date_publication_declaree AS date_publication,"
        "NULL AS url_document,v.code_cpv AS code_cpv,"
        "v.montant_euros_ht AS montant_euros_ht,"
        "v.empreinte_version AS empreinte_version "
        "FROM recherche_marches r JOIN versions v ON r.cle = "
        "(v.acheteur_siret || char(31) || v.id_marche || char(31) || v.empreinte_version) "
        "WHERE recherche_marches MATCH ? "
        "ORDER BY v.date_publication_declaree DESC,v.id_marche LIMIT ?",
        (recherche, limite),
    )


def _lire_ted(conn: sqlite3.Connection, motif: str, limite: int):
    return conn.execute(
        "SELECT numero AS identifiant,titre,acheteur AS organisme,"
        "date_publication,source_url AS url_document,"
        "codes_cpv AS code_cpv,NULL AS montant_euros_ht,"
        "empreinte_courante AS empreinte_version "
        "FROM avis_ted WHERE titre LIKE ? ESCAPE '\\' "
        "OR acheteur LIKE ? ESCAPE '\\' "
        "ORDER BY date_publication DESC,numero DESC LIMIT ?",
        (motif, motif, limite),
    )


def etat(chemins: Chemins) -> dict[str, dict]:
    resultats: dict[str, dict] = {}
    for nom in SOURCES:
        try:
            with _connecter(chemins.chemin(nom)) as conn:
                if conn is None:
                    resultats[nom] = {"etat": "non_configure"}
                elif not ATTENDUES[nom].issubset(_tables(conn)):
                    resultats[nom] = {"etat": "schema_incompatible"}
                else:
                    requetes = {
                        "boamp": "SELECT MAX(observe_le) FROM captures_boamp",
                        "emplois": "SELECT MAX(observe_le) FROM captures_emplois_publics",
                        "decp": "SELECT MAX(observe_le) FROM attestations",
                        "ted": "SELECT MAX(observe_le) FROM captures_ted",
                    }
                    resultats[nom] = {
                        "etat": "accessible",
                        "derniere_observation": conn.execute(requetes[nom]).fetchone()[0],
                    }
        except (OSError, sqlite3.Error):
            resultats[nom] = {"etat": "lecture_impossible"}
    return resultats


def rechercher(chemins: Chemins, expression: str, *,
              limite: int = 30, sources: tuple[str, ...] = SOURCES) -> dict:
    """Rechercher sans inventer de correspondances ni de documents sources."""
    if (not isinstance(expression, str) or
            not 1 <= len(expression.strip()) <= 150):
        raise ValueError("Expression de recherche absente ou trop longue.")
    if type(limite) is not int or not 1 <= limite <= 100:
        raise ValueError("Limite de réponse incorrecte.")
    if not sources or any(nom not in SOURCES for nom in sources):
        raise ValueError("Sources de recherche non reconnues.")
    if len(set(sources)) != len(sources):
        raise ValueError("Source répétée dans la recherche.")
    motif = "%" + expression.strip().replace("\\", "\\\\").replace(
        "%", "\\%").replace("_", "\\_") + "%"
    lecteurs = {
        "boamp": lambda conn: _lire_boamp(conn, motif, limite),
        "emplois": lambda conn: _lire_emplois(conn, motif, limite),
        "decp": lambda conn: _lire_decp(conn, expression, limite),
        "ted": lambda conn: _lire_ted(conn, motif, limite),
    }
    rencontres: list[dict] = []
    etats: dict[str, str] = {}
    for source in sources:
        try:
            with _connecter(chemins.chemin(source)) as conn:
                if conn is None:
                    etats[source] = "non_configure"
                    continue
                if not ATTENDUES[source].issubset(_tables(conn)):
                    etats[source] = "schema_incompatible"
                    continue
                lignes = lecteurs[source](conn)
                rencontres.extend(_ecrire_resultat(source, ligne) for ligne in lignes)
                etats[source] = "accessible"
        except (OSError, sqlite3.Error):
            etats[source] = "lecture_impossible"
    rencontres.sort(
        key=lambda x: (
            x["date_publication"] or "", x["source"], x["identifiant"]
        ), reverse=True
    )
    return {
        "expression": expression.strip(),
        "resultats": rencontres[:limite],
        "nombre_retourne": min(limite, len(rencontres)),
        "sources": etats,
        "troncature_par_limite": len(rencontres) > limite,
        "limite": limite,
    }


def creer_application(chemins: Chemins | None = None) -> FastAPI:
    config = chemins or Chemins.environnement()
    app = FastAPI(title="FRONTIÈRE — consultation nationale", version="0.1.0")

    @app.get("/sante")
    def sante():
        resultats = etat(config)
        return {
            "service": "consultation_frontiere",
            "etat": "pret",
            "sources": resultats,
        }

    @app.get("/sources")
    def sources():
        return etat(config)

    @app.get("/exploitation")
    def exploitation():
        from app.etat_exploitation import diagnostic
        return diagnostic(config)

    @app.get("/pret")
    def pret():
        from app.etat_exploitation import diagnostic
        resultat = diagnostic(config)
        if not resultat["pret_pour_consultation_complete"]:
            raise HTTPException(status_code=503, detail=resultat)
        return resultat

    @app.get("/recherche")
    def recherche(
        q: str = Query(min_length=1, max_length=150),
        limite: int = Query(default=30, ge=1, le=100),
        source: str | None = None,
    ):
        demande = tuple(source.split(",")) if source else SOURCES
        try:
            return rechercher(config, q, limite=limite, sources=demande)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


app = creer_application()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boamp", type=Path)
    parser.add_argument("--emplois", type=Path)
    parser.add_argument("--decp", type=Path)
    parser.add_argument("--ted", type=Path)
    sub = parser.add_subparsers(dest="action", required=True)
    requete = sub.add_parser("rechercher")
    requete.add_argument("expression")
    requete.add_argument("--limite", type=int, default=30)
    sub.add_parser("sources")
    args = parser.parse_args(argv)
    configuration = Chemins(**{
        s: getattr(args, s) or Chemins.environnement().chemin(s)
        for s in SOURCES
    })
    try:
        resultat = (
            rechercher(configuration, args.expression, limite=args.limite)
            if args.action == "rechercher" else etat(configuration)
        )
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
        return 0
    except ValueError as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
