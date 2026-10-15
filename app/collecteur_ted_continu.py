"""Collecter les avis TED concernant les acheteurs français dans une base durable.

Interface officielle TED Search API v3, sans clef. Chaque date de publication
est interrogée en mode ITERATION, avec pagination complète. Une recherche
incomplète ne modifie aucune notice ni capture déjà validée pour cette date.
L'historique des variantes et la réponse originale sont conservés.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://api.ted.europa.eu/v3/notices/search"
CHAMPS = [
    "publication-number", "publication-date", "notice-title", "buyer-name",
    "buyer-country", "notice-type", "classification-cpv", "deadline",
    "procedure-identifier", "buyer-identifier",
]
NOMBRE_PAR_PAGE = 200
PLAFOND_JOUR = 30_000
PLAFOND_REPONSE = 8 * 1024 * 1024
PUBLICATION = re.compile(r"^[0-9]{1,8}-20[0-9]{2}$")
SCHEMA = """
CREATE TABLE IF NOT EXISTS avis_ted (
  numero TEXT PRIMARY KEY,
  date_publication TEXT NOT NULL,
  titre TEXT NOT NULL,
  acheteur TEXT NOT NULL,
  pays_acheteur TEXT,
  type_avis TEXT,
  codes_cpv TEXT,
  date_limite TEXT,
  empreinte_courante TEXT NOT NULL,
  observe_le TEXT NOT NULL,
  source_url TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ted_date ON avis_ted(date_publication);
CREATE INDEX IF NOT EXISTS ix_ted_acheteur ON avis_ted(acheteur);
CREATE TABLE IF NOT EXISTS versions_avis_ted (
  numero TEXT NOT NULL,
  empreinte TEXT NOT NULL,
  contenu_source TEXT NOT NULL,
  premiere_observation TEXT NOT NULL,
  PRIMARY KEY(numero, empreinte)
);
CREATE TABLE IF NOT EXISTS captures_ted (
  jour TEXT PRIMARY KEY,
  empreinte TEXT NOT NULL,
  observe_le TEXT NOT NULL,
  notices INTEGER NOT NULL,
  pages INTEGER NOT NULL
);
"""


class TEDInvalide(ValueError):
    """Réponse TED incomplète, incompatible ou hors des plafonds."""


def instant() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def requete_ted(corps: dict) -> dict:
    """POST JSON borné vers la seule interface officielle configurée."""
    charge = json.dumps(corps, ensure_ascii=False).encode("utf-8")
    requete = Request(URL, data=charge, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "FRONTIERE-collecte-TED/1.0",
    }, method="POST")
    with urlopen(requete, timeout=70) as flux:
        if flux.status != 200 or flux.geturl() != URL:
            raise TEDInvalide("Réponse HTTP TED inattendue.")
        octets = flux.read(PLAFOND_REPONSE + 1)
    if len(octets) > PLAFOND_REPONSE:
        raise TEDInvalide("Réponse TED trop volumineuse.")
    resultat = json.loads(octets)
    if not isinstance(resultat, dict):
        raise TEDInvalide("Enveloppe TED invalide.")
    return resultat


def _texte(valeur: object, *, longueur: int = 400) -> str:
    """Résoudre les scalaires et libellés multilingues de la recherche TED."""
    if isinstance(valeur, str):
        return valeur[:longueur]
    if isinstance(valeur, list):
        return next((_texte(v, longueur=longueur) for v in valeur
                     if _texte(v, longueur=longueur)), "")
    if isinstance(valeur, dict):
        for langue in ("fra", "eng"):
            texte = _texte(valeur.get(langue), longueur=longueur)
            if texte:
                return texte
        return next((_texte(x, longueur=longueur) for x in valeur.values()
                     if _texte(x, longueur=longueur)), "")
    return ""


def _notice(brut: object, jour: date) -> dict:
    if not isinstance(brut, dict):
        raise TEDInvalide("Notice TED non structurée.")
    numero = _texte(brut.get("publication-number"), longueur=30)
    if not PUBLICATION.fullmatch(numero):
        raise TEDInvalide("Numéro de publication TED incorrect.")
    publication = _texte(brut.get("publication-date"), longueur=40)
    if publication[:10] != jour.isoformat():
        raise TEDInvalide("Avis en dehors de la journée demandée.")
    canon = json.dumps(brut, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False)
    if len(canon) > 140_000:
        raise TEDInvalide("Notice TED démesurée.")
    return {
        "numero": numero, "empreinte": hashlib.sha256(canon.encode()).hexdigest(),
        "contenu_source": canon, "date_publication": jour.isoformat(),
        "titre": _texte(brut.get("notice-title"), longueur=400),
        "acheteur": _texte(brut.get("buyer-name"), longueur=400),
        "pays_acheteur": _texte(brut.get("buyer-country"), longueur=80),
        "type_avis": _texte(brut.get("notice-type"), longueur=80),
        "codes_cpv": _texte(brut.get("classification-cpv"), longueur=500),
        "date_limite": _texte(brut.get("deadline"), longueur=100),
        "source_url": f"https://ted.europa.eu/fr/notice/-/detail/{numero}",
    }


def collecter_jour(jour: date, *, obtenir=requete_ted,
                   attendre=time.sleep) -> tuple[list[dict], int]:
    """Parcourir une journée française via la pagination numérotée complète."""
    if not isinstance(jour, date) or jour > datetime.now(timezone.utc).date():
        raise TEDInvalide("Journée TED impossible ou future.")
    chaine = jour.strftime("%Y%m%d")
    corps = {
        "query": f"buyer-country = FRA AND publication-date = {chaine}",
        "fields": CHAMPS,
        "limit": NOMBRE_PAR_PAGE,
        "scope": "ALL",
        "paginationMode": "PAGE_NUMBER",
        "page": 1,
    }
    documents: dict[str, dict] = {}
    total: int | None = None
    pages = 0
    while True:
        pages += 1
        if pages > 200:
            raise TEDInvalide("Trop de pages dans une même journée TED.")
        resultat = obtenir(dict(corps))
        if (not isinstance(resultat, dict)
                or resultat.get("timedOut") is True
                or not isinstance(resultat.get("notices"), list)):
            raise TEDInvalide("Réponse TED absente, expirée ou incorrecte.")
        decompte = resultat.get("totalNoticeCount")
        if type(decompte) is not int or decompte < 0 or decompte > 15_000:
            raise TEDInvalide("Décompte TED absent ou supérieur à 15 000 avis.")
        if total is None:
            total = decompte
        elif total != decompte:
            raise TEDInvalide("Décompte TED modifié pendant la pagination.")
        lignes = resultat["notices"]
        if len(lignes) > NOMBRE_PAR_PAGE:
            raise TEDInvalide("Page TED supérieure à la taille autorisée.")
        for brut in lignes:
            element = _notice(brut, jour)
            numero = element["numero"]
            if numero in documents and documents[numero]["empreinte"] != element["empreinte"]:
                raise TEDInvalide("Deux versions différentes dans une même collecte.")
            documents[numero] = element
            if len(documents) > PLAFOND_JOUR:
                raise TEDInvalide("Trop de notices TED dans une journée.")
        if pages * NOMBRE_PAR_PAGE >= total:
            break
        if not lignes:
            raise TEDInvalide("Page intermédiaire TED vide avant le total déclaré.")
        corps["page"] = pages + 1
        attendre(0.4)
    if len(documents) != total:
        raise TEDInvalide("Pagination TED incomplète selon le total déclaré.")
    return list(documents.values()), pages


class StockageTED:
    def __init__(self, fichier: Path):
        self.fichier = fichier
        fichier.parent.mkdir(parents=True, exist_ok=True)
        with self.connexion() as conn:
            conn.executescript(SCHEMA)

    def connexion(self):
        conn = sqlite3.connect(self.fichier, timeout=60)
        conn.execute("PRAGMA busy_timeout=60000")
        return conn

    def importer(self, jour: date, notices: list[dict], pages: int) -> dict:
        """Appliquer un cliché journalier complet en une seule transaction."""
        horloge = instant()
        notices_ordonnees = sorted(notices, key=lambda x: x["numero"])
        digest = hashlib.sha256(json.dumps(
            [(v["numero"], v["empreinte"]) for v in notices_ordonnees],
            separators=(",", ":")
        ).encode()).hexdigest()
        with self.connexion() as conn:
            precedent = conn.execute(
                "SELECT empreinte FROM captures_ted WHERE jour=?",
                (jour.isoformat(),),
            ).fetchone()
            if precedent and precedent[0] == digest:
                return {"jour": jour.isoformat(), "etat": "inchangé",
                        "avis": len(notices), "pages": pages}
            for n in notices_ordonnees:
                conn.execute(
                    "INSERT OR IGNORE INTO versions_avis_ted"
                    " (numero, empreinte, contenu_source, premiere_observation)"
                    " VALUES (?,?,?,?)",
                    (n["numero"], n["empreinte"], n["contenu_source"], horloge),
                )
                conn.execute(
                    "INSERT INTO avis_ted (numero,date_publication,titre,acheteur,"
                    "pays_acheteur,type_avis,codes_cpv,date_limite,empreinte_courante,"
                    "observe_le,source_url) VALUES (?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(numero) DO UPDATE SET "
                    "titre=excluded.titre,acheteur=excluded.acheteur,"
                    "pays_acheteur=excluded.pays_acheteur,"
                    "type_avis=excluded.type_avis,codes_cpv=excluded.codes_cpv,"
                    "date_limite=excluded.date_limite,"
                    "empreinte_courante=excluded.empreinte_courante,"
                    "observe_le=excluded.observe_le",
                    (n["numero"], n["date_publication"], n["titre"], n["acheteur"],
                     n["pays_acheteur"], n["type_avis"], n["codes_cpv"], n["date_limite"],
                     n["empreinte"], horloge, n["source_url"]),
                )
            conn.execute(
                "INSERT INTO captures_ted(jour,empreinte,observe_le,notices,pages)"
                " VALUES (?,?,?,?,?) ON CONFLICT(jour) DO UPDATE SET "
                "empreinte=excluded.empreinte,observe_le=excluded.observe_le,"
                "notices=excluded.notices,pages=excluded.pages",
                (jour.isoformat(), digest, horloge, len(notices), pages),
            )
        return {"jour": jour.isoformat(), "etat": "actualisé",
                "avis": len(notices), "pages": pages}

    def etat(self) -> dict:
        with self.connexion() as conn:
            return {
                "avis": conn.execute("SELECT COUNT(*) FROM avis_ted").fetchone()[0],
                "versions": conn.execute(
                    "SELECT COUNT(*) FROM versions_avis_ted"
                ).fetchone()[0],
                "jours": conn.execute("SELECT COUNT(*) FROM captures_ted").fetchone()[0],
                "dernier_jour": conn.execute(
                    "SELECT MAX(jour) FROM captures_ted"
                ).fetchone()[0],
            }

    def rechercher(self, expression: str, limite: int = 25) -> list[dict]:
        if not isinstance(expression, str) or not 1 <= len(expression.strip()) <= 150:
            raise ValueError("Expression de recherche TED incorrecte.")
        if type(limite) is not int or not 1 <= limite <= 100:
            raise ValueError("Limite de recherche incorrecte.")
        motif = "%" + expression.strip().replace("\\", "\\\\").replace(
            "%", "\\%").replace("_", "\\_") + "%"
        with self.connexion() as conn:
            conn.row_factory = sqlite3.Row
            lignes = conn.execute(
                "SELECT numero,date_publication,titre,acheteur,codes_cpv,"
                "date_limite,source_url FROM avis_ted WHERE "
                "titre LIKE ? ESCAPE '\\' OR acheteur LIKE ? ESCAPE '\\' "
                "ORDER BY date_publication DESC, numero DESC LIMIT ?",
                (motif, motif, limite),
            )
            return [dict(x) for x in lignes]


def cycle(stockage: StockageTED, *, jours: int = 4,
          premier: date | None = None, obtenir=requete_ted,
          attendre=time.sleep) -> dict:
    if not 1 <= jours <= 31:
        raise ValueError("Nombre de journées TED incorrect.")
    fin = datetime.now(timezone.utc).date()
    debut = premier or fin - timedelta(days=jours - 1)
    resultats = []
    for i in range(jours):
        jour = debut + timedelta(days=i)
        notices, pages = collecter_jour(jour, obtenir=obtenir, attendre=attendre)
        resultats.append(stockage.importer(jour, notices, pages))
    return {"captures": resultats, **stockage.etat()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    actions = parser.add_subparsers(dest="action", required=True)
    run = actions.add_parser("collecter")
    run.add_argument("--jours", type=int, default=4)
    run.add_argument("--depuis", type=date.fromisoformat)
    run = actions.add_parser("suivre")
    run.add_argument("--jours", type=int, default=4)
    run.add_argument("--intervalle", type=int, default=7200)
    actions.add_parser("etat")
    search = actions.add_parser("rechercher")
    search.add_argument("expression")
    search.add_argument("--limite", type=int, default=25)
    args = parser.parse_args(argv)
    try:
        base = StockageTED(args.base)
        if args.action == "etat":
            resultat = base.etat()
        elif args.action == "rechercher":
            resultat = base.rechercher(args.expression, args.limite)
        else:
            if args.action == "suivre" and not 3600 <= args.intervalle <= 604800:
                parser.error("Intervalle TED hors limites.")
            while True:
                debut = args.depuis if args.action == "collecter" else None
                resultat = cycle(base, jours=args.jours, premier=debut)
                print(json.dumps(resultat, ensure_ascii=False), flush=True)
                if args.action != "suivre":
                    return 0
                time.sleep(args.intervalle)
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, HTTPError, URLError, json.JSONDecodeError,
            sqlite3.Error) as exc:
        print(f"TED : {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
