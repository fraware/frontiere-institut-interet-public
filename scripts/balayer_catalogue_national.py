"""Balayer progressivement tout le catalogue data.gouv.fr, par pages versionnées.

Chaque exécution traite un lot borné de pages. Les pages antérieures restent
dans le dépôt et sont revisitées au cycle suivant, sans collecte de fichiers
bruts ni conservation de descriptions libres ou d'informations nominatives.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

if __package__:
    from scripts.decouvrir_sources_publiques import (
        DOSSIER, ErreurCollecte, enregistrer_json, horodatage,
        lire_json, telecharger_page, url_catalogue, _texte, ID,
    )
else:
    from decouvrir_sources_publiques import (
        DOSSIER, ErreurCollecte, enregistrer_json, horodatage,
        lire_json, telecharger_page, url_catalogue, _texte,
    )

CONFIG = DOSSIER / "balayage_config_v1.json"
ETAT = DOSSIER / "balayage_etat.json"
PAGES = DOSSIER / "balayage_pages"


def verifier_configuration(config: dict) -> None:
    if not isinstance(config, dict) or config.get("origine") != "https://www.data.gouv.fr/api/1/datasets/":
        raise ErreurCollecte("Origine nationale du catalogue incorrecte.")
    if config.get("tri") != "title" or config.get("conserver_uniquement_metadonnees") is not True:
        raise ErreurCollecte("Tri ou contenu du balayage non autorisé.")
    for k, minimum, maximum in (
        ("taille_page", 10, 100),
        ("pages_par_execution", 1, 80),
        ("nombre_max_pages", 100, 5000),
    ):
        value = config.get(k)
        if type(value) is not int or not minimum <= value <= maximum:
            raise ErreurCollecte(f"Limite {k} incorrecte.")


def reduire_notice(brut: object) -> dict | None:
    """Conserver la notice minimale, avec lien officiel, sans ressources brutes."""
    if not isinstance(brut, dict) or brut.get("private") is True:
        return None
    uid = brut.get("id")
    if not isinstance(uid, str) or not ID.fullmatch(uid):
        return None
    title = _texte(brut.get("title"), 240)
    if not title:
        return None
    producteur = brut.get("organization") or {}
    if not isinstance(producteur, dict):
        producteur = {}
    return {
        "id": uid,
        "titre": title,
        "producteur": _texte(producteur.get("name"), 150),
        "licence": _texte(brut.get("license"), 70) or "non_precisee",
        "actualise_le": _texte(brut.get("last_update"), 45) or None,
        "page": "https://www.data.gouv.fr/datasets/" + uid + "/",
        "nombre_ressources": len(brut.get("resources") or []),
    }


def preparer_lot(config: dict, etat: dict, charge=telecharger_page,
                 patienter=time.sleep) -> tuple[list[tuple[int, list[dict]]], dict]:
    verifier_configuration(config)
    if not isinstance(etat, dict):
        raise ErreurCollecte("État antérieur illisible.")
    curseur = etat.get("page_suivante", 1)
    if type(curseur) is not int or not 1 <= curseur <= config["nombre_max_pages"]:
        raise ErreurCollecte("Page de reprise hors limites.")
    tours = etat.get("cycles_acheves", 0)
    if type(tours) is not int or tours < 0:
        raise ErreurCollecte("Compteur de cycles incorrect.")
    lot: list[tuple[int, list[dict]]] = []
    erreurs = []
    termine = False
    total_declare = None
    for _ in range(config["pages_par_execution"]):
        page = curseur
        url = url_catalogue(None, page, config["taille_page"], "title")
        try:
            enveloppe = charge(url)
            if not isinstance(enveloppe, dict) or not isinstance(enveloppe.get("data"), list):
                raise ErreurCollecte("Réponse incorrecte.")
            donnees = enveloppe["data"]
            maximum = enveloppe.get("total")
            if type(maximum) is int and maximum >= 0:
                total_declare = maximum
            notices = [item for brut in donnees if (item := reduire_notice(brut)) is not None]
            lot.append((page, sorted(notices, key=lambda x: x["id"])))
            if len(donnees) < config["taille_page"]:
                curseur = 1
                tours += 1
                termine = True
                break
            curseur += 1
            if curseur > config["nombre_max_pages"]:
                # Refuser de déclarer la couverture complète si la limite
                # de pagination a été atteinte avant la fin du catalogue.
                curseur = config["nombre_max_pages"]
                erreurs.append({"page": page, "motif": "limite_de_pagination"})
                break
        except (OSError, TimeoutError, ValueError) as e:
            erreurs.append({"page": page, "motif": type(e).__name__})
            break
        finally:
            patienter(config.get("secondes_entre_appels", 0))
    if not lot:
        raise ErreurCollecte("Aucune page valide : le balayage antérieur est préservé.")
    statistiques = {
        "version": "balayage-national-v1",
        "controle_le": horodatage(),
        "page_suivante": curseur,
        "cycles_acheves": tours,
        "pages_examinees_cette_execution": len(lot),
        "notices_relevees_cette_execution": sum(len(x) for _, x in lot),
        "derniere_page_traitee": lot[-1][0],
        "nombre_total_jeux_declare_par_catalogue": total_declare,
        "derniere_execution_est_un_tour_complet": termine,
        "erreurs": erreurs,
        "exhaustivite_du_web": False,
        "fichiers_bruts_copies": 0,
    }
    return lot, statistiques


def publier_lot(lot: list[tuple[int, list[dict]]], etat: dict, dossier: Path) -> None:
    """Ne remplacer que les pages entièrement téléchargées, sans supprimer les autres."""
    repertoire = dossier / "balayage_pages"
    repertoire.mkdir(parents=True, exist_ok=True)
    for page, notices in lot:
        fichier = repertoire / f"page_{page:05d}.jsonl"
        temporaire = fichier.with_suffix(".jsonl.temp")
        contenu = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True)
                          + "\n" for x in notices)
        temporaire.write_text(contenu, encoding="utf-8")
        temporaire.replace(fichier)
    enregistrer_json(dossier / "balayage_etat.json", etat)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", type=Path, default=CONFIG)
    parser.add_argument("--etat", type=Path, default=ETAT)
    parser.add_argument("--dossier", type=Path, default=DOSSIER)
    args = parser.parse_args()
    try:
        config = lire_json(args.configuration, None)
        etat = lire_json(args.etat, {"page_suivante": 1, "cycles_acheves": 0})
        lot, bilan = preparer_lot(config, etat)
        publier_lot(lot, bilan, args.dossier)
        print(json.dumps(bilan, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
        parser.exit(1, f"Balayage interrompu : {type(e).__name__}: {e}\n")


if __name__ == "__main__":
    main()
