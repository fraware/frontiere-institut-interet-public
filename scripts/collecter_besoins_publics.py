"""Relever les besoins publics publiés : annonces BOAMP et fichiers d'offres CSP.

Deux sorties indépendantes : seules les métadonnées sélectionnées sont conservées.
Une indisponibilité de l'une des sources n'efface aucune sortie précédente.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

RACINE = Path(__file__).resolve().parents[1]
SORTIES = RACINE / "institutionnel" / "besoins_publics"
BOAMP = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
CSP = "https://www.data.gouv.fr/api/1/datasets/les-offres-diffusees-sur-choisir-le-service-public/"
BOAMP_NOM = SORTIES / "annonces_boamp.json"
BOAMP_ETAT = SORTIES / "etat_boamp.json"
CSP_NOM = SORTIES / "ressources_emplois_publics.json"
CSP_ETAT = SORTIES / "etat_emplois_publics.json"
PLAFOND_REPONSE = 3_000_000
PLAFOND_NOTICES = 30_000
CHAMPS_BOAMP = ("idweb", "objet", "nomacheteur", "dateparution",
                "datelimitereponse", "type_marche", "etat", "url_avis")
FORMAT_AUTORISE = {"csv", "json", "parquet", "xlsx", "zip"}
IDENTIFIANT = re.compile(r"^[\w.-]{1,150}$", re.UNICODE)


class EchecBesoins(ValueError):
    """La réponse ne permet pas de publier des données vérifiées."""


class SansRedirection(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EchecBesoins("Redirection interdite pour cette source.")


def texte(obj: object, maximum: int = 220) -> str:
    return obj.strip()[:maximum] if isinstance(obj, str) else ""


def url_publique(obj: object) -> str | None:
    if not isinstance(obj, str) or len(obj) > 2048:
        return None
    p = urlparse(obj)
    if (p.scheme not in ("http", "https") or not p.hostname or p.username or p.password
            or p.hostname in ("localhost", "127.0.0.1", "::1")):
        return None
    return obj


def recevoir(url: str, origine: str) -> dict:
    if not url.startswith(origine):
        raise EchecBesoins("Origine non autorisée.")
    if origine == CSP and url != CSP:
        raise EchecBesoins("L'adresse de l'emploi public doit être exacte.")
    request = Request(url, headers={
        "User-Agent": "FRONTIERE-veille-besoins-publics/1.0",
        "Accept": "application/json",
    })
    with build_opener(SansRedirection).open(request, timeout=35) as response:
        if response.status != 200:
            raise EchecBesoins("Statut HTTP non conforme.")
        payload = response.read(PLAFOND_REPONSE + 1)
    if len(payload) > PLAFOND_REPONSE:
        raise EchecBesoins("Réponse trop volumineuse.")
    result = json.loads(payload)
    if not isinstance(result, dict):
        raise EchecBesoins("Document officiel mal formé.")
    return result


def adresse_boamp(debut: str, page: int, taille: int) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", debut):
        raise EchecBesoins("Date de recherche incorrecte.")
    if not 0 <= page <= 30 or not 1 <= taille <= 100:
        raise EchecBesoins("Pagination hors limites.")
    return BOAMP + "?" + urlencode({
        "where": f'dateparution >= "{debut}"',
        "order_by": "dateparution desc",
        "select": ",".join(CHAMPS_BOAMP),
        "limit": taille,
        "offset": page * taille,
    })


def notice_boamp(enregistrement: object) -> dict | None:
    if not isinstance(enregistrement, dict):
        return None
    identifiant = enregistrement.get("idweb")
    if isinstance(identifiant, int):
        identifiant = str(identifiant)
    if not isinstance(identifiant, str) or not IDENTIFIANT.fullmatch(identifiant):
        return None
    return {
        "id": identifiant,
        "objet": texte(enregistrement.get("objet"), 450),
        "acheteur": texte(enregistrement.get("nomacheteur"), 200),
        "date_parution": texte(enregistrement.get("dateparution"), 32) or None,
        "date_limite_reponse": texte(enregistrement.get("datelimitereponse"), 32) or None,
        "categorie_marche": texte(enregistrement.get("type_marche"), 80) or None,
        "etat_avis": texte(enregistrement.get("etat"), 60) or None,
        "avis": url_publique(enregistrement.get("url_avis")),
        "catalogue_source": "https://boamp-datadila.opendatasoft.com/explore/dataset/boamp/",
        "contenu_integral_copie": False,
    }


def relever_boamp(ancien: dict, obtenir=recevoir, maintenant=None,
                  pages: int = 12, taille: int = 100, attendre=time.sleep) -> tuple[dict, dict]:
    if not isinstance(ancien, dict) or not isinstance(ancien.get("annonces", []), list):
        raise EchecBesoins("Index antérieur incorrect.")
    if not 1 <= pages <= 30 or not 1 <= taille <= 100:
        raise EchecBesoins("Plafond de consultation incorrect.")
    instant = maintenant or datetime.now(timezone.utc)
    debut = (instant.date() - timedelta(days=7)).isoformat()
    archive = {x["id"]: x for x in ancien.get("annonces", [])
               if isinstance(x, dict) and isinstance(x.get("id"), str)}
    erreurs, ajoutes, lus, valides, pages_reussies = [], 0, 0, 0, 0
    total = None
    for page in range(pages):
        try:
            reponse = obtenir(adresse_boamp(debut, page, taille), BOAMP)
            donnees = reponse.get("results")
            if not isinstance(donnees, list):
                raise EchecBesoins("Liste d'annonces officielle absente.")
            if type(reponse.get("total_count")) is int:
                total = reponse["total_count"]
            lus += len(donnees)
            for brut in donnees:
                val = notice_boamp(brut)
                if val is None:
                    continue
                valides += 1
                if val["id"] not in archive:
                    ajoutes += 1
                archive[val["id"]] = val
            if len(archive) > PLAFOND_NOTICES:
                raise EchecBesoins("Plafond du dépôt atteint : besoin d'une nouvelle partition.")
            pages_reussies += 1
            if len(donnees) < taille or (total is not None and (page + 1) * taille >= total):
                break
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            erreurs.append({"page": page + 1,
                            "motif": f"HTTP_{exc.code}" if isinstance(exc, HTTPError)
                            else type(exc).__name__})
            break
        finally:
            attendre(0.2)
    if not pages_reussies:
        raise EchecBesoins("Aucune page BOAMP reçue : conserver l'index précédent.")
    horloge = instant.replace(microsecond=0).isoformat()
    rapport = {
        "source": "BOAMP",
        "controle_le": horloge,
        "periode_recherche_commence_le": debut,
        "pages_reussies": pages_reussies,
        "pages_echouees": len(erreurs),
        "enregistrements_lus": lus,
        "enregistrements_valides": valides,
        "nouveaux_identifiants": ajoutes,
        "annonces_distinctes_conservees": len(archive),
        "total_annonces_recherche_declare": total,
        "recherche_partielle": bool(erreurs or
            (total is not None and pages_reussies * taille < total)),
        "erreurs": erreurs,
        "donnees_nominatives_de_contact_copiees": False,
        "couverture_exhaustive_du_boamp": False,
    }
    return {"version": "avis-boamp-v1",
            "annonces": sorted(archive.values(), key=lambda a: a["id"])}, rapport


def notice_ressource_csp(ressource: object) -> dict | None:
    if not isinstance(ressource, dict):
        return None
    uid = ressource.get("id")
    if not isinstance(uid, str) or not IDENTIFIANT.fullmatch(uid):
        return None
    return {
        "id": uid,
        "titre": texte(ressource.get("title"), 210),
        "format": texte(ressource.get("format"), 30).lower(),
        "url": url_publique(ressource.get("url")),
        "taille_octets_declaree": ressource.get("filesize") if type(ressource.get("filesize")) is int
                                and 0 <= ressource["filesize"] < 2_000_000_000 else None,
        "modifie_le": texte(ressource.get("last_modified"), 60) or None,
        "fichier_integral_copie": False,
    }


def relever_emplois(obtenir=recevoir, maintenant=None) -> tuple[dict, dict]:
    reponse = obtenir(CSP, CSP)
    ressources = reponse.get("resources")
    if not isinstance(ressources, list) or not ressources:
        raise EchecBesoins("Le catalogue des offres publiques ne fournit aucune ressource.")
    notices = [x for r in ressources if (x := notice_ressource_csp(r)) is not None]
    if not notices:
        raise EchecBesoins("Aucune ressource publique identifiable.")
    horloge = (maintenant or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
    return {
        "version": "ressources-emplois-publics-v1",
        "jeu": "Les offres diffusées sur Choisir le Service Public",
        "producteur": "Direction générale de l'administration et de la fonction publique",
        "licence_declaree": texte(reponse.get("license"), 90) or "non_precisee",
        "ressources": sorted(notices, key=lambda x: x["id"]),
        "fichiers_originaux_telecharges": 0,
    }, {
        "controle_le": horloge,
        "source": CSP,
        "ressources_recensees": len(notices),
        "fichiers_originaux_telecharges": 0,
        "actualisation_des_offres_individuelles_constatee": False,
    }


def enregistrer(path: Path, valeur: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporaire = path.with_suffix(path.suffix + ".temp")
    temporaire.write_text(json.dumps(valeur, ensure_ascii=False, sort_keys=True, indent=2)
                          + "\n", encoding="utf-8")
    temporaire.replace(path)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, default=SORTIES)
    args = p.parse_args()
    heures = datetime.now(timezone.utc)
    succes = 0
    anciens = [
        ("boamp", BOAMP_NOM, BOAMP_ETAT),
        ("emplois", CSP_NOM, CSP_ETAT),
    ]
    for source, fichier, etat in anciens:
        dest, suivi = args.sortie / fichier.name, args.sortie / etat.name
        try:
            if source == "boamp":
                old = json.loads(dest.read_text(encoding="utf-8")) if dest.is_file() else {"annonces": []}
                valeurs, rapport = relever_boamp(old, maintenant=heures)
            else:
                valeurs, rapport = relever_emplois(maintenant=heures)
            enregistrer(dest, valeurs)
            enregistrer(suivi, rapport)
            print(json.dumps(rapport, ensure_ascii=False))
            succes += 1
        except (OSError, ValueError, TypeError) as exc:
            print(json.dumps({"source": source, "collecte_reussie": False,
                              "erreur": type(exc).__name__}, ensure_ascii=False))
    if not succes:
        p.exit(1, "Aucune source de besoins publics ne répond correctement.\n")


if __name__ == "__main__":
    main()
