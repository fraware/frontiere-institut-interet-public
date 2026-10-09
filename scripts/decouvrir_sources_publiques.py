"""Découvrir et suivre les métadonnées publiques de data.gouv.fr sans copier les fichiers.

La recherche est bornée et non exhaustive. Les identifiants déjà rencontrés
sont conservés à chaque interrogation réussie ou partiellement réussie.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "institutionnel" / "decouverte"
CONFIG = DOSSIER / "recherches_v1.json"
REGISTRE = RACINE / "institutionnel" / "sources_v1.json"
CANDIDATS = DOSSIER / "candidats_data_gouv.json"
ETAT = DOSSIER / "etat_collecte.json"
AGENT = "FRONTIERE-moissonnage-metadata/1.0 (catalogue public; contact via dépôt)"
ORIGINE = "https://www.data.gouv.fr/api/1/datasets/"
MAX_OCTETS = 3_000_000
MAX_RESSOURCES = 25
ID = re.compile(r"^[A-Za-z0-9_-]{5,120}$")
LICENCES_LIBRES = {"lov2", "lov1", "odbl", "cc-by", "cc-by-sa", "cc0", "cc-zero"}


class ErreurCollecte(ValueError):
    """Une réponse ou un paramètre ne permet pas une collecte sûre."""


def horodatage() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def lire_json(chemin: Path, defaut: object) -> object:
    if not chemin.is_file():
        return defaut
    return json.loads(chemin.read_text(encoding="utf-8"))


def enregistrer_json(chemin: Path, valeur: object) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(chemin.suffix + ".temp")
    temporaire.write_text(
        json.dumps(valeur, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporaire.replace(chemin)


def url_publique(url: object) -> str | None:
    """N'enregistrer que des adresses HTTP(S) publiques sans identifiants."""
    if not isinstance(url, str) or len(url) > 2048:
        return None
    info = urlparse(url)
    if (info.scheme not in {"http", "https"} or not info.hostname
            or info.username or info.password
            or info.hostname in {"localhost", "127.0.0.1", "::1"}):
        return None
    return url


def url_catalogue(terme: str | None, page: int, taille: int,
                  tri: str | None = None) -> str:
    """Le domaine du téléchargement est fixe, sans redirection définie par une fiche."""
    if not 1 <= page <= 100_000 or not 1 <= taille <= 100:
        raise ErreurCollecte("Pagination hors limites.")
    params: dict[str, str | int] = {"page": page, "page_size": taille}
    if terme is not None:
        if not isinstance(terme, str) or len(terme) > 160 or not terme.strip():
            raise ErreurCollecte("Expression de recherche incorrecte.")
        params["q"] = terme
    if tri is not None:
        if tri not in {"-last_update", "-created"}:
            raise ErreurCollecte("Tri non autorisé.")
        params["sort"] = tri
    return ORIGINE + "?" + urlencode(params)


def telecharger_page(url: str) -> dict:
    if not url.startswith(ORIGINE + "?"):
        raise ErreurCollecte("Adresse distante non autorisée.")
    requete = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": AGENT,
    })
    with urlopen(requete, timeout=25) as reponse:
        if reponse.status != 200:
            raise ErreurCollecte("Réponse HTTP non conforme.")
        if urlparse(reponse.geturl()).hostname != "www.data.gouv.fr":
            raise ErreurCollecte("Redirection hors du domaine officiel.")
        contenu = reponse.read(MAX_OCTETS + 1)
    if len(contenu) > MAX_OCTETS:
        raise ErreurCollecte("Réponse dépassant la limite prévue.")
    data = json.loads(contenu)
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        raise ErreurCollecte("Réponse du catalogue sans liste de jeux.")
    return data


def _texte(x: object, plafond: int = 350) -> str:
    return x.strip()[:plafond] if isinstance(x, str) else ""


def normaliser_fiche(fiche: dict) -> dict | None:
    """Conserver seulement les métadonnées autorisées, sans descriptions nominatives."""
    if not isinstance(fiche, dict) or fiche.get("private") is True:
        return None
    identifiant = fiche.get("id")
    if not isinstance(identifiant, str) or not ID.fullmatch(identifiant):
        return None
    nom = _texte(fiche.get("title"), 240)
    if not nom:
        return None
    lic = _texte(fiche.get("license"), 90)
    org = fiche.get("organization") or {}
    if not isinstance(org, dict):
        org = {}
    ressources = []
    vus = set()
    for res in fiche.get("resources") or []:
        if not isinstance(res, dict):
            continue
        uid = _texte(res.get("id"), 120)
        if not uid or uid in vus or not ID.fullmatch(uid):
            continue
        vus.add(uid)
        ressources.append({
            "id": uid,
            "titre": _texte(res.get("title"), 200),
            "format": _texte(res.get("format"), 40).lower(),
            "url": url_publique(res.get("url")),
            "modifie_le": _texte(res.get("last_modified"), 50) or None,
        })
        if len(ressources) >= MAX_RESSOURCES:
            break
    # Seuls des pointeurs vers les fichiers sont conservés ; le téléchargement
    # des fichiers doit obéir à des règles de licence et de données distinctes.
    return {
        "id": identifiant,
        "titre": nom,
        "producteur": _texte(org.get("name"), 180),
        "licence_declaree": lic or "non_precisee",
        "reutilisation_potentielle": lic.casefold() in LICENCES_LIBRES,
        "page": url_publique(fiche.get("page"))
                or "https://www.data.gouv.fr/datasets/" + identifiant + "/",
        "modifie_le": _texte(fiche.get("last_modified"), 50) or None,
        "donnees_actualisees_le": _texte(fiche.get("last_update"), 50) or None,
        "frequence_declaree": _texte(fiche.get("frequency"), 60) or None,
        "ressources": ressources,
        "nombre_ressources_rapportees": len(fiche.get("resources") or []),
        "contenu_original_copie": False,
        "examen_licence_et_vie_privee_a_faire": True,
    }


def cle_fiche(fiche: dict) -> str:
    return fiche["id"]


def indexer_existants(sources: dict) -> tuple[set[str], set[str]]:
    ids = set()
    pages = set()
    for src in sources.get("sources", []):
        if not isinstance(src, dict):
            continue
        for key in ("metadata_url", "page_url"):
            url = src.get(key)
            if isinstance(url, str):
                pages.add(url.rstrip("/").lower())
                if "/datasets/" in url:
                    ids.add(url.rstrip("/").split("/datasets/")[-1].split("/")[0].lower())
    return ids, pages


def rapprocher(fiche: dict, sources: tuple[set[str], set[str]]) -> bool:
    ids, pages = sources
    return (fiche["id"].lower() in ids
            or fiche["page"].rstrip("/").lower() in pages
            or fiche["page"].rstrip("/").split("/datasets/")[-1].lower() in ids)


def inserer(resultats: dict[str, dict], donnees: dict, mot: str,
            sources: tuple[set[str], set[str]], limite: int) -> int:
    if not isinstance(donnees, dict) or not isinstance(donnees.get("data"), list):
        raise ErreurCollecte("Enveloppe du catalogue invalide.")
    nouveaux = 0
    for brut in donnees["data"]:
        item = normaliser_fiche(brut)
        if item is None:
            continue
        identifiant = cle_fiche(item)
        ancien = resultats.get(identifiant)
        termes = set(ancien.get("recherches", [])) if ancien else set()
        termes.add(mot)
        item["recherches"] = sorted(termes)
        item["source_deja_suivie"] = rapprocher(item, sources)
        if ancien:
            resultats[identifiant] = item
        elif len(resultats) < limite:
            resultats[identifiant] = item
            nouveaux += 1
    return nouveaux


def verifier_config(configuration: dict) -> None:
    if not isinstance(configuration, dict) or configuration.get("source") != ORIGINE:
        raise ErreurCollecte("Origine du catalogue incorrecte.")
    termes = configuration.get("recherches")
    if not isinstance(termes, list) or not 1 <= len(termes) <= 80:
        raise ErreurCollecte("Nombre de recherches hors limites.")
    if len(set(termes)) != len(termes):
        raise ErreurCollecte("Expressions de recherche répétées.")
    for term in termes:
        if not isinstance(term, str) or not 1 <= len(term.strip()) <= 160:
            raise ErreurCollecte("Expression de recherche invalide.")
    for key, low, high in (
        ("taille_page", 1, 100),
        ("nombre_pages_par_recherche", 1, 5),
        ("limite_fiches_enregistrees", 100, 100_000),
    ):
        n = configuration.get(key)
        if type(n) is not int or not low <= n <= high:
            raise ErreurCollecte(f"Paramètre {key} hors limites.")
    extra = configuration.get("recherches_transversales", [])
    if not isinstance(extra, list) or len(extra) > 5:
        raise ErreurCollecte("Recherches transversales incorrectes.")
    for regle in extra:
        if (not isinstance(regle, dict) or regle.get("q") is not None
                or regle.get("sort") != "-last_update"
                or type(regle.get("page_size")) is not int
                or not 1 <= regle["page_size"] <= 100
                or type(regle.get("pages")) is not int
                or not 1 <= regle["pages"] <= 5):
            raise ErreurCollecte("Recherche transversale invalide.")


def executer(configuration: dict, anciennes: dict, sources: dict,
             telecharger=telecharger_page, pause=lambda s: time.sleep(s),
             instant: str | None = None) -> tuple[dict, dict]:
    verifier_config(configuration)
    enregistrees = anciennes.get("candidats", [])
    if not isinstance(enregistrees, list):
        raise ErreurCollecte("Candidats antérieurs non structurés.")
    # Les sorties historiques ne sont jamais supprimées sur une erreur distante.
    resultat = {item["id"]: item for item in enregistrees if (
        isinstance(item, dict) and isinstance(item.get("id"), str)
    )}
    ensemble_sources = indexer_existants(sources)
    succes, erreurs, nouveaux, examines = 0, [], 0, 0
    cas = [(mot, p, configuration["taille_page"], None)
           for mot in configuration["recherches"]
           for p in range(1, configuration["nombre_pages_par_recherche"] + 1)]
    cas.extend(
        ("actualisations recentes", p, x["page_size"], x["sort"])
        for x in configuration.get("recherches_transversales", [])
        for p in range(1, x["pages"] + 1)
    )
    for mot, p, taille, tri in cas:
        url = url_catalogue(None if tri else mot, p, taille, tri)
        try:
            donnees = telecharger(url)
            if not isinstance(donnees, dict) or not isinstance(donnees.get("data"), list):
                raise ErreurCollecte("Réponse invalide.")
            examines += len(donnees["data"])
            nouveaux += inserer(resultat, donnees, mot, ensemble_sources,
                                configuration["limite_fiches_enregistrees"])
            succes += 1
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as err:
            erreurs.append({"expression": mot, "page": p,
                            "motif": type(err).__name__})
        pause(configuration.get("secondes_entre_appels", 0))
    horodatage_observation = instant or horodatage()
    candidats = sorted(resultat.values(), key=lambda x: x["id"])
    rapport = {
        "version": "veille-catalogue-v1",
        "controle_le": horodatage_observation,
        "pages_tentees": len(cas),
        "pages_reussies": succes,
        "pages_echouees": len(erreurs),
        "fiches_recues_avec_doublons": examines,
        "nouveaux_identifiants": nouveaux,
        "identifiants_distincts_conserves": len(candidats),
        "sources_deja_suivies_dans_le_resultat": sum(
            x.get("source_deja_suivie", False) for x in candidats),
        "erreurs": erreurs,
        "collecte_complete": len(erreurs) == 0,
        "couverture_exhaustive_du_web": False,
        "fichiers_sources_originaux_telecharges": 0,
    }
    return {"version": "candidats-data-gouv-v1", "candidats": candidats}, rapport


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--configuration", type=Path, default=CONFIG)
    p.add_argument("--registre", type=Path, default=REGISTRE)
    p.add_argument("--candidats", type=Path, default=CANDIDATS)
    p.add_argument("--etat", type=Path, default=ETAT)
    args = p.parse_args()
    try:
        config = lire_json(args.configuration, None)
        sources = lire_json(args.registre, None)
        candidats = lire_json(args.candidats, {"candidats": []})
        if not isinstance(sources, dict) or not isinstance(candidats, dict):
            raise ErreurCollecte("Registre ou index incorrect.")
        donnees, rapport = executer(config, candidats, sources)
        if rapport["pages_reussies"] < 1:
            raise ErreurCollecte("Aucune interrogation réussie : index antérieur préservé.")
        enregistrer_json(args.candidats, donnees)
        enregistrer_json(args.etat, rapport)
        print(json.dumps(rapport, ensure_ascii=False, indent=2))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as err:
        p.exit(1, f"Découverte interrompue : {type(err).__name__} : {err}\n")


if __name__ == "__main__":
    main()
