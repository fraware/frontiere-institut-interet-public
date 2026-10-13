"""Prélever progressivement plusieurs fichiers XML PES Marché de la DGFiP.

Les ressources sont choisies exclusivement parmi les 150 métadonnées déjà
inventoriées et recoupées avec la fiche officielle courante. Le curseur
mémorise les versions effectivement traitées, jamais les simples tentatives.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from urllib.error import HTTPError, URLError

if __package__:
    from scripts.collecter_catalogues_decp import telecharger as telecharger_fiche
    from scripts.sonder_ressource_decp_aife import recevoir_fichier, _url_officielle
    from scripts.ingerer_fichier_decp_xml import analyser_fichier, XMLDECPInvalide
else:
    from collecter_catalogues_decp import telecharger as telecharger_fiche
    from sonder_ressource_decp_aife import recevoir_fichier, _url_officielle
    from ingerer_fichier_decp_xml import analyser_fichier, XMLDECPInvalide

RACINE = Path(__file__).resolve().parents[1]
INVENTAIRE = RACINE / "institutionnel/decp/etat_ressources.json"
DESTINATION = RACINE / "institutionnel/decp/lot_dgfip_xml.json"
CATALOGUE_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024/"
)
SOURCE_ID = "dgfip_pes_marche"
TAILLE_MAX = 1_500_000
FICHIERS_PAR_CYCLE = 4
MAX_HISTORIQUE = 2000


class LotDECPInvalide(ValueError):
    """Source, curseur ou fichier incompatible avec la collecte bornée."""


def cle_ressource(resource: dict) -> tuple[str, int, str | None]:
    """Identifier un état déclaré de ressource, sans supposer son immutabilité."""
    return (
        resource["id"],
        resource["taille_octets_declaree"],
        resource.get("modifie_le"),
    )


def choisir_ressources(
    inventaire: dict, fiche: dict, historique: dict,
    *, maximum: int = FICHIERS_PAR_CYCLE,
) -> list[dict]:
    """Sélectionner les premières ressources XML non traitées et corroborées."""
    if type(maximum) is not int or not 1 <= maximum <= FICHIERS_PAR_CYCLE:
        raise LotDECPInvalide("Plafond de cycle incorrect")
    if not isinstance(inventaire, dict) or not isinstance(fiche, dict):
        raise LotDECPInvalide("Métadonnées de catalogue non structurées")
    local = next(
        (c for c in inventaire.get("catalogues", [])
         if isinstance(c, dict) and c.get("source_id") == SOURCE_ID), None
    )
    if local is None or not isinstance(local.get("ressources_recentes"), list):
        raise LotDECPInvalide("Référentiel DGFiP non disponible")
    distantes = fiche.get("resources")
    if not isinstance(distantes, list):
        raise LotDECPInvalide("Liste officielle de ressources absente")
    paires = {}
    for ressource in distantes:
        if isinstance(ressource, dict) and isinstance(ressource.get("id"), str):
            if ressource["id"] in paires:
                raise LotDECPInvalide("Identifiant de ressource répété dans la fiche")
            paires[ressource["id"]] = ressource
    prises = {
        (f["id"], f["taille_octets_declaree"], f.get("modifie_le"))
        for f in historique.get("fichiers", [])
    }
    selections = []
    for connu in local["ressources_recentes"]:
        if not isinstance(connu, dict) or connu.get("format") != "xml":
            continue
        rid = connu.get("id")
        distant = paires.get(rid)
        taille = connu.get("taille_octets_declaree")
        if (
            distant is None
            or str(distant.get("format", "")).lower() != "xml"
            or type(taille) is not int or not 0 < taille <= TAILLE_MAX
            or type(distant.get("filesize")) is not int
            or distant["filesize"] != taille
            or cle_ressource(connu) in prises
        ):
            continue
        url = _url_officielle(distant.get("url"))
        selections.append({
            "id": rid, "url": url, "titre": connu.get("titre"),
            "taille_octets_declaree": taille,
            "modifie_le": connu.get("modifie_le"),
        })
        if len(selections) >= maximum:
            break
    return selections


def executer(
    inventaire: dict, fiche: dict, ancien: dict,
    *, recuperer=recevoir_fichier, maximum: int = FICHIERS_PAR_CYCLE,
    moment: str | None = None,
) -> dict:
    """Indexer les fichiers correctement analysés ; rejeter un cycle sans succès."""
    if not isinstance(ancien, dict) or ancien.get("version") not in (None, "lot-decp-dgfip-xml-v1"):
        raise LotDECPInvalide("Version du curseur incorrecte")
    deja = ancien.get("fichiers", [])
    if not isinstance(deja, list) or len(deja) > MAX_HISTORIQUE or any(
        not isinstance(e, dict) for e in deja
    ):
        raise LotDECPInvalide("Historique de collecte incorrect")
    selections = choisir_ressources(inventaire, fiche, ancien, maximum=maximum)
    if not selections:
        return ancien if ancien else {
            "version": "lot-decp-dgfip-xml-v1", "source_catalogue": SOURCE_ID,
            "fichiers": [], "echecs_du_dernier_cycle": [],
            "aucune_ressource_admissible_nouvelle": True,
        }
    if len(deja) + len(selections) > MAX_HISTORIQUE:
        raise LotDECPInvalide("Plafond historique atteint : stockage externe nécessaire")
    succes, erreurs = [], []
    with tempfile.TemporaryDirectory(prefix="frontiere-dgfip-") as dossier:
        for index, selection in enumerate(selections):
            chemin = Path(dossier) / f"ressource_{index:02d}.xml"
            try:
                octets = recuperer(selection, chemin)
                if octets != selection["taille_octets_declaree"] or chemin.stat().st_size != octets:
                    raise LotDECPInvalide("Taille effective différente de la fiche")
                bilan = analyser_fichier(
                    chemin, source_id=SOURCE_ID,
                    ressource_id=selection["id"], limite_extraits=200,
                )
                succes.append({
                    "id": selection["id"], "titre": selection["titre"],
                    "taille_octets_declaree": octets,
                    "modifie_le": selection["modifie_le"],
                    "empreinte_sha256": bilan["sha256_fichier_brut"],
                    "releves": bilan["releves"],
                    "rejets_par_categorie": bilan["rejets_par_categorie"],
                    "categories_cpv_prefixe_2": bilan["categories_cpv_prefixe_2"],
                    "marches_extraits": bilan["marches_extraits"],
                    "extraits_plafonnes": bilan["extraits_plafonnes"],
                    "schéma_complet_valide": False,
                    "besoin_encore_ouvert_demontre": False,
                })
            except (OSError, ValueError, UnicodeError, HTTPError, URLError) as exc:
                erreurs.append({
                    "id": selection["id"],
                    "type_erreur": (
                        "HTTP_" + str(exc.code)
                        if isinstance(exc, HTTPError) else type(exc).__name__
                    ),
                    # Les erreurs XML internes sont constituées par le programme.
                    # Ne pas exposer la réponse HTTP, les objets de marchés ou
                    # les informations issues de documents arbitraires.
                    "diagnostic": (
                        str(exc)[:150]
                        if isinstance(exc, (XMLDECPInvalide, LotDECPInvalide))
                        else None
                    ),
                })
    if not succes:
        raise LotDECPInvalide(
            "Toutes les ressources XML sélectionnées ont échoué : curseur inchangé. "
            + json.dumps(erreurs[:FICHIERS_PAR_CYCLE], ensure_ascii=False, sort_keys=True)
        )
    instant = moment or datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "version": "lot-decp-dgfip-xml-v1",
        "source_catalogue": SOURCE_ID,
        "page_catalogue": (
            "https://www.data.gouv.fr/datasets/"
            "donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024"
        ),
        "controle_le": instant,
        "fichiers": deja + succes,
        "nombre_fichiers_du_cycle": len(succes),
        "echecs_du_dernier_cycle": erreurs,
        "nombre_fichiers_historises": len(deja) + len(succes),
        "couverture_complete_des_ressources_dgfip": False,
        "liens_boamp_verifies": 0,
        "besoins_encore_ouverts_prouves": 0,
    }


def main() -> None:
    """Mettre à jour atomiquement le registre de fichiers XML réellement lus."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventaire", type=Path, default=INVENTAIRE)
    p.add_argument("--sortie", type=Path, default=DESTINATION)
    args = p.parse_args()
    try:
        inventaire = json.loads(args.inventaire.read_text(encoding="utf-8"))
        fiche = telecharger_fiche({"url": CATALOGUE_URL})
        ancien = json.loads(args.sortie.read_text(encoding="utf-8")) if args.sortie.is_file() else {}
        nouveau = executer(inventaire, fiche, ancien)
        if ancien == nouveau:
            print(json.dumps({"statut": "aucune_nouvelle_ressource_traitee"}))
            return
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.sortie.with_name(args.sortie.name + ".tmp")
        tmp.write_text(json.dumps(nouveau, ensure_ascii=False, indent=2,
                                  sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        tmp.replace(args.sortie)
        print(json.dumps({
            k: v for k, v in nouveau.items() if k != "fichiers"
        }, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, UnicodeError, HTTPError, URLError) as exc:
        p.exit(1, f"Lot DGFiP refusé : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
