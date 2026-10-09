"""Archiver les petits CSV quotidiens BeauAMP avec leurs octets et leur attribution.

Les données sont enrichies par leur auteur et comportent des estimations.
Ne jamais les assimiler aux avis officiels originaux du BOAMP.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DOSSIER = Path(__file__).resolve().parents[1] / "institutionnel" / "marches_attribues"
API = ("https://www.data.gouv.fr/api/1/datasets/"
       "base-etendue-amelioree-et-unifiee-des-annonces-des-marches-publics/")
PAGE_SOURCE = "https://www.data.gouv.fr/datasets/base-etendue-amelioree-et-unifiee-des-annonces-des-marches-publics"
REGEX = re.compile(r"^beauamp-(\d{2})-(\d{2})-(20\d{2})\.csv$", re.IGNORECASE)
MAX_REPONSE = 2_000_000
MAX_CSV = 1_500_000
MAX_RAPPORT = 60
LICENCES = {"cc-by-sa", "cc-by-sa-4.0", "cc-by-sa-3.0", "cc-by-sa-2.0"}
AUTEUR = "Adrien Deschamps"


class RefusFichier(ValueError):
    """Publication incomplète ou source extérieure aux contraintes déclarées."""


def lire_source(obtenir=None) -> dict:
    if obtenir is not None:
        source = obtenir()
    else:
        with urlopen(Request(API, headers={
            "Accept": "application/json",
            "User-Agent": "FRONTIERE-beauamp/1.0",
        }), timeout=40) as reponse:
            if reponse.status != 200:
                raise RefusFichier("Réponse HTTP inattendue pour le catalogue.")
            if reponse.geturl() != API:
                raise RefusFichier("Redirection du catalogue non prévue.")
            octets = reponse.read(MAX_REPONSE + 1)
            if len(octets) > MAX_REPONSE:
                raise RefusFichier("Catalogue trop volumineux.")
            source = json.loads(octets)
    if not isinstance(source, dict) or not isinstance(source.get("resources"), list):
        raise RefusFichier("Ressources officielles indisponibles.")
    return source


def selectionner(ressources: list[dict], instant: date | None = None,
               jours_archives: set[str] | None = None) -> list[dict]:
    """Conserver la veille récente et compléter progressivement les jours anciens.

    Le paramètre jours_archives active le rattrapage historique et doit être
    établi par vérification réelle des fichiers et empreintes déjà conservés.
    L'appel sans ce paramètre conserve le comportement historique de sélection
    limitée aux 31 derniers jours.
    """
    aujourd_hui = instant or datetime.now(timezone.utc).date()
    recentes, anterieures = [], []
    for brut in ressources:
        if not isinstance(brut, dict):
            continue
        titre = brut.get("title")
        r = REGEX.fullmatch(titre) if isinstance(titre, str) else None
        if r is None:
            continue
        try:
            jour = date(int(r[3]), int(r[2]), int(r[1]))
        except ValueError:
            continue
        ecart = (aujourd_hui - jour).days
        if ecart < 0:
            continue
        taille = brut.get("filesize")
        if type(taille) is not int or not 1 <= taille <= MAX_CSV:
            continue
        url = brut.get("url")
        p = urlparse(url) if isinstance(url, str) else None
        if (p is None or p.scheme != "https" or p.hostname != "static.data.gouv.fr"
                or p.username or p.password or p.query or p.fragment
                or not p.path.startswith("/resources/")):
            continue
        uid = brut.get("id")
        if not isinstance(uid, str) or not re.fullmatch(r"[0-9a-f-]{36}", uid):
            continue
        fiche = {
            "id": uid,
            "titre": titre,
            "jour": jour.isoformat(),
            "octets_declares": taille,
            "url": url,
            "modifie_le": brut.get("last_modified"),
        }
        if ecart <= 31:
            recentes.append(fiche)
        elif jours_archives is not None and fiche["jour"] not in jours_archives:
            anterieures.append(fiche)
    ordre = lambda x: (x["jour"], x["id"])
    recentes = sorted(recentes, key=ordre, reverse=True)[:MAX_RAPPORT]
    anterieures = sorted(anterieures, key=ordre, reverse=True)
    # Donner la priorité à la veille et remplir le reste du lot avec les
    # journées historiquement absentes, sans multiplier les téléchargements.
    return recentes + anterieures[:MAX_RAPPORT - len(recentes)]


def telecharger_fichier(fiche: dict, obtenir=None) -> bytes:
    if obtenir is None:
        with urlopen(Request(fiche["url"], headers={
            "Accept-Encoding": "identity",
            "User-Agent": "FRONTIERE-beauamp/1.0",
        }), timeout=40) as reponse:
            if reponse.status != 200 or reponse.geturl() != fiche["url"]:
                raise RefusFichier("Réponse ou redirection inattendue.")
            brut = reponse.read(MAX_CSV + 1)
    else:
        brut = obtenir(fiche)
    if not isinstance(brut, bytes) or not 0 < len(brut) <= MAX_CSV:
        raise RefusFichier("Fichier quotidien trop volumineux ou vide.")
    if len(brut) != fiche["octets_declares"]:
        raise RefusFichier("Taille du fichier différente des métadonnées officielles.")
    if b"\x00" in brut[:1024] or b"\n" not in brut[:MAX_CSV]:
        raise RefusFichier("Le fichier ne ressemble pas à un CSV textuel.")
    return brut


def collecter(base: Path = DOSSIER, obtenir_source=None, obtenir_fichier=None,
             instant: date | None = None) -> dict:
    catalogue = lire_source(obtenir_source)
    licence = catalogue.get("license", "")
    if isinstance(licence, dict):
        licence = licence.get("id", "")
    code = str(licence or "").strip().casefold()
    erreurs = []
    preuves = []
    fichiers = base / "quotidiens"
    if code not in LICENCES:
        raise RefusFichier(
            "Licence de la source non reconnue pour republier les octets du CSV."
        )
    # L'inventaire antérieur est conservé uniquement si ses octets correspondent
    # à l'empreinte déclarée. Le catalogue récent n'efface pas l'historique.
    manifest_ancien = base / "manifest.json"
    ancien = json.loads(manifest_ancien.read_text(encoding="utf-8")) if manifest_ancien.is_file() else {}
    deja_archives = {}
    for notice in ancien.get("fichiers", []):
        if not isinstance(notice, dict):
            raise RefusFichier("Ancien manifeste mal formé.")
        jour, empreinte = notice.get("jour"), notice.get("sha256")
        if not isinstance(jour, str) or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", jour):
            raise RefusFichier("Date de fichier antérieur incohérente.")
        if not isinstance(empreinte, str) or not re.fullmatch(r"[a-f0-9]{64}", empreinte):
            raise RefusFichier("Empreinte historique absente.")
        ancien_fichier = fichiers / (jour + ".csv")
        if not ancien_fichier.is_file():
            raise RefusFichier("Fichier historique mentionné dans le manifeste absent.")
        if hashlib.sha256(ancien_fichier.read_bytes()).hexdigest() != empreinte:
            raise RefusFichier("Empreinte historique différente du manifeste.")
        if jour in deja_archives:
            raise RefusFichier("Date historique répétée dans le manifeste.")
        deja_archives[jour] = notice
    ressources = selectionner(catalogue["resources"], instant=instant,
                             jours_archives=set(deja_archives))
    fichiers.mkdir(parents=True, exist_ok=True)
    for fiche in ressources:
        cible = fichiers / (fiche["jour"] + ".csv")
        try:
            brut = telecharger_fichier(fiche, obtenir_fichier)
            empreinte = hashlib.sha256(brut).hexdigest()
            if not cible.is_file() or hashlib.sha256(cible.read_bytes()).hexdigest() != empreinte:
                temporaire = cible.with_suffix(".csv.tmp")
                temporaire.write_bytes(brut)
                temporaire.replace(cible)
            preuves.append({**fiche, "sha256": empreinte, "octets_archives": len(brut),
                            "chemin": "quotidiens/" + cible.name})
        except (OSError, TimeoutError, ValueError) as err:
            erreurs.append({"jour": fiche["jour"], "motif": type(err).__name__})
    if not preuves and erreurs:
        raise RefusFichier("Aucun fichier quotidien récupéré : archives préservées.")
    for preuve in preuves:
        deja_archives[preuve["jour"]] = preuve
    manifest = {
        "version": "beauamp-quotidiens-v1",
        "source": PAGE_SOURCE,
        "producteur": AUTEUR,
        "licence": code,
        "mention": "Données dérivées, estimations et rapprochements à confirmer auprès du BOAMP.",
        "fichiers": sorted(deja_archives.values(), key=lambda f: f["jour"]),
        "fichiers_en_echec": erreurs,
        "nombre_fichiers": len(deja_archives),
        "nombre_jours_anterieurs_conserves": sum(
            (instant or datetime.now(timezone.utc).date()) - date.fromisoformat(x) > timedelta(days=31)
            for x in deja_archives
        ),
        "completude_historique": False,
    }
    etat = {
        "controle_le": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "fichiers_telecharges_et_verifies": len(preuves),
        "fichiers_echoues": len(erreurs),
        "couverture_integrale_de_tous_les_marches": False,
    }
    for nom, objet in (("manifest.json", manifest), ("etat.json", etat)):
        chemin = base / nom
        temporaire = chemin.with_suffix(".json.tmp")
        temporaire.write_text(json.dumps(objet, indent=2, ensure_ascii=False,
                                        sort_keys=True) + "\n", encoding="utf-8")
        temporaire.replace(chemin)
    return etat


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, default=DOSSIER)
    args = p.parse_args()
    try:
        etat = collecter(args.sortie)
        print(json.dumps(etat, ensure_ascii=False))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as err:
        p.exit(1, f"Archive BeauAMP non actualisée : {type(err).__name__}: {err}\n")


if __name__ == "__main__":
    main()
