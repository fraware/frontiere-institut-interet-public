"""Contrôler les bilans SQLite contre les manifestes de la révision courante.

Les collectes automatiques modifient les populations archivées. La CI doit
comparer ses index aux manifestes vérifiés, sans figer les effectifs du jour
de création du test. Les indexeurs contrôlent séparément les octets sources.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


class BilanIncompatible(ValueError):
    """Population indexée incompatible avec les archives versionnées."""


def exiger(condition: bool, message: str) -> None:
    if not condition:
        raise BilanIncompatible(message)


def nombre(objet: dict, cle: str) -> int:
    valeur = objet.get(cle)
    exiger(type(valeur) is int and valeur >= 0, f"Compteur invalide : {cle}")
    return valeur


def verifier_csp(recrutements: dict, manifeste_csp: dict) -> dict:
    """Vérifier les quantités CSP sur le manifeste courant."""
    exiger(isinstance(manifeste_csp, dict)
            and manifeste_csp.get("version") == "emplois-publics-extraits-v1",
            "Manifeste CSP incompatible.")
    exiger(isinstance(recrutements, dict)
            and recrutements.get("version") == "frontiere-index-integral-recrutements-v1",
            "Version d'index CSP incorrecte.")
    attentes = {
        "variantes_indexees": nombre(manifeste_csp, "offres_distinctes"),
        "references_distinctes": nombre(manifeste_csp, "references_distinctes"),
        "references_multivariantes": nombre(manifeste_csp, "references_avec_plusieurs_variantes"),
        "partitions_verifiees": len(manifeste_csp.get("empreintes_partitions", {})),
    }
    exiger(attentes["partitions_verifiees"] == 16
            and attentes["variantes_indexees"] >= attentes["references_distinctes"],
            "Les seize partitions CSP ou la hiérarchie des références sont incorrectes.")
    for cle, attendu in attentes.items():
        exiger(nombre(recrutements, cle) == attendu, f"CSP : divergence de {cle}.")
    exiger(recrutements.get("couverture_nationale_demontree") is False
            and nombre(recrutements, "recrutements_actuels_confirmes") == 0,
            "Conclusions institutionnelles non établies dans l'index CSP.")
    return attentes


def verifier_commande(commande: dict, archive_boamp: dict, bilan_decp: dict) -> dict:
    """Vérifier les unités BOAMP et DECP sans rapprocher leurs marchés."""
    exiger(isinstance(archive_boamp, dict)
            and archive_boamp.get("version") == "avis-boamp-v1"
            and isinstance(archive_boamp.get("annonces"), list),
            "Archive BOAMP incompatible.")
    exiger(isinstance(bilan_decp, dict)
            and bilan_decp.get("version") == "index-unifie-decp-v1",
            "Bilan DECP incompatible.")
    exiger(isinstance(commande, dict)
            and commande.get("version") == "frontiere-commande-publique-integrale-v1",
            "Version d'index BOAMP–DECP incorrecte.")
    attentes = {
        "avis_boamp": len(archive_boamp["annonces"]),
        "marches_identites": nombre(bilan_decp, "identites_distinctes_par_siret_et_id_marche"),
        "marches_variantes": nombre(bilan_decp, "variantes_documentaires_distinctes"),
        "marches_attestations": nombre(bilan_decp, "attestations_documentaires"),
        "fichiers_decp": nombre(bilan_decp, "fichiers_documentaires"),
    }
    exiger(attentes["marches_attestations"] >= attentes["marches_variantes"]
            >= attentes["marches_identites"],
            "Hiérarchie des unités documentaires DECP incorrecte.")
    for cle, attendu in attentes.items():
        exiger(nombre(commande, cle) == attendu, f"Commande : divergence de {cle}.")
    exiger(commande.get("couverture_nationale_demontree") is False
            and nombre(commande, "liaisons_boamp_decp_prouvees") == 0,
            "Conclusions institutionnelles non établies dans l'index commande.")
    return attentes


def comparer(
    recrutements: dict, commande: dict, manifeste_csp: dict,
    archive_boamp: dict, bilan_decp: dict,
) -> dict:
    """Comparer les unités documentaires, sans inférence institutionnelle."""
    return {"version": "frontiere-verification-bilans-index-v1",
            "recrutements": verifier_csp(recrutements, manifeste_csp),
            "commande_publique": verifier_commande(commande, archive_boamp, bilan_decp),
            "couverture_nationale_demontree": False}


def lire_json(chemin: Path) -> dict:
    """Charger un seul document JSON, sans appel réseau."""
    return json.loads(chemin.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    choix = parser.add_mutually_exclusive_group(required=True)
    choix.add_argument("--bilan-csp", type=Path)
    choix.add_argument("--bilan-commande", type=Path)
    parser.add_argument("--racine", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        if args.bilan_csp is not None:
            attendu = verifier_csp(
                lire_json(args.bilan_csp),
                lire_json(args.racine / "institutionnel/besoins_publics/manifest_offres_postes.json"),
            )
            famille = "recrutements"
        else:
            attendu = verifier_commande(
                lire_json(args.bilan_commande),
                lire_json(args.racine / "institutionnel/besoins_publics/annonces_boamp.json"),
                lire_json(args.racine / "institutionnel/decp/bilan_index_unifie.json"),
            )
            famille = "commande_publique"
    except (BilanIncompatible, OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"Vérification des bilans refusée : {exc}\\n")
    print(json.dumps({"version": "frontiere-verification-bilans-index-v1",
                      "famille": famille, "population": attendu,
                      "couverture_nationale_demontree": False},
                     ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
