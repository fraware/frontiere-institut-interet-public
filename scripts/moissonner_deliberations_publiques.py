"""Repérer des délibérations locales techniques dans des CSV publics au schéma SCDL.

Une entrée signale un objet de délibération susceptible de justifier une enquête.
Ni l'objet ni le lien ni un mot-clé ne démontrent la livraison d'une prestation.
Aucun document annexé n'est ouvert ou téléchargé. Aucun texte libre n'est conservé.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "institutionnel" / "deliberations_publiques"
CATALOGUE = "https://www.data.gouv.fr/api/1/datasets/"
HOTES_CSV = {"static.data.gouv.fr", "tabular-api.data.gouv.fr"}
RESSOURCE_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
RECHERCHES = ("délibérations", "deliberations", "actes réglementaires")
# Repérages déjà confirmés comme jeux publics sur data.gouv.fr le 14/10/2026.
# Les fiches de catalogue restent à télécharger et à valider au cours du passage.
JEUX_CIBLES = (
    "deliberations-2026",
    "deliberations-2025",
    "deliberations-evry-courcouronnes-format-scdl",
    "deliberations-du-conseil-municipal-de-la-possession",
    "deliberations-23",
    "deliberations-des-organismes-adherents-du-gip-recia",
    "deliberations-mandature-2020-2026-1",
    "deliberations-mandature-2026-2033",
    "sla-deliberations-depuis-2017-de-saint-louis-agglomeration",
    "deliberations-du-conseil-departemental-du-cher-et-de-la-commission-permanente",
)
URLS_CIBLEES = frozenset(CATALOGUE + code + "/" for code in JEUX_CIBLES)
MAX_OCTETS_META = 3_000_000
MAX_OCTETS_CSV = 12_000_000
MAX_DATASETS = 180
MAX_RESSOURCES_CSV = 25
MAX_LIGNES_CSV = 80_000
MAX_CANDIDATS = 1200
AGENT = "FRONTIERE-deliberations-publiques/1.0 (donnees ouvertes; contact via depot)"
CHAMPS = {"COLL_SIRET", "DELIB_ID", "DELIB_DATE", "DELIB_OBJET"}
REGLES = {
    "intelligence_artificielle": r"\bintelligence artificielle\b|\bia generative\b|\bchatbot\b",
    "expertise_juridique": r"\bdelibia\b|\bassistant juridique\b|\bassistance juridique\b",
    "transcription": r"\btranscription automatique\b|\bretranscription\b",
    "cybersecurite": r"\bcybersecurite\b|\bsecurite des systemes d.information\b",
    "experimentations_techniques": (
        r"\bexperimentation (?:d.un |de la |d.)(?:logiciel|outil numerique|"
        r"solution numerique|intelligence artificielle)\b"
    ),
    "formation_technique": (
        r"\bformation (?:a l.|en |aux )(?:intelligence artificielle|"
        r"cybersecurite|outils numeriques)\b"
    ),
}
MOTIFS = {k: re.compile(v) for k, v in REGLES.items()}


class CollecteInvalide(ValueError):
    """Signaler une source, un schéma ou une réponse hors du périmètre."""


class SansRedirection(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CollecteInvalide("Redirection interdite : provenance indéterminée")


def horodatage() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def adresse_autorisee(url: object, *, catalogue: bool = False) -> bool:
    if not isinstance(url, str) or len(url) > 2048:
        return False
    p = urlsplit(url)
    hote = "www.data.gouv.fr" if catalogue else None
    return (
        p.scheme == "https" and p.hostname is not None
        and p.hostname in ({hote} if catalogue else HOTES_CSV)
        and p.port is None and not p.username and not p.password
        and not p.fragment
        and ((p.path == "/api/1/datasets/" or url in URLS_CIBLEES) if catalogue else
             (p.hostname == "static.data.gouv.fr" and p.path.startswith("/resources/"))
             or (p.hostname == "tabular-api.data.gouv.fr" and
                 re.fullmatch(r"/api/resources/[0-9a-f-]{36}/data/csv/", p.path) is not None))
    )


def reference_document(url: object) -> str | None:
    if not isinstance(url, str) or len(url) > 2048:
        return None
    p = urlsplit(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.fragment:
        return None
    if p.hostname in {"localhost", "127.0.0.1", "::1"} or p.hostname.endswith(".local"):
        return None
    if p.port not in (None, 443):
        return None
    return url


def obtenir(url: str, plafond: int) -> bytes:
    """Télécharger une seule ressource au domaine fixé, sans redirection."""
    if not (
        (plafond == MAX_OCTETS_META and adresse_autorisee(url, catalogue=True))
        or (plafond == MAX_OCTETS_CSV and adresse_autorisee(url))
    ):
        raise CollecteInvalide("Adresse non autorisée pour ce téléchargement")
    req = Request(url, headers={"User-Agent": AGENT, "Accept": "text/csv, application/json"})
    with build_opener(SansRedirection).open(req, timeout=22) as reponse:
        if reponse.status != 200 or reponse.geturl() != url:
            raise CollecteInvalide("Réponse HTTP ou destination inattendue")
        data = reponse.read(plafond + 1)
    if len(data) > plafond:
        raise CollecteInvalide("Taille de réponse supérieure au plafond")
    return data


def sans_accents(texte: str) -> str:
    normalise = unicodedata.normalize("NFKD", texte.casefold())
    return "".join(c for c in normalise if not unicodedata.combining(c))


def requete(terme: str, page: int = 1) -> str:
    if terme not in RECHERCHES or type(page) is not int or page not in (1, 2, 3, 4):
        raise CollecteInvalide("Recherche hors de la sélection autorisée")
    return CATALOGUE + "?" + urlencode({"q": terme, "page": page, "page_size": 50})


def selectionner_datasets(pages: list[dict]) -> list[dict]:
    """Réduire les métadonnées à des jeux licites de délibérations."""
    choix: dict[str, dict] = {}
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            raise CollecteInvalide("Catalogue sans liste de jeux")
        for jeu in page["data"]:
            if not isinstance(jeu, dict) or jeu.get("private") is True:
                continue
            uid = jeu.get("id")
            titre = jeu.get("title")
            if not isinstance(uid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{5,120}", uid):
                continue
            if not isinstance(titre, str) or not any(
                token in sans_accents(titre) for token in ("deliberation", "actes reglementaires")
            ):
                continue
            lic = jeu.get("license")
            lic = lic.get("id") if isinstance(lic, dict) else lic
            if lic not in {"lov2", "lov1", "cc0", "cc-zero", "odbl"}:
                continue
            ressources = jeu.get("resources")
            if not isinstance(ressources, list):
                continue
            csvs = []
            for res in ressources:
                if not isinstance(res, dict):
                    continue
                rid, url = res.get("id"), res.get("url")
                if (isinstance(rid, str) and re.fullmatch(r"[a-zA-Z0-9_-]{5,120}", rid)
                        and str(res.get("format", "")).lower() == "csv"):
                    if adresse_autorisee(url):
                        adresse_csv = url
                    elif RESSOURCE_UUID.fullmatch(rid.lower()):
                        # La lecture passe par le service public tabulaire,
                        # jamais par le domaine externe contenu dans la fiche.
                        adresse_csv = (
                            "https://tabular-api.data.gouv.fr/api/resources/"
                            + rid.lower() + "/data/csv/"
                        )
                    else:
                        continue
                    csvs.append({"id": rid, "url": adresse_csv})
            if csvs and uid not in choix:
                choix[uid] = {
                    "id": uid, "titre": titre.strip()[:180], "licence": lic,
                    "ressources": csvs[:5],
                }
    return [choix[k] for k in sorted(choix)][:MAX_DATASETS]


def extraire_csv(donnees: bytes, *, jeu: dict, ressource: dict, instant: str) -> tuple[list[dict], int]:
    """Repérer une sélection de lignes structurées, sans conserver le texte libre."""
    try:
        texte = donnees.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CollecteInvalide("CSV non décodable en UTF-8") from exc
    en_tete = texte.splitlines()[0] if texte.splitlines() else ""
    sep = ";" if en_tete.count(";") > en_tete.count(",") else ","
    lecture = csv.DictReader(io.StringIO(texte, newline=""), delimiter=sep)
    if not lecture.fieldnames or not CHAMPS.issubset(
        {x.strip().upper() for x in lecture.fieldnames}
    ):
        raise CollecteInvalide("Colonnes SCDL absentes")
    if len(lecture.fieldnames) != len(set(lecture.fieldnames)):
        raise CollecteInvalide("En-têtes dupliqués")
    trouves: list[dict] = []
    lus = 0
    empreinte_ressource = hashlib.sha256(donnees).hexdigest()
    for brut in lecture:
        lus += 1
        if lus > MAX_LIGNES_CSV:
            raise CollecteInvalide("CSV au-delà du plafond de lignes")
        ligne = {str(k).strip().upper(): v for k, v in brut.items() if k is not None}
        objet = ligne.get("DELIB_OBJET", "")
        if not isinstance(objet, str):
            continue
        codes = sorted(n for n, motif in MOTIFS.items() if motif.search(sans_accents(objet)))
        if not codes:
            continue
        siret = ligne.get("COLL_SIRET", "").strip()
        reference = ligne.get("DELIB_ID", "").strip()
        jour = ligne.get("DELIB_DATE", "").strip()
        if not re.fullmatch(r"\d{14}", siret) or not 1 <= len(reference) <= 120:
            continue
        try:
            if date.fromisoformat(jour).isoformat() != jour:
                continue
        except ValueError:
            continue
        cle = "\n".join((jeu["id"], ressource["id"], siret, reference))
        nom = ligne.get("COLL_NOM", "")
        adresse = reference_document(ligne.get("DELIB_URL"))
        trouves.append({
            "identifiant": hashlib.sha256(cle.encode("utf-8")).hexdigest(),
            "jeu_id": jeu["id"], "ressource_id": ressource["id"],
            "collectivite": nom[:160] if isinstance(nom, str) else "",
            "collectivite_siret": siret,
            "deliberation_id": reference, "deliberation_date": jour,
            "mots_de_reperage": codes, "url_document_annonce": adresse,
            "url_ressource_csv": ressource["url"],
            "sha256_csv": empreinte_ressource,
            "sha256_ligne": hashlib.sha256(
                json.dumps(ligne, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "constat": "correspondance_textuelle_non_qualifiee",
            "preuve_usage_verifiee": False, "observe_pour_la_premiere_fois": instant,
        })
    return trouves, lus


def collecter(*, ancien: dict, etat_precedent: dict | None = None,
             charger=obtenir, instant: str | None = None,
             patienter=time.sleep) -> tuple[dict, dict]:
    """Préserver tous les constats passés lorsque des téléchargements échouent."""
    instant = instant or horodatage()
    if not isinstance(ancien, dict) or ancien.get("version") != "pistes-deliberations-v1":
        raise CollecteInvalide("Registre antérieur invalide")
    precedents = ancien.get("pistes")
    if not isinstance(precedents, list):
        raise CollecteInvalide("Liste de pistes antérieures invalide")
    acquis = {x["identifiant"]: x for x in precedents if isinstance(x, dict)
              and isinstance(x.get("identifiant"), str)}
    if len(acquis) > MAX_CANDIDATS:
        raise CollecteInvalide("Registre antérieur trop grand")
    pages, echecs = [], []
    tentatives = 0
    for terme in RECHERCHES:
        for page in (1, 2, 3, 4):
            adresse = requete(terme, page)
            tentatives += 1
            try:
                brut = charger(adresse, MAX_OCTETS_META)
                reponse = json.loads(brut)
                if not isinstance(reponse, dict) or not isinstance(reponse.get("data"), list):
                    raise CollecteInvalide("Catalogue invalide")
                pages.append(reponse)
                if not reponse.get("next_page") and len(reponse["data"]) < 50:
                    break
            except (OSError, ValueError, HTTPError, URLError) as exc:
                echecs.append({"type": "catalogue", "terme": terme, "page": page,
                               "motif": type(exc).__name__})
                break
            finally:
                patienter(0.12)
    fiches_ciblees_reussies = 0
    for code in JEUX_CIBLES:
        adresse = CATALOGUE + code + "/"
        tentatives += 1
        try:
            jeu = json.loads(charger(adresse, MAX_OCTETS_META))
            if not isinstance(jeu, dict) or jeu.get("slug") not in (code, None):
                raise CollecteInvalide("Fiche ciblée incohérente")
            # Une fiche de jeu directe n'a pas la même enveloppe que la recherche.
            if not isinstance(jeu.get("id"), str) or not isinstance(jeu.get("resources"), list):
                raise CollecteInvalide("Fiche ciblée sans identité ou ressources")
            pages.append({"data": [jeu]})
            fiches_ciblees_reussies += 1
        except (OSError, ValueError, HTTPError, URLError) as exc:
            echecs.append({"type": "fiche_ciblee", "code": code,
                           "motif": type(exc).__name__})
        finally:
            patienter(0.12)
    if not pages:
        raise CollecteInvalide("Aucune page de catalogue valide : sorties préservées")
    jeux = selectionner_datasets(pages)
    candidats = [(jeu, res) for jeu in jeux for res in jeu["ressources"]]
    dernier_etat = etat_precedent or {}
    if not isinstance(dernier_etat, dict):
        raise CollecteInvalide("État de progression invalide")
    position = dernier_etat.get("position_suivante", 0)
    if type(position) is not int or position < 0:
        raise CollecteInvalide("Curseur de progression incorrect")
    # Un inventaire évolutif ne garantit pas la stabilité des positions :
    # le curseur borne les lots mais ne prouve pas une exhaustivité historique.
    debut = position % len(candidats) if candidats else 0
    fin = min(len(candidats), debut + MAX_RESSOURCES_CSV)
    lot = candidats[debut:fin]
    suivant = 0 if fin == len(candidats) else fin
    telecharges = 0
    lignes = 0
    nouveaux = 0
    schemas_refuses = 0
    for jeu, res in lot:
        try:
            donnees = charger(res["url"], MAX_OCTETS_CSV)
            telecharges += 1
            extraits, nb = extraire_csv(donnees, jeu=jeu, ressource=res, instant=instant)
            lignes += nb
            for candidat in extraits:
                key = candidat["identifiant"]
                if key in acquis:
                    # Préserver l'observation initiale sans compter plusieurs copies.
                    if (acquis[key].get("sha256_ligne") != candidat["sha256_ligne"]
                            or acquis[key].get("sha256_csv") != candidat["sha256_csv"]):
                        candidat["observe_pour_la_premiere_fois"] = (
                            acquis[key].get("observe_pour_la_premiere_fois", instant)
                        )
                        acquis[key] = candidat
                elif len(acquis) < MAX_CANDIDATS:
                    acquis[key] = candidat
                    nouveaux += 1
        except (OSError, ValueError, HTTPError, URLError) as exc:
            schemas_refuses += isinstance(exc, CollecteInvalide)
            echecs.append({"type": "csv", "jeu_id": jeu["id"],
                           "ressource_id": res["id"], "motif": type(exc).__name__})
        finally:
            patienter(0.12)
    resultat = {
        "version": "pistes-deliberations-v1",
        "portee": "reperage_textuel_uniquement_sans_preuve_d_execution",
        "pistes": [acquis[k] for k in sorted(acquis)],
    }
    etat = {
        "version": "collecte-deliberations-scdl-v1", "controle_le": instant,
        "requetes_catalogue": tentatives,
        "pages_catalogue_reussies": len(pages) - fiches_ciblees_reussies,
        "fiches_ciblees_tentees": len(JEUX_CIBLES),
        "fiches_ciblees_reussies": fiches_ciblees_reussies,
        "jeux_retenus": len(jeux), "ressources_csv_eligibles": len(candidats),
        "ressources_csv_examinees": len(lot),
        "position_initiale": debut,
        "position_suivante": suivant,
        "tour_du_releve_termine": bool(candidats) and suivant == 0,
        "paginage_ressources_csv_verifie": False,
        "ressources_sources_externes_directes_appelees": 0,
        "ressources_csv_telechargees": telecharges,
        "csv_schemas_refuses": schemas_refuses,
        "lignes_scdl_examinees": lignes, "nouvelles_pistes": nouveaux,
        "pistes_conservees": len(acquis),
        "echecs": echecs[:30], "couverture_exhaustive": False,
        "documents_primaires_pdf_telecharges": 0,
        "utilisations_effectives_deduites": 0,
    }
    return resultat, etat


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, default=SORTIE)
    args = p.parse_args()
    precedent = args.sortie / "pistes.json"
    try:
        ancien = (json.loads(precedent.read_text(encoding="utf-8"))
                  if precedent.exists() else {"version": "pistes-deliberations-v1", "pistes": []})
        etat_precedent = args.sortie / "etat_collecte.json"
        precedent_etat = (json.loads(etat_precedent.read_text(encoding="utf-8"))
                          if etat_precedent.exists() else None)
        resultat, etat = collecter(ancien=ancien, etat_precedent=precedent_etat)
        args.sortie.mkdir(parents=True, exist_ok=True)
        for nom, valeur in (("pistes.json", resultat), ("etat_collecte.json", etat)):
            chemin = args.sortie / nom
            temporaire = chemin.with_suffix(".json.temp")
            temporaire.write_text(json.dumps(
                valeur, ensure_ascii=False, sort_keys=True, indent=2
            ) + "\n", encoding="utf-8")
            temporaire.replace(chemin)
        print(json.dumps(etat, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        p.exit(1, f"Collecte SCDL interrompue : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
