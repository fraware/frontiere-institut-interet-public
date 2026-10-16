"""Recherche locale BOAMP–DECP, intégrale à l'égard des relevés archivés.

La fusion documentaire conserve les identités distinctes :
BOAMP : identifiant d'avis ; DECP : SIRET acheteur + identifiant de marché.
Aucune concordance BOAMP–DECP n'est inférée d'un objet ou d'un acheteur similaire.
Le code réutilise l'index DECP éprouvé, avec ses versions et attestations.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from urllib.parse import urlsplit

from scripts.consolider_attributions_decp import construire_index, IndexDECPInvalide

RACINE = Path(__file__).resolve().parents[1]
BOAMP = Path("institutionnel/besoins_publics/annonces_boamp.json")
AIFE = Path("institutionnel/decp/sonde_aife_json.json")
DGFIP = Path("institutionnel/decp/lot_dgfip_xml.json")
BILAN = Path("institutionnel/decp/bilan_index_unifie.json")
VERSION = "frontiere-commande-publique-integrale-v1"
ORIGINE_BOAMP = "https://boamp-datadila.opendatasoft.com/explore/dataset/boamp/"
ETATS = {"INITIAL", "RECTIFICATIF", "ANNULATION", "MODIFICATION"}
CATEGORIES = {"SERVICES", "TRAVAUX", "FOURNITURES", ""}
ID_AVIS = re.compile(r"^\d{2}-\d{1,12}$")
SIRET = re.compile(r"^\d{14}$")
MOTS = re.compile(r"\w+", re.UNICODE)
MAX_AVIS = 200_000
SCHEMA_BOAMP = """
CREATE TABLE avis_boamp(
 identifiant TEXT PRIMARY KEY,
 titre TEXT NOT NULL,
 acheteur_declare TEXT NOT NULL,
 parution TEXT NOT NULL,
 categorie TEXT NOT NULL,
 etat_avis TEXT NOT NULL,
 date_limite_reponse TEXT,
 url_officielle TEXT NOT NULL,
 provenance TEXT NOT NULL,
 empreinte_ligne TEXT NOT NULL
);
CREATE INDEX ix_avis_parution ON avis_boamp(parution DESC, identifiant);
CREATE VIRTUAL TABLE recherche_avis USING fts5(
 identifiant UNINDEXED, titre, acheteur_declare,
 tokenize='unicode61 remove_diacritics 2'
);
CREATE TABLE meta_commande(nom TEXT PRIMARY KEY, valeur TEXT NOT NULL);
"""


class IndexCommandeInvalide(ValueError):
    pass


def imposer(ok: bool, message: str) -> None:
    if not ok:
        raise IndexCommandeInvalide(message)


def hachage(obj: object) -> str:
    return hashlib.sha256(json.dumps(
        obj, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _lire(racine: Path, chemin: Path, limite_octets: int) -> tuple[dict, str]:
    p = racine / chemin
    taille = p.stat().st_size
    imposer(0 < taille <= limite_octets, "Archive absente ou trop volumineuse : " + str(chemin))
    brut = p.read_bytes()
    try:
        objet = json.loads(brut)
    except (ValueError, UnicodeError) as exc:
        raise IndexCommandeInvalide("Archive illisible : " + str(chemin)) from exc
    imposer(isinstance(objet, dict), "Archive non structurée : " + str(chemin))
    return objet, hashlib.sha256(brut).hexdigest()


def _date_jour(valeur: object, libelle: str) -> str:
    imposer(isinstance(valeur, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", valeur) is not None,
            "Date de publication non conforme : " + libelle)
    try:
        date.fromisoformat(valeur)
    except ValueError as exc:
        raise IndexCommandeInvalide("Date civile impossible : " + libelle) from exc
    return valeur


def _limite(valeur: object) -> str | None:
    if valeur is None:
        return None
    imposer(isinstance(valeur, str) and len(valeur) <= 40 and
            ("+" in valeur or valeur.endswith("Z")),
            "Échéance BOAMP sans horodatage explicite.")
    try:
        jour = datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IndexCommandeInvalide("Échéance BOAMP impossible.") from exc
    imposer(jour.tzinfo is not None, "Échéance BOAMP sans fuseau.")
    return valeur


def _courte(valeur: object, maximum: int, *, facultative: bool = False) -> str:
    if valeur is None and facultative:
        return ""
    imposer(isinstance(valeur, str), "Champ documentaire absent ou invalide.")
    # Les titres des avis officiels contiennent parfois des séparateurs de
    # ligne : les normaliser pour la recherche, sans altérer la pièce d'origine.
    normalise = re.sub(r"[\\r\\n\\t]+", " ", valeur).strip()
    imposer(0 < len(normalise) <= maximum
            and not any(ord(c) < 32 for c in normalise),
            "Champ documentaire absent ou invalide.")
    return normalise


def _url_boamp(adresse: object) -> str:
    imposer(isinstance(adresse, str) and len(adresse) <= 500, "URL BOAMP manquante.")
    u = urlsplit(adresse)
    imposer(u.scheme == "https" and u.hostname in ("boamp.fr", "www.boamp.fr")
            and not u.username and not u.password and u.port is None
            and u.path == "/pages/avis/" and u.query.startswith("q=idweb:"),
            "Source d'avis BOAMP non officielle.")
    return adresse


def verifier_boamp(source: dict) -> list[dict]:
    imposer(source.get("version") == "avis-boamp-v1" and
            isinstance(source.get("annonces"), list) and
            0 < len(source["annonces"]) <= MAX_AVIS,
            "Archive d'avis BOAMP incompatible.")
    vus = set()
    for a in source["annonces"]:
        imposer(isinstance(a, dict), "Avis BOAMP non structuré.")
        ident = _courte(a.get("id"), 100)
        imposer(ID_AVIS.fullmatch(ident) is not None and ident not in vus,
                "Identifiant BOAMP répété ou incompatible.")
        vus.add(ident)
        _courte(a.get("objet"), 3000)
        _courte(a.get("acheteur"), 600)
        _date_jour(a.get("date_parution"), ident)
        _limite(a.get("date_limite_reponse"))
        imposer((a.get("categorie_marche") or "") in CATEGORIES
                and a.get("etat_avis") in ETATS
                and a.get("contenu_integral_copie") is False
                and a.get("catalogue_source") == ORIGINE_BOAMP,
                "Nature de l'avis ou portée de l'archive BOAMP incompatible.")
        _url_boamp(a.get("avis"))
        imposer(f"q=idweb:{ident}" in a["avis"],
                "Lien BOAMP et identifiant d'avis discordants.")
    return source["annonces"]


def _destination(racine: Path, base: Path) -> Path:
    racine = racine.resolve()
    base = base.absolute()
    imposer(base.suffix in (".sqlite3", ".sqlite", ".db")
            and not base.is_symlink()
            and not base.resolve().is_relative_to(racine),
            "Base SQLite à créer hors du dépôt, dans un chemin admis.")
    return base


def construire(racine: Path, base: Path, *, remplacer: bool = False) -> dict:
    """Reconstruire les sources dans un fichier temporaire puis remplacer atomiquement."""
    racine = racine.resolve()
    base = _destination(racine, base)
    imposer(remplacer or not base.exists(), "Base déjà présente : préciser --remplacer.")
    source, sha_boamp = _lire(racine, BOAMP, 100_000_000)
    annonces = verifier_boamp(source)
    aife, sha_aife = _lire(racine, AIFE, 80_000_000)
    dgfip, sha_dgfip = _lire(racine, DGFIP, 150_000_000)
    bilan_path = racine / BILAN
    attendu = json.loads(bilan_path.read_text(encoding="utf-8")) if bilan_path.is_file() else None
    base.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".frontiere-commande-", dir=base.parent) as folder:
        temporaire = Path(folder) / "index.sqlite3"
        try:
            bilan_decp = construire_index(
                temporaire, aife=aife, dgfip=dgfip,
                horodatage="2026-10-15T00:00:00+00:00",
            )
            if attendu is not None:
                imposer(attendu.get("version") == "index-unifie-decp-v1"
                        and attendu.get("empreintes_releves_publies") ==
                        bilan_decp["empreintes_releves_publies"]
                        and all(attendu.get(champ) == bilan_decp[champ] for champ in (
                            "fichiers_documentaires",
                            "enregistrements_normalises_par_fichier",
                            "identites_distinctes_par_siret_et_id_marche",
                            "variantes_documentaires_distinctes",
                            "identites_avec_plusieurs_variantes",
                            "attestations_documentaires",
                        )),
                        "Bilan DECP versionné divergent des archives sources.")
            cx = sqlite3.connect(temporaire)
            try:
                with cx:
                    cx.executescript(SCHEMA_BOAMP)
                    for a in annonces:
                        ident = a["id"]
                        cx.execute("""
                            INSERT INTO avis_boamp(
                                identifiant,titre,acheteur_declare,parution,categorie,
                                etat_avis,date_limite_reponse,url_officielle,provenance,
                                empreinte_ligne
                            ) VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            ident, _courte(a["objet"], 3000), _courte(a["acheteur"], 600), a["date_parution"],
                            a["categorie_marche"] or "", a["etat_avis"],
                            a["date_limite_reponse"], a["avis"], str(BOAMP), hachage(a),
                        ))
                        cx.execute("""
                            INSERT INTO recherche_avis(identifiant,titre,acheteur_declare)
                            VALUES(?,?,?)
                        """, (ident, _courte(a["objet"], 3000), _courte(a["acheteur"], 600)))
                    infos = {
                        "version": VERSION,
                        "sha256_archive_boamp": sha_boamp,
                        "sha256_releve_aife": sha_aife,
                        "sha256_releve_dgfip": sha_dgfip,
                        "avis_boamp": str(len(annonces)),
                        "marches_identites": str(bilan_decp["identites_distinctes_par_siret_et_id_marche"]),
                        "marches_variantes": str(bilan_decp["variantes_documentaires_distinctes"]),
                        "marches_attestations": str(bilan_decp["attestations_documentaires"]),
                        "fichiers_decp": str(bilan_decp["fichiers_documentaires"]),
                        "liaisons_boamp_decp_prouvees": "0",
                        "besoins_non_satisfaits_prouves": "0",
                        "couverture_nationale_demontree": "false",
                    }
                    cx.executemany("INSERT INTO meta_commande VALUES(?,?)", sorted(infos.items()))
                imposer(cx.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                        "Intégrité SQLite non établie.")
                imposer(cx.execute("PRAGMA foreign_key_check").fetchone() is None,
                        "Attestations DECP non cohérentes.")
                cx.execute("INSERT INTO recherche_avis(recherche_avis) VALUES('integrity-check')")
                cx.execute("INSERT INTO recherche_marches(recherche_marches) VALUES('integrity-check')")
            finally:
                cx.close()
            os.replace(temporaire, base)
            return {
                "version": VERSION,
                "avis_boamp": len(annonces),
                "marches_identites": bilan_decp["identites_distinctes_par_siret_et_id_marche"],
                "marches_variantes": bilan_decp["variantes_documentaires_distinctes"],
                "marches_attestations": bilan_decp["attestations_documentaires"],
                "fichiers_decp": bilan_decp["fichiers_documentaires"],
                "octets_base": base.stat().st_size,
                "liaisons_boamp_decp_prouvees": 0,
                "besoins_non_satisfaits_prouves": 0,
                "couverture_nationale_demontree": False,
            }
        except (IndexDECPInvalide, sqlite3.Error, OSError, ValueError) as exc:
            raise IndexCommandeInvalide("Construction refusée : " + str(exc)) from exc


def _ouvrir(base: Path) -> sqlite3.Connection:
    imposer(base.is_file() and not base.is_symlink(), "Base de recherche absente.")
    cx = sqlite3.connect(f"file:{base.resolve()}?mode=ro", uri=True)
    cx.row_factory = sqlite3.Row
    info = cx.execute("SELECT valeur FROM meta_commande WHERE nom='version'").fetchone()
    imposer(info is not None and info["valeur"] == VERSION, "Version d'index inconnue.")
    return cx


def _fts(texte: str) -> str:
    imposer(isinstance(texte, str) and 1 <= len(texte) <= 160
            and ";" not in texte and not any(ord(c) < 32 for c in texte),
            "Recherche textuelle incorrecte.")
    mots = MOTS.findall(texte)
    imposer(1 <= len(mots) <= 12 and all(len(m) <= 45 for m in mots),
            "Expression sans mots admissibles.")
    return " AND ".join('"' + mot + '"' for mot in mots)


def _filtre_date(texte: str | None) -> str | None:
    if texte is not None:
        return _date_jour(texte, "filtre")
    return None


def rechercher(base: Path, *, expression: str | None = None,
               source: str | None = None,
               identifiant: str | None = None,
               siret: str | None = None,
               depuis: str | None = None, jusqua: str | None = None,
               limite: int = 30, decalage: int = 0) -> dict:
    """Recherche fédérée sur deux familles documentaires ; aucune jointure supposée."""
    imposer(source in (None, "boamp", "decp") and
            type(limite) is int and 1 <= limite <= 100 and
            type(decalage) is int and 0 <= decalage <= 15000,
            "Source ou pagination incompatible.")
    imposer(any(x is not None for x in (expression, identifiant, siret)),
            "Expression, identifiant ou SIRET exact nécessaire.")
    if siret is not None:
        imposer(isinstance(siret, str) and SIRET.fullmatch(siret) is not None,
                "SIRET invalide.")
    if identifiant is not None:
        imposer(isinstance(identifiant, str) and 3 <= len(identifiant) <= 120
                and not any(ord(c) < 32 for c in identifiant),
                "Identifiant incorrect.")
    d1, d2 = _filtre_date(depuis), _filtre_date(jusqua)
    imposer(not (d1 and d2 and d1 > d2), "Intervalle inversé.")
    expr = _fts(expression) if expression is not None else None
    resultat = []
    cx = _ouvrir(base)
    try:
        if source in (None, "boamp") and siret is None:
            filtres, args = [], []
            table = "avis_boamp AS a"
            if expr:
                table += " JOIN recherche_avis ON recherche_avis.identifiant=a.identifiant"
                filtres.append("recherche_avis MATCH ?")
                # Une jointure FTS sans rowid d'avis évite de supposer un SIRET.
                args.append(expr)
            if identifiant is not None:
                filtres.append("a.identifiant=?")
                args.append(identifiant)
            if d1:
                filtres.append("a.parution>=?")
                args.append(d1)
            if d2:
                filtres.append("a.parution<=?")
                args.append(d2)
            where = " WHERE " + " AND ".join(filtres) if filtres else ""
            rows = cx.execute("""
                SELECT a.identifiant,a.titre,a.acheteur_declare,a.parution,
                       a.etat_avis,a.categorie,a.date_limite_reponse,
                       a.url_officielle,a.empreinte_ligne,a.provenance
                FROM """ + table + where, args).fetchall()
            for row in rows:
                resultat.append({
                    "source": "boamp", "identifiant": row["identifiant"],
                    "date_documentaire": row["parution"], "nature_date": "parution_avis",
                    "titre": row["titre"], "entite_declarante": row["acheteur_declare"],
                    "etat_documentaire": row["etat_avis"],
                    "categorie": row["categorie"], "date_limite_annoncee": row["date_limite_reponse"],
                    "lien_officiel": row["url_officielle"], "siret_acheteur": None,
                    "versions_documentaires": 1, "attestations": 1,
                    "empreinte_preuve": row["empreinte_ligne"],
                    "provenance": row["provenance"],
                    "besoin_non_satisfait": "non_etabli",
                })
        if source in (None, "decp"):
            filtres, args = [], []
            jointure = "versions AS v"
            if expr:
                jointure += (""" JOIN recherche_marches ON recherche_marches.cle=(
                  v.acheteur_siret || char(31) || v.id_marche || char(31) || v.empreinte_version
                  )""")
                filtres.append("recherche_marches MATCH ?")
                args.append(expr)
            if siret is not None:
                filtres.append("v.acheteur_siret=?")
                args.append(siret)
            if identifiant is not None:
                filtres.append("(v.acheteur_siret || '/' || v.id_marche)=?")
                args.append(identifiant)
            if d1:
                filtres.append("COALESCE(v.date_notification,v.date_publication_declaree)>=?")
                args.append(d1)
            if d2:
                filtres.append("COALESCE(v.date_notification,v.date_publication_declaree)<=?")
                args.append(d2)
            where = " WHERE " + " AND ".join(filtres) if filtres else ""
            rows = cx.execute("""
                SELECT v.acheteur_siret,v.id_marche,v.empreinte_version,v.objet,
                       v.code_cpv,v.date_notification,v.date_publication_declaree,
                       (SELECT COUNT(*) FROM attestations att WHERE
                         att.acheteur_siret=v.acheteur_siret AND
                         att.id_marche=v.id_marche AND
                         att.empreinte_version=v.empreinte_version) AS attestations,
                       (SELECT COUNT(*) FROM versions vv WHERE
                         vv.acheteur_siret=v.acheteur_siret AND
                         vv.id_marche=v.id_marche) AS versions
                FROM """ + jointure + where, args).fetchall()
            # Plusieurs versions ne constituent pas plusieurs contrats.
            groupes = {}
            for row in rows:
                ident = row["acheteur_siret"] + "/" + row["id_marche"]
                date_doc = row["date_notification"] or row["date_publication_declaree"]
                ordre = (date_doc or "", row["empreinte_version"])
                if ident not in groupes:
                    groupes[ident] = (ordre, row, 1)
                else:
                    vieux_ordre, vieux, compte = groupes[ident]
                    groupes[ident] = (
                        ordre if ordre > vieux_ordre else vieux_ordre,
                        row if ordre > vieux_ordre else vieux, compte + 1)
            for ident, (_, row, compte) in groupes.items():
                resultat.append({
                    "source": "decp", "identifiant": ident,
                    "date_documentaire": row["date_notification"] or row["date_publication_declaree"],
                    "nature_date": ("notification_marche" if row["date_notification"]
                                    else "publication_declaree" if row["date_publication_declaree"]
                                    else "inconnue"),
                    "titre": row["objet"],
                    "entite_declarante": "Acheteur SIRET " + row["acheteur_siret"],
                    "etat_documentaire": "marche_attribue_declare",
                    "categorie": row["code_cpv"], "date_limite_annoncee": None,
                    "lien_officiel": None, "siret_acheteur": row["acheteur_siret"],
                    "versions_documentaires": row["versions"],
                    "versions_correspondantes": compte,
                    "attestations": row["attestations"],
                    "empreinte_preuve": row["empreinte_version"],
                    "provenance": "attestations_DECP_47_fichiers_repertories",
                    "besoin_non_satisfait": "non_etabli",
                })
        resultat.sort(key=lambda r: (r["date_documentaire"] or "", r["source"],
                                    r["identifiant"]), reverse=True)
        page = resultat[decalage:decalage + limite]
        return {
            "version": VERSION,
            "resultats_totaux": len(resultat),
            "resultats": page,
            "liens_contractuels_inferes": 0,
            "couverture_nationale_demontree": False,
            "pagination": {"limite": limite, "decalage": decalage},
        }
    finally:
        cx.close()


def bilan(base: Path) -> dict:
    cx = _ouvrir(base)
    try:
        d = dict(cx.execute("SELECT nom,valeur FROM meta_commande"))
        return {
            "version": d["version"],
            "avis_boamp": int(d["avis_boamp"]),
            "marches_identites": int(d["marches_identites"]),
            "marches_variantes": int(d["marches_variantes"]),
            "marches_attestations": int(d["marches_attestations"]),
            "fichiers_decp": int(d["fichiers_decp"]),
            "sha256_archive_boamp": d["sha256_archive_boamp"],
            "sha256_releve_aife": d["sha256_releve_aife"],
            "sha256_releve_dgfip": d["sha256_releve_dgfip"],
            "liaisons_boamp_decp_prouvees": 0,
            "besoins_non_satisfaits_prouves": 0,
            "couverture_nationale_demontree": False,
        }
    finally:
        cx.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="commande", required=True)
    c = sub.add_parser("construire")
    c.add_argument("--racine", type=Path, default=RACINE)
    c.add_argument("--base", type=Path, required=True)
    c.add_argument("--remplacer", action="store_true")
    r = sub.add_parser("rechercher")
    r.add_argument("--base", type=Path, required=True)
    r.add_argument("--expression")
    r.add_argument("--source", choices=["boamp", "decp"])
    r.add_argument("--identifiant")
    r.add_argument("--siret")
    r.add_argument("--depuis")
    r.add_argument("--jusqua")
    r.add_argument("--limite", type=int, default=30)
    r.add_argument("--decalage", type=int, default=0)
    b = sub.add_parser("bilan")
    b.add_argument("--base", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.commande == "construire":
            sortie = construire(a.racine, a.base, remplacer=a.remplacer)
        elif a.commande == "rechercher":
            sortie = rechercher(a.base, expression=a.expression, source=a.source,
                                identifiant=a.identifiant, siret=a.siret,
                                depuis=a.depuis, jusqua=a.jusqua,
                                limite=a.limite, decalage=a.decalage)
        else:
            sortie = bilan(a.base)
        print(json.dumps(sortie, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, sqlite3.Error) as exc:
        p.exit(1, f"Index BOAMP–DECP refusé : {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
