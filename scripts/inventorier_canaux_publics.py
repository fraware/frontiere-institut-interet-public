"""Inventorier les éditeurs de jeux publics et les canaux institutionnels référencés.

Lecture locale des pages data.gouv.fr déjà conservées par FRONTIÈRE.
Un libellé d'éditeur constitue une piste d'organisme, non une identité
administrative résolue. Une absence de canal répertorié n'est jamais une
preuve d'absence d'un canal sur le Web.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata

RACINE = Path(__file__).resolve().parents[1]
PAGES = RACINE / "institutionnel/decouverte/balayage_pages"
ETAT_BALAYAGE = RACINE / "institutionnel/decouverte/balayage_etat.json"
FLUX = RACINE / "institutionnel/flux_publics/sources_v1.json"
CONFIG = RACINE / "institutionnel/canaux_publics/configuration_v1.json"
SORTIE = RACINE / "institutionnel/canaux_publics/inventaire_v1.json"
ID_JEU = re.compile(r"^[A-Za-z0-9_-]{5,120}$")
ID_PAGE = re.compile(r"^page_[0-9]{5}\.jsonl$")


class InventaireInvalide(ValueError):
    """Les entrées n'autorisent pas une actualisation reproductible."""


def normaliser(nom: str) -> str:
    """Normalisation minimale, sans fusion de noms institutionnels voisins."""
    if not isinstance(nom, str):
        return ""
    nom = unicodedata.normalize("NFKC", nom).casefold()
    return " ".join(nom.split())


def _texte(objet: object, plafond: int) -> str:
    return objet.strip()[:plafond] if isinstance(objet, str) else ""


def verifier_configuration(config: dict, catalogue_flux: dict) -> None:
    """Interdire les regroupements implicites ou les identifiants inconnus."""
    if not isinstance(config, dict) or config.get("version") != "inventaire-canaux-v1":
        raise InventaireInvalide("Version du répertoire incorrecte")
    limite = config.get("limite_editeurs_detailles")
    if type(limite) is not int or not 50 <= limite <= 3000:
        raise InventaireInvalide("Limite hors bornes")
    flux = catalogue_flux.get("sources") if isinstance(catalogue_flux, dict) else None
    if not isinstance(flux, list):
        raise InventaireInvalide("Catalogue des flux absent")
    ids_flux = {s.get("id") for s in flux if isinstance(s, dict)}
    organismes = config.get("organismes_renseignes")
    if not isinstance(organismes, list) or not organismes:
        raise InventaireInvalide("Références institutionnelles manquantes")
    ids = set()
    alias = {}
    for org in organismes:
        if not isinstance(org, dict) or not _texte(org.get("nom"), 200):
            raise InventaireInvalide("Organisme mal décrit")
        identifiant = org.get("id")
        if not isinstance(identifiant, str) or not re.fullmatch(r"[a-z0-9_-]{2,45}", identifiant):
            raise InventaireInvalide("Identifiant d'organisme mal formé")
        if identifiant in ids:
            raise InventaireInvalide("Organisme dupliqué")
        ids.add(identifiant)
        if not isinstance(org.get("canaux"), list) or not org["canaux"]:
            raise InventaireInvalide("Canaux de référence absents")
        if len(set(org["canaux"])) != len(org["canaux"]):
            raise InventaireInvalide("Canal répété")
        if not set(org["canaux"]) <= ids_flux:
            raise InventaireInvalide("Identifiant de canal non présent dans la collecte")
        if not isinstance(org.get("source_officielle"), str) or not org["source_officielle"].startswith("https://"):
            raise InventaireInvalide("Page officielle manquante")
        noms = org.get("editeurs_data_gouv")
        if not isinstance(noms, list) or not noms:
            raise InventaireInvalide("Producteurs associés manquants")
        for nom in noms:
            cle = normaliser(nom)
            if not cle:
                raise InventaireInvalide("Nom d'éditeur vide")
            if cle in alias and alias[cle] != identifiant:
                raise InventaireInvalide("Un même libellé est attribué à plusieurs organismes")
            alias[cle] = identifiant


def charger_pages(fichiers: list[Path]) -> tuple[dict[str, dict], dict]:
    """Dédupliquer les identifiants de jeux sans faire disparaître les lacunes."""
    if not fichiers:
        raise InventaireInvalide("Aucune page de catalogue")
    ids_pages = set()
    jeux = {}
    lignes_lues = 0
    reprises = 0
    pourcentage_noms_manquants = 0
    for fichier in sorted(fichiers):
        if not ID_PAGE.fullmatch(fichier.name):
            raise InventaireInvalide("Nom de page inattendu")
        numero = int(fichier.stem.split("_")[1])
        if numero in ids_pages:
            raise InventaireInvalide("Page dupliquée")
        ids_pages.add(numero)
        if fichier.stat().st_size > 2_000_000:
            raise InventaireInvalide("Page trop volumineuse")
        with fichier.open("r", encoding="utf-8") as flux:
            for numero_ligne, ligne in enumerate(flux, 1):
                if not ligne.strip():
                    continue
                lignes_lues += 1
                if numero_ligne > 200:
                    raise InventaireInvalide("Plus de 200 entrées sur une page")
                try:
                    data = json.loads(ligne)
                except json.JSONDecodeError as exc:
                    raise InventaireInvalide(f"JSON invalide dans {fichier.name}") from exc
                if not isinstance(data, dict):
                    raise InventaireInvalide("Notice non structurée")
                uid = data.get("id")
                if not isinstance(uid, str) or not ID_JEU.fullmatch(uid):
                    raise InventaireInvalide("Identifiant de jeu incorrect")
                nom = _texte(data.get("producteur"), 220)
                if not nom:
                    pourcentage_noms_manquants += 1
                candidat = {
                    "id": uid, "titre": _texte(data.get("titre"), 240),
                    "editeur_publie": nom,
                    "date_actualisation_declaree": _texte(data.get("actualise_le"), 60) or None,
                    "page": data.get("page"),
                }
                if uid in jeux:
                    reprises += 1
                    # Le même identifiant peut migrer entre pages après une
                    # réindexation. Conserver l'enregistrement le plus récent
                    # seulement si sa date publique est effectivement supérieure.
                    precedent = jeux[uid]
                    if (candidat["date_actualisation_declaree"] or "") > (
                        precedent["date_actualisation_declaree"] or ""
                    ):
                        jeux[uid] = candidat
                else:
                    jeux[uid] = candidat
    manquantes = [
        p for p in range(1, max(ids_pages) + 1) if p not in ids_pages
    ]
    etat = {
        "pages_presentes": len(ids_pages),
        "premiere_page": min(ids_pages),
        "derniere_page": max(ids_pages),
        "lacunes_de_pagination": len(manquantes),
        "numeros_pages_manquantes_exemples": manquantes[:20],
        "lignes_lues": lignes_lues,
        "jeux_distincts": len(jeux),
        "reapparitions_identifiants": reprises,
        "lignes_sans_editeur_declare": pourcentage_noms_manquants,
        "pages_homogenes_temporellement_verifiees": False,
        "couverture_exhaustive_du_catalogue_attestee": False,
    }
    return jeux, etat


def produire(
    config: dict, catalogue_flux: dict, fichiers: list[Path],
    *,
    releve_le: str = "2026-10-13T00:00:00+00:00",
) -> dict:
    """Construire un rapport groupé, borné et transparent sur sa couverture."""
    verifier_configuration(config, catalogue_flux)
    jeux, metriques = charger_pages(fichiers)
    producteurs: dict[str, dict] = {}
    for jeu in jeux.values():
        libelle = jeu["editeur_publie"]
        cle = normaliser(libelle)
        if not cle:
            continue
        groupe = producteurs.setdefault(cle, {
            "editeur_publie": libelle,
            "jeux_declares": 0,
            "jeux_exemples": [],
            "dernier_jeu_actualise_le": None,
        })
        groupe["jeux_declares"] += 1
        if len(groupe["jeux_exemples"]) < 3:
            groupe["jeux_exemples"].append({
                "id": jeu["id"], "titre": jeu["titre"], "page": jeu["page"],
            })
        derniere = groupe["dernier_jeu_actualise_le"] or ""
        prochain = jeu["date_actualisation_declaree"] or ""
        if prochain > derniere:
            groupe["dernier_jeu_actualise_le"] = prochain

    flux_par_id = {s["id"]: s for s in catalogue_flux["sources"]}
    selection = sorted(
        producteurs, key=lambda nom: (-producteurs[nom]["jeux_declares"], nom)
    )[:config["limite_editeurs_detailles"]]
    for org in config["organismes_renseignes"]:
        for alias in org["editeurs_data_gouv"]:
            cle = normaliser(alias)
            if cle in producteurs and cle not in selection:
                selection.append(cle)
    items = []
    identite_par_nom = {}
    for org in config["organismes_renseignes"]:
        for alias in org["editeurs_data_gouv"]:
            identite_par_nom[normaliser(alias)] = org
    for cle in selection:
        p = producteurs[cle]
        org = identite_par_nom.get(cle)
        items.append({
            **p,
            "organisme_associe": org["id"] if org else None,
            "type_rapprochement": "correspondance_de_libelle_configuree" if org else "non_resolu",
            "canaux_documentes": org["canaux"] if org else [],
            "absence_de_canaux_etablie": False,
            "identite_juridique_verifiee": False,
        })
    organismes = [{
        "id": org["id"], "nom": org["nom"],
        "preuve_de_la_liste_des_canaux": org["source_officielle"],
        "canaux": [
            {"id": k, "nom": flux_par_id[k]["nom"],
             "type": flux_par_id[k]["type"],
             "categorie": flux_par_id[k]["categorie"]}
            for k in org["canaux"]
        ],
        "canaux_supplementaires_absents_attestes": False,
    } for org in config["organismes_renseignes"]]
    return {
        "version": "inventaire-canaux-v1",
        "construit_le": releve_le,
        "perimetre": "editeurs_de_jeux_de_donnees_et_canaux_documentes",
        "sources": {"pages_data_gouv": str(PAGES.relative_to(RACINE)),
                    "registre_flux": str(FLUX.relative_to(RACINE))},
        "statistiques": {
            **metriques,
            "editeurs_distincts_libelles": len(producteurs),
            "editeurs_detailles": len(items),
            "editeurs_non_detailles": len(producteurs) - len(items),
            "organismes_a_canaux_documentes": len(organismes),
            "canaux_officiels_documentes": sum(len(o["canaux"]) for o in organismes),
        },
        "organismes_references": organismes,
        "editeurs": items,
        "couverture_tous_les_organismes_publics": False,
    }


def main() -> None:
    """Regrouper les fichiers locaux et produire un inventaire atomique."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--configuration", type=Path, default=CONFIG)
    parser.add_argument("--flux", type=Path, default=FLUX)
    parser.add_argument("--sortie", type=Path, default=SORTIE)
    args = parser.parse_args()
    try:
        result = produire(
            json.loads(args.configuration.read_text(encoding="utf-8")),
            json.loads(args.flux.read_text(encoding="utf-8")),
            list(args.pages.glob("page_*.jsonl")),
            releve_le=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        temporaire = args.sortie.with_suffix(".json.tmp")
        temporaire.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporaire.replace(args.sortie)
        print(json.dumps(result["statistiques"], ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Inventaire refusé : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
