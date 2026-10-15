"""Importation persistante des offres d'emploi public déjà extraites par FRONTIÈRE.

Les partitions produites par scripts.extraire_offres_publiques sont lues en
flux, avec vérification de leur empreinte et de celle de chaque offre.
Un cliché de source est enregistré en une transaction SQL ; les variations
historiques et les références présentant plusieurs variantes sont préservées.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Iterator

from sqlalchemy import (
    Column, ForeignKeyConstraint, Index, Integer, MetaData, String, Table,
    Text, create_engine, func, or_, select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

TABLES = MetaData()
IDENTIFIANT_SHA = re.compile(r"^[0-9a-f]{64}$")
LOT = 300
LIGNE_MAX_OCTETS = 18000
FICHIER_MAX_OCTETS = 70 * 1024 * 1024
PARTITIONS = tuple(f"lot_{i:02x}.jsonl" for i in range(16))

captures = Table(
    "captures_emplois_publics", TABLES,
    Column("source_id", String(120), primary_key=True),
    Column("sha256_csv", String(64), primary_key=True),
    Column("observe_le", String(32), nullable=False),
    Column("importe_le", String(32), nullable=False),
    Column("offres", Integer, nullable=False),
    Column("source_url", Text, nullable=False),
)
versions = Table(
    "versions_emplois_publics", TABLES,
    Column("empreinte", String(64), primary_key=True),
    Column("reference", String(180), nullable=False),
    Column("intitule", String(400)),
    Column("employeur", String(250)),
    Column("organisme", String(240)),
    Column("competences", Text),
    Column("metier", String(220)),
    Column("localisation", String(250)),
    Column("contenu_json", Text, nullable=False),
    Column("premier_releve_le", String(32), nullable=False),
)
Index("ix_emplois_reference", versions.c.reference)
Index("ix_emplois_organisme", versions.c.organisme)
apparitions = Table(
    "apparitions_emplois_publics", TABLES,
    Column("source_id", String(120), primary_key=True),
    Column("sha256_csv", String(64), primary_key=True),
    Column("empreinte", String(64), primary_key=True),
    ForeignKeyConstraint(
        ["source_id", "sha256_csv"],
        ["captures_emplois_publics.source_id", "captures_emplois_publics.sha256_csv"],
    ),
    ForeignKeyConstraint(["empreinte"], ["versions_emplois_publics.empreinte"]),
)


class ImportEmploisInvalide(ValueError):
    """Manifestation d'une capture mal formée ou incomplète."""


def _instant(value: object) -> str:
    if not isinstance(value, str):
        raise ImportEmploisInvalide("Date du cliché absente.")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ImportEmploisInvalide("Date du cliché invalide.") from exc
    if dt.tzinfo is None:
        raise ImportEmploisInvalide("Date sans fuseau horaire.")
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _manifeste(dossier: Path) -> dict:
    fichier = dossier / "manifest_offres_postes.json"
    brut = json.loads(fichier.read_text(encoding="utf-8"))
    if not isinstance(brut, dict) or brut.get("version") != "emplois-publics-extraits-v1":
        raise ImportEmploisInvalide("Version du manifeste non reconnue.")
    if not isinstance(brut.get("source_id"), str) or not 1 <= len(brut["source_id"]) <= 120:
        raise ImportEmploisInvalide("Identifiant de ressource absent.")
    if not isinstance(brut.get("source_url"), str) or not brut["source_url"].startswith(
        "https://static.data.gouv.fr/resources/"
    ):
        raise ImportEmploisInvalide("Provenance de ressource incorrecte.")
    if not isinstance(brut.get("sha256_csv"), str) or not IDENTIFIANT_SHA.fullmatch(
        brut["sha256_csv"]
    ):
        raise ImportEmploisInvalide("Empreinte du CSV source invalide.")
    if type(brut.get("offres_distinctes")) is not int or not 0 < brut["offres_distinctes"] <= 300000:
        raise ImportEmploisInvalide("Effectif du cliché incohérent.")
    signatures = brut.get("empreintes_partitions")
    if (not isinstance(signatures, dict) or set(signatures) != set(PARTITIONS)
        or not all(isinstance(x, str) and IDENTIFIANT_SHA.fullmatch(x)
                   for x in signatures.values())):
        raise ImportEmploisInvalide("Empreintes des seize partitions absentes.")
    brut["extraire_le"] = _instant(brut.get("extraire_le"))
    return brut


def _lire_partition(path: Path, signature: str) -> Iterator[dict]:
    """Contrôler en une passe l'empreinte du lot et toutes ses lignes JSONL."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > FICHIER_MAX_OCTETS:
        raise ImportEmploisInvalide("Partition absente, liée ou démesurée.")
    sha = hashlib.sha256()
    total = 0
    with path.open("rb") as f:
        for ligne in f:
            total += len(ligne)
            if len(ligne) > LIGNE_MAX_OCTETS or total > FICHIER_MAX_OCTETS:
                raise ImportEmploisInvalide("Ligne ou partition trop volumineuse.")
            sha.update(ligne)
            if not ligne.endswith(b"\n"):
                raise ImportEmploisInvalide("Ligne JSONL incomplète.")
            objet = json.loads(ligne)
            if not isinstance(objet, dict):
                raise ImportEmploisInvalide("Enregistrement d'emploi mal formé.")
            reference = objet.get("reference")
            empreinte = objet.get("cle_enregistrement")
            if (not isinstance(reference, str) or len(reference) < 3
                or len(reference) > 180 or not isinstance(empreinte, str)
                or not IDENTIFIANT_SHA.fullmatch(empreinte)):
                raise ImportEmploisInvalide("Identifiant d'offre manquant.")
            champs = {k: v for k, v in objet.items() if k != "cle_enregistrement"}
            contenu = json.dumps(
                champs, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            if hashlib.sha256(contenu.encode("utf-8")).hexdigest() != empreinte:
                raise ImportEmploisInvalide("Contenu d'offre incompatible avec son empreinte.")
            for nom, plafond in (("intitule", 400), ("employeur", 250),
                                 ("organisme", 240), ("metier", 220),
                                 ("localisation", 250), ("competences_attendues", 6000)):
                valeur = objet.get(nom)
                if valeur is not None and (
                    not isinstance(valeur, str) or len(valeur) > plafond
                ):
                    raise ImportEmploisInvalide(f"Champ incompatible : {nom}.")
            yield {
                "empreinte": empreinte,
                "reference": reference,
                "intitule": objet.get("intitule"),
                "employeur": objet.get("employeur"),
                "organisme": objet.get("organisme"),
                "metier": objet.get("metier"),
                "localisation": objet.get("localisation"),
                "competences": objet.get("competences_attendues"),
                "contenu_json": contenu,
            }
    if sha.hexdigest() != signature:
        raise ImportEmploisInvalide("Empreinte de partition différente du manifeste.")


class StockageEmplois:
    """Interface SQL commune à SQLite et PostgreSQL pour les offres publiques."""

    def __init__(self, url: str):
        kwargs = {"future": True, "pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"timeout": 45}
        self.moteur = create_engine(url, **kwargs)
        if self.moteur.dialect.name not in ("sqlite", "postgresql"):
            raise ValueError("Seuls SQLite et PostgreSQL sont pris en charge.")
        if self.moteur.dialect.name == "sqlite":
            from sqlalchemy import event
            @event.listens_for(self.moteur, "connect")
            def activer_cles(dbapi_connection, _record):
                dbapi_connection.execute("PRAGMA foreign_keys=ON")
        TABLES.create_all(self.moteur)

    def _insert(self, table):
        return sqlite_insert(table) if self.moteur.dialect.name == "sqlite" else pg_insert(table)

    def capture_presente(self, source_id: str, sha: str) -> bool:
        with self.moteur.connect() as conn:
            return conn.execute(select(captures.c.source_id).where(
                captures.c.source_id == source_id, captures.c.sha256_csv == sha
            )).first() is not None

    def importer(self, dossier: Path) -> dict:
        """Indexer intégralement un cliché ou revenir à l'état précédent.

        Les écritures ne deviennent permanentes qu'après lecture des seize
        partitions et concordance des décomptes.
        """
        manifest = _manifeste(dossier)
        identifiant, sha = manifest["source_id"], manifest["sha256_csv"]
        if self.capture_presente(identifiant, sha):
            return {"etat": "deja_importe", **self.etat()}
        observe = manifest["extraire_le"]
        horloge = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        total = 0
        with self.moteur.begin() as conn:
            conn.execute(captures.insert().values(
                source_id=identifiant, sha256_csv=sha, observe_le=observe,
                importe_le=horloge, offres=manifest["offres_distinctes"],
                source_url=manifest["source_url"],
            ))
            for nom in PARTITIONS:
                lot: list[dict] = []
                for x in _lire_partition(dossier / "offres_postes" / nom,
                                          manifest["empreintes_partitions"][nom]):
                    lot.append(x)
                    total += 1
                    if len(lot) == LOT:
                        self._importer_lot(conn, lot, identifiant, sha, observe)
                        lot.clear()
                if lot:
                    self._importer_lot(conn, lot, identifiant, sha, observe)
            enregistrés = conn.scalar(select(func.count()).select_from(apparitions).where(
                apparitions.c.source_id == identifiant,
                apparitions.c.sha256_csv == sha,
            ))
            if total != manifest["offres_distinctes"] or enregistrés != total:
                raise ImportEmploisInvalide("Nombre d'offres distinctes différent du manifeste.")
        return {"etat": "importe", "offres_importees": total, **self.etat()}

    def _importer_lot(self, conn, lot: list[dict], source: str, sha: str, observe: str):
        historiques = [{
            **x, "premier_releve_le": observe
        } for x in lot]
        insert_v = self._insert(versions).values(historiques)
        conn.execute(insert_v.on_conflict_do_nothing(index_elements=[versions.c.empreinte]))
        insert_a = self._insert(apparitions).values([
            {"source_id": source, "sha256_csv": sha, "empreinte": x["empreinte"]}
            for x in lot
        ])
        conn.execute(insert_a.on_conflict_do_nothing(index_elements=[
            apparitions.c.source_id, apparitions.c.sha256_csv, apparitions.c.empreinte
        ]))

    def _dernier(self, conn):
        return conn.execute(select(
            captures.c.source_id, captures.c.sha256_csv, captures.c.observe_le
        ).order_by(
            captures.c.observe_le.desc(), captures.c.source_id.desc(),
            captures.c.sha256_csv.desc(),
        ).limit(1)).first()

    def etat(self) -> dict:
        with self.moteur.connect() as conn:
            dernier = self._dernier(conn)
            courant = 0 if dernier is None else conn.scalar(
                select(func.count()).select_from(apparitions).where(
                    apparitions.c.source_id == dernier.source_id,
                    apparitions.c.sha256_csv == dernier.sha256_csv,
                )
            )
            return {
                "captures": conn.scalar(select(func.count()).select_from(captures)),
                "variantes_historiques": conn.scalar(select(func.count()).select_from(versions)),
                "offres_du_dernier_cliche": courant,
                "derniere_observation": dernier.observe_le if dernier else None,
            }

    def rechercher(self, expression: str, limite: int = 20) -> list[dict]:
        if not isinstance(expression, str) or not expression.strip() or len(expression) > 150:
            raise ValueError("Expression de recherche invalide.")
        if type(limite) is not int or not 1 <= limite <= 100:
            raise ValueError("Limite de recherche invalide.")
        motif = "%" + expression.strip().replace("\\", "\\\\").replace(
            "%", "\\%").replace("_", "\\_") + "%"
        with self.moteur.connect() as conn:
            dernier = self._dernier(conn)
            if dernier is None:
                return []
            q = select(
                versions.c.reference, versions.c.intitule, versions.c.organisme,
                versions.c.employeur, versions.c.metier, versions.c.localisation,
                versions.c.competences
            ).select_from(versions.join(
                apparitions, versions.c.empreinte == apparitions.c.empreinte
            )).where(
                apparitions.c.source_id == dernier.source_id,
                apparitions.c.sha256_csv == dernier.sha256_csv,
                or_(
                    versions.c.intitule.ilike(motif, escape="\\"),
                    versions.c.organisme.ilike(motif, escape="\\"),
                    versions.c.metier.ilike(motif, escape="\\"),
                    versions.c.competences.ilike(motif, escape="\\"),
                ),
            ).order_by(versions.c.reference).limit(limite)
            return [dict(x) for x in conn.execute(q).mappings()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="URL SQLAlchemy de la base persistante")
    sub = parser.add_subparsers(dest="action", required=True)
    cmd = sub.add_parser("importer", help="Intégrer un cliché DGAFP partitionné")
    cmd.add_argument("--repertoire", type=Path, default=Path("institutionnel/besoins_publics"))
    sub.add_parser("etat", help="Afficher le dernier cliché disponible")
    cmd = sub.add_parser("rechercher", help="Chercher parmi les offres du dernier cliché")
    cmd.add_argument("expression")
    cmd.add_argument("--limite", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        base = StockageEmplois(args.base)
        if args.action == "importer":
            resultat = base.importer(args.repertoire)
        elif args.action == "rechercher":
            resultat = base.rechercher(args.expression, args.limite)
        else:
            resultat = base.etat()
        print(json.dumps(resultat, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Base des emplois publics : {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
