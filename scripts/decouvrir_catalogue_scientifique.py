"""Inventorier le catalogue scientifique du ministère chargé de la recherche.

Les seules données conservées sont les notices des ensembles publiés par
l'interface officielle Explore 2.1. Aucune ligne de données nominatives,
aucune pièce jointe et aucun fichier source ne sont téléchargés.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://mesr.opendatasoft.com/api/explore/v2.1/catalog/datasets"
PAGE = "https://data.enseignementsup-recherche.gouv.fr/explore/dataset/"
ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "institutionnel/decouverte"
SORTIE = DIR / "catalogue_mesr.json"
ETAT = DIR / "catalogue_mesr_etat.json"
IDENTIFIANT = re.compile(r"^[a-zA-Z0-9_-]{3,120}$")
BORNES = (50, 30, 3_000_000)


class EchecCatalogue(ValueError):
    """La collecte ne permet pas de conclure sur cette page."""


class SansRedirection(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EchecCatalogue("Redirection interdite sur l'interface du ministère.")


def _texte(value: object, maxlen: int = 240) -> str:
    return value.strip()[:maxlen] if isinstance(value, str) else ""


def _enregistrer(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = path.with_suffix(path.suffix + ".tmp")
    t.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    t.replace(path)


def _charger(path: Path, vide: object) -> object:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else vide


def url_page(offset: int, limit: int = 50) -> str:
    if type(offset) is not int or type(limit) is not int or offset < 0 or offset > 100000 or not 1 <= limit <= 100:
        raise EchecCatalogue("Pagination hors limites.")
    return BASE + "?" + urlencode({"limit": limit, "offset": offset})


def recevoir(url: str) -> dict:
    if not url.startswith(BASE + "?"):
        raise EchecCatalogue("Origine non autorisée.")
    req = Request(url, headers={"User-Agent": "FRONTIERE-veille-catalogues/1.0", "Accept": "application/json"})
    with build_opener(SansRedirection).open(req, timeout=25) as reponse:
        if reponse.status != 200:
            raise EchecCatalogue("Réponse non valide.")
        brut = reponse.read(3_000_001)
    if len(brut) > 3_000_000:
        raise EchecCatalogue("Réponse trop volumineuse.")
    result = json.loads(brut)
    if not isinstance(result, dict) or not isinstance(result.get("datasets"), list):
        raise EchecCatalogue("L'interface ne fournit plus la liste attendue.")
    return result


def notice(data: object) -> dict | None:
    if not isinstance(data, dict):
        return None
    ds = data.get("dataset", data)
    if not isinstance(ds, dict):
        return None
    uid = ds.get("dataset_id")
    if not isinstance(uid, str) or not IDENTIFIANT.fullmatch(uid):
        return None
    metas = ds.get("metas") or {}
    if not isinstance(metas, dict):
        metas = {}
    metad = metas.get("default") if isinstance(metas.get("default"), dict) else metas
    title = _texte(metad.get("title"), 240) or uid
    licence = _texte(metad.get("license"), 120) or "non_precisee"
    updates = (
        _texte(metad.get("modified"), 60)
        or _texte(metad.get("data_processed"), 60)
        or _texte(ds.get("modified"), 60)
        or None
    )
    return {
        "id": uid,
        "titre": title,
        "licence_declaree": licence,
        "modifie_le": updates,
        "page": PAGE + uid + "/",
        "producteur": "Ministère chargé de l'enseignement supérieur et de la recherche",
        "donnees_brutes_copiees": False,
        "controle_juridique_contenu_non_effectue": True,
    }


def executer(ancien: dict, obtenir=recevoir, attente=time.sleep,
             instant: str | None = None, pages: int = 30, taille: int = 50) -> tuple[dict, dict]:
    if type(pages) is not int or not 1 <= pages <= 40 or type(taille) is not int or not 1 <= taille <= 100:
        raise EchecCatalogue("Limite de pagination.")
    initial = ancien.get("notices", [])
    if not isinstance(initial, list):
        raise EchecCatalogue("Catalogue existant non structuré.")
    conserves = {x["id"]: x for x in initial if isinstance(x, dict) and isinstance(x.get("id"), str)}
    erreurs, succes, nouveaux, parcourus = [], 0, 0, 0
    total = None
    for page in range(pages):
        offset = page * taille
        if offset > 100000:
            break
        try:
            response = obtenir(url_page(offset, taille))
            if not isinstance(response, dict) or not isinstance(response.get("datasets"), list):
                raise EchecCatalogue("Format de réponse invalide.")
            count = response.get("total_count")
            if type(count) is int and count >= 0:
                total = count
            row = response["datasets"]
            parcourus += len(row)
            for item in row:
                norme = notice(item)
                if norme is None:
                    continue
                if norme["id"] not in conserves:
                    nouveaux += 1
                conserves[norme["id"]] = norme
            succes += 1
            if len(row) < taille or (total is not None and offset + taille >= total):
                break
        except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as err:
            raisons = f"HTTP_{err.code}" if isinstance(err, HTTPError) else type(err).__name__
            erreurs.append({"page": page + 1, "motif": raisons})
            break
        finally:
            attente(0.25)
    rapport = {
        "version": "catalogue-mesr-v1",
        "controle_le": instant or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "pages_reussies": succes,
        "pages_echouees": len(erreurs),
        "ressources_catalogue_declarees": total,
        "notices_distinctes_conservees": len(conserves),
        "nouvelles_notices": nouveaux,
        "entrees_lues": parcourus,
        "erreurs": erreurs,
        "exhaustivite_constatee": bool(
            not erreurs and total is not None and parcourus >= total
        ),
        "donnees_brutes_copiees": False,
    }
    return {"version": "catalogue-mesr-v1", "notices": sorted(conserves.values(), key=lambda x: x["id"])}, rapport


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, default=SORTIE)
    p.add_argument("--etat", type=Path, default=ETAT)
    a = p.parse_args()
    try:
        ancien = _charger(a.sortie, {"notices": []})
        if not isinstance(ancien, dict):
            raise EchecCatalogue("Ancien fichier invalide.")
        nouveau, rapport = executer(ancien)
        if rapport["pages_reussies"] == 0:
            raise EchecCatalogue("Aucune page officielle reçue ; conserver le fichier précédent.")
        _enregistrer(a.sortie, nouveau)
        _enregistrer(a.etat, rapport)
        print(json.dumps(rapport, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError) as err:
        p.exit(1, f"Collecte scientifique non effectuée : {type(err).__name__}: {err}\n")


if __name__ == "__main__":
    main()
