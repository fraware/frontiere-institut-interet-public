"""Projection persistante des captures BOAMP déjà collectées par FRONTIÈRE.

Une capture (archive quotidienne ou relevé courant) est ingérée en une seule
transaction. Le programme ne consulte aucun site : les collecteurs existants
alimentent ses fichiers d'entrée. SQLite et PostgreSQL sont pris en charge
par SQLAlchemy 2.x ; PostgreSQL nécessite un pilote installé séparément.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

from sqlalchemy import (
    Boolean, Column, Index, Integer, MetaData, String, Table, Text,
    and_, create_engine, func, or_, select,
)
from sqlalchemy.dialects.postgresql import insert as insert_postgres
from sqlalchemy.dialects.sqlite import insert as insert_sqlite

SOURCE = "BOAMP"
IDENTIFIANT = re.compile(r"^[\w.-]{1,150}$", re.UNICODE)
EMPREINTE = re.compile(r"^[a-f0-9]{64}$")
TAILLE_DECOMPRESSEE_MAX = 64 * 1024 * 1024
TAILLE_COURANTE_MAX = 48 * 1024 * 1024
AVIS_PAR_ARCHIVE_MAX = 5_000
AVIS_COURANTS_MAX = 30_000
TAILLE_LOT = 400

meta = MetaData()
captures = Table(
    "captures_boamp", meta,
    Column("chemin", String(500), primary_key=True),
    Column("empreinte", String(64), primary_key=True),
    Column("observe_le", String(32), nullable=False),
    Column("importe_le", String(32), nullable=False),
    Column("nombre_avis", Integer, nullable=False),
    Column("jour", String(10)),
    Column("jour_complet", Boolean, nullable=False),
)
versions = Table(
    "versions_avis_boamp", meta,
    Column("identifiant", String(150), primary_key=True),
    Column("empreinte", String(64), primary_key=True),
    Column("contenu", Text, nullable=False),
    Column("observe_initialement_le", String(32), nullable=False),
    Column("capture_initiale", String(500), nullable=False),
)
courants = Table(
    "avis_boamp", meta,
    Column("identifiant", String(150), primary_key=True),
    Column("empreinte", String(64), nullable=False),
    Column("objet", Text, nullable=False),
    Column("acheteur", String(250), nullable=False),
    Column("date_parution", String(32)),
    Column("date_limite_reponse", String(32)),
    Column("categorie_marche", String(80)),
    Column("etat_avis", String(80)),
    Column("avis", String(2048)),
    Column("observe_le", String(32), nullable=False),
    Column("capture", String(500), nullable=False),
)
Index("ix_boamp_parution", courants.c.date_parution)
Index("ix_boamp_acheteur", courants.c.acheteur)


class CaptureInvalide(ValueError):
    """Capture incohérente : ne jamais l'intégrer partiellement."""


def _instant(valeur: Any) -> str:
    if not isinstance(valeur, str):
        raise CaptureInvalide("Horodatage de capture absent.")
    try:
        instant = datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureInvalide("Horodatage de capture illisible.") from exc
    if instant.tzinfo is None:
        raise CaptureInvalide("Horodatage de capture sans fuseau.")
    return instant.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _fichier_sur(racine: Path, chemin: Path) -> Path:
    """Empêcher qu'un manifeste pointe hors des archives attendues."""
    base = racine.resolve()
    cible = chemin.resolve()
    if not cible.is_relative_to(base) or not cible.is_file():
        raise CaptureInvalide("Archive absente ou extérieure au répertoire de collecte.")
    return cible


def _empreinte_fichier(chemin: Path) -> str:
    empreinte = hashlib.sha256()
    with chemin.open("rb") as entree:
        for bloc in iter(lambda: entree.read(1024 * 1024), b""):
            empreinte.update(bloc)
    return empreinte.hexdigest()


def _normaliser(avis: Any, *, jour: str | None) -> dict:
    if not isinstance(avis, dict):
        raise CaptureInvalide("Enregistrement BOAMP non structuré.")
    identifiant = avis.get("id")
    if not isinstance(identifiant, str) or not IDENTIFIANT.fullmatch(identifiant):
        raise CaptureInvalide("Identifiant BOAMP absent ou incorrect.")
    parution = avis.get("date_parution")
    if parution is not None and (not isinstance(parution, str) or
                                not re.match(r"^\d{4}-\d{2}-\d{2}", parution)):
        raise CaptureInvalide("Date de publication BOAMP incorrecte.")
    if jour is not None and (parution is None or parution[:10] != jour):
        raise CaptureInvalide("Avis publié hors de la journée archivée.")
    champs = {
        "objet": (avis.get("objet"), 450),
        "acheteur": (avis.get("acheteur"), 250),
        "date_parution": (parution, 32),
        "date_limite_reponse": (avis.get("date_limite_reponse"), 32),
        "categorie_marche": (avis.get("categorie_marche"), 80),
        "etat_avis": (avis.get("etat_avis"), 80),
        "avis": (avis.get("avis"), 2048),
    }
    valeurs: dict[str, Any] = {"identifiant": identifiant}
    for nom, (valeur, limite) in champs.items():
        if valeur is not None and (not isinstance(valeur, str) or len(valeur) > limite):
            raise CaptureInvalide(f"Champ BOAMP incorrect : {nom}.")
        valeurs[nom] = valeur
    valeurs["objet"] = valeurs["objet"] or ""
    valeurs["acheteur"] = valeurs["acheteur"] or ""
    # Les autres champs du collecteur ne contiennent ici aucune donnée nécessaire
    # à l'index. Leur suppression rend l'empreinte stable entre producteurs.
    contenu = json.dumps(valeurs, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    valeurs["contenu"] = contenu
    valeurs["empreinte"] = hashlib.sha256(contenu.encode("utf-8")).hexdigest()
    return valeurs


def _lire_archive(racine: Path, fiche: Path) -> tuple[dict, list[dict], str]:
    manifeste = json.loads(fiche.read_text(encoding="utf-8"))
    if (not isinstance(manifeste, dict) or
            manifeste.get("version") != "boamp-historique-journalier-v1" or
            manifeste.get("pages_completes") is not True):
        raise CaptureInvalide("Manifeste BOAMP incomplet ou de version inconnue.")
    jour = manifeste.get("jour_parution")
    if not isinstance(jour, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", jour):
        raise CaptureInvalide("Journée de capture inconnue.")
    relative = manifeste.get("archive_relative")
    if not isinstance(relative, str) or not relative.endswith(".jsonl.gz"):
        raise CaptureInvalide("Chemin de l'archive non conforme.")
    archive = _fichier_sur(racine, racine / relative)
    sha_compresse = manifeste.get("sha256_archive_gzip")
    sha_source = manifeste.get("sha256_octets_decompresses")
    if (not isinstance(sha_compresse, str) or not EMPREINTE.fullmatch(sha_compresse)
            or not isinstance(sha_source, str) or not EMPREINTE.fullmatch(sha_source)):
        raise CaptureInvalide("Empreintes de l'archive manquantes.")
    if _empreinte_fichier(archive) != sha_compresse:
        raise CaptureInvalide("Empreinte des octets comprimés différente du manifeste.")
    resultats: list[dict] = []
    empreinte = hashlib.sha256()
    taille = 0
    identifiants: set[str] = set()
    try:
        with gzip.open(archive, "rb") as flux:
            for ligne in flux:
                taille += len(ligne)
                if taille > TAILLE_DECOMPRESSEE_MAX or len(resultats) >= AVIS_PAR_ARCHIVE_MAX:
                    raise CaptureInvalide("Archive BOAMP dépassant les limites déclarées.")
                empreinte.update(ligne)
                if not ligne.endswith(b"\n"):
                    raise CaptureInvalide("Ligne JSONL incomplète.")
                avis = _normaliser(json.loads(ligne), jour=jour)
                if avis["identifiant"] in identifiants:
                    raise CaptureInvalide("Identifiant répété dans une journée.")
                identifiants.add(avis["identifiant"])
                resultats.append(avis)
    except (OSError, EOFError, UnicodeError, json.JSONDecodeError) as exc:
        raise CaptureInvalide("Archive BOAMP illisible.") from exc
    if empreinte.hexdigest() != sha_source:
        raise CaptureInvalide("Empreinte des octets décompressés incorrecte.")
    attendu = manifeste.get("avis_distincts")
    if type(attendu) is not int or attendu != len(resultats):
        raise CaptureInvalide("Décompte de la journée différent du manifeste.")
    return ({
        "chemin": relative,
        "empreinte": sha_compresse,
        "observe_le": _instant(manifeste.get("collecte_le")),
        "jour": jour,
        "jour_complet": True,
    }, resultats, sha_compresse)


def _lire_courants(racine: Path) -> tuple[dict, list[dict], str] | None:
    chemin = racine / "annonces_boamp.json"
    etat = racine / "etat_boamp.json"
    if not chemin.is_file() or not etat.is_file():
        return None
    if chemin.stat().st_size > TAILLE_COURANTE_MAX:
        raise CaptureInvalide("Relevé courant BOAMP trop volumineux.")
    octets = chemin.read_bytes()
    donnees = json.loads(octets)
    rapport = json.loads(etat.read_text(encoding="utf-8"))
    if (not isinstance(donnees, dict) or donnees.get("version") != "avis-boamp-v1"
            or not isinstance(donnees.get("annonces"), list)
            or not isinstance(rapport, dict) or
            not isinstance(rapport.get("pages_reussies"), int)
            or rapport["pages_reussies"] < 1):
        raise CaptureInvalide("Relevé courant BOAMP non confirmé.")
    bruts = donnees["annonces"]
    if len(bruts) > AVIS_COURANTS_MAX:
        raise CaptureInvalide("Relevé courant trop volumineux.")
    resultats = [_normaliser(avis, jour=None) for avis in bruts]
    if len({a["identifiant"] for a in resultats}) != len(resultats):
        raise CaptureInvalide("Identifiant répété dans le relevé courant.")
    sha = hashlib.sha256(octets).hexdigest()
    return ({
        "chemin": "annonces_boamp.json",
        "empreinte": sha,
        "observe_le": _instant(rapport.get("controle_le")),
        "jour": None,
        "jour_complet": False,
    }, resultats, sha)


class StockageBOAMP:
    """Persister les captures avec reprise et conservation des versions."""

    def __init__(self, url: str) -> None:
        self.moteur = create_engine(url, future=True)
        if self.moteur.dialect.name not in {"sqlite", "postgresql"}:
            raise ValueError("Seuls SQLite et PostgreSQL sont pris en charge.")
        meta.create_all(self.moteur)

    def _insertion(self, table: Table):
        return insert_sqlite(table) if self.moteur.dialect.name == "sqlite" else insert_postgres(table)

    def ingerer(self, capture: dict, avis: list[dict]) -> int:
        """Intégrer une capture ou annuler entièrement sa transaction."""
        horloge = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with self.moteur.begin() as connexion:
            deja = connexion.execute(
                select(captures.c.chemin).where(
                    captures.c.chemin == capture["chemin"],
                    captures.c.empreinte == capture["empreinte"],
                )
            ).first()
            if deja is not None:
                return 0
            for debut in range(0, len(avis), TAILLE_LOT):
                lot = avis[debut:debut + TAILLE_LOT]
                nouveaux = [{
                    "identifiant": x["identifiant"],
                    "empreinte": x["empreinte"],
                    "contenu": x["contenu"],
                    "observe_initialement_le": capture["observe_le"],
                    "capture_initiale": capture["chemin"],
                } for x in lot]
                statement = self._insertion(versions).values(nouveaux)
                connexion.execute(statement.on_conflict_do_nothing(
                    index_elements=[versions.c.identifiant, versions.c.empreinte]
                ))
                courants_lot = [{
                    k: x[k] for k in (
                        "identifiant", "empreinte", "objet", "acheteur",
                        "date_parution", "date_limite_reponse", "categorie_marche",
                        "etat_avis", "avis"
                    )
                } for x in lot]
                for ligne in courants_lot:
                    ligne.update(observe_le=capture["observe_le"], capture=capture["chemin"])
                statement = self._insertion(courants).values(courants_lot)
                exclu = statement.excluded
                # En cas d'égalité d'heure, une empreinte départage les versions
                # sans leur attribuer de signification chronologique artificielle.
                avancer = or_(
                    exclu.observe_le > courants.c.observe_le,
                    and_(exclu.observe_le == courants.c.observe_le,
                         exclu.empreinte > courants.c.empreinte),
                )
                connexion.execute(statement.on_conflict_do_update(
                    index_elements=[courants.c.identifiant],
                    set_={nom: getattr(exclu, nom) for nom in courants_lot[0]
                          if nom != "identifiant"},
                    where=avancer,
                ))
            connexion.execute(captures.insert().values(
                **capture, importe_le=horloge, nombre_avis=len(avis)
            ))
        return len(avis)

    def etat(self) -> dict:
        with self.moteur.connect() as connexion:
            return {
                "avis_distincts": connexion.scalar(select(func.count()).select_from(courants)),
                "versions_distinctes": connexion.scalar(select(func.count()).select_from(versions)),
                "captures_importees": connexion.scalar(select(func.count()).select_from(captures)),
                "derniere_observation": connexion.scalar(select(func.max(captures.c.observe_le))),
            }

    def rechercher(self, expression: str, limite: int = 20) -> list[dict]:
        if not 1 <= limite <= 100 or not expression.strip() or len(expression) > 150:
            raise ValueError("Expression ou limite de recherche incorrecte.")
        motif = "%" + expression.strip().replace("\\", "\\\\").replace(
            "%", "\\%").replace("_", "\\_") + "%"
        with self.moteur.connect() as connexion:
            selection = select(
                courants.c.identifiant, courants.c.objet, courants.c.acheteur,
                courants.c.date_parution, courants.c.avis, courants.c.observe_le
            ).where(or_(
                courants.c.objet.ilike(motif, escape="\\"),
                courants.c.acheteur.ilike(motif, escape="\\"),
            )).order_by(courants.c.date_parution.desc(), courants.c.identifiant).limit(limite)
            return [dict(ligne) for ligne in connexion.execute(selection).mappings()]


def importer_cycle(stockage: StockageBOAMP, racine: Path, maximum: int = 0) -> dict:
    """Lire les manifestes journaliers et le relevé courant, sans réseau."""
    if maximum < 0:
        raise ValueError("Limite d'archives incorrecte.")
    compteurs = {"captures_nouvelles": 0, "avis_lus": 0, "archives_examinees": 0}
    fiches = sorted((racine / "historique_boamp").glob("*/*/*.json"))
    for fiche in fiches[:maximum or None]:
        capture, avis, _ = _lire_archive(racine, fiche)
        compteurs["archives_examinees"] += 1
        ajout = stockage.ingerer(capture, avis)
        compteurs["avis_lus"] += ajout
        compteurs["captures_nouvelles"] += int(ajout > 0 or len(avis) == 0 and
                                            stockage.etat()["captures_importees"] > 0)
    courants_releves = _lire_courants(racine)
    if courants_releves is not None:
        capture, avis, _ = courants_releves
        avant = stockage.etat()["captures_importees"]
        ajout = stockage.ingerer(capture, avis)
        compteurs["avis_lus"] += ajout
        compteurs["captures_nouvelles"] += int(
            stockage.etat()["captures_importees"] > avant
        )
    compteurs.update(stockage.etat())
    return compteurs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True,
                        help="URL SQLAlchemy, ex. sqlite:////var/lib/frontiere/boamp.db")
    sub = parser.add_subparsers(dest="action", required=True)
    importer = sub.add_parser("importer", help="Importer les archives et le relevé courant")
    importer.add_argument("--repertoire", type=Path, default=Path(
        "institutionnel/besoins_publics"))
    importer.add_argument("--maximum-archives", type=int, default=0)
    importer.add_argument("--suivre", action="store_true",
                          help="Répéter indéfiniment l'ingestion des fichiers locaux")
    importer.add_argument("--intervalle", type=int, default=300)
    recherche = sub.add_parser("rechercher", help="Chercher dans l'index courant")
    recherche.add_argument("expression")
    recherche.add_argument("--limite", type=int, default=20)
    sub.add_parser("etat", help="État de la base persistante")
    args = parser.parse_args(argv)
    try:
        stockage = StockageBOAMP(args.base)
        if args.action == "rechercher":
            resultat = stockage.rechercher(args.expression, args.limite)
        elif args.action == "etat":
            resultat = stockage.etat()
        else:
            if args.suivre and not 15 <= args.intervalle <= 86400:
                parser.error("L'intervalle doit être compris entre 15 et 86400 secondes.")
            while True:
                resultat = importer_cycle(
                    stockage, args.repertoire, args.maximum_archives
                )
                print(json.dumps(resultat, ensure_ascii=False), flush=True)
                if not args.suivre:
                    return 0
                time.sleep(args.intervalle)
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
        return 0
    except (CaptureInvalide, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Importation BOAMP interrompue : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
