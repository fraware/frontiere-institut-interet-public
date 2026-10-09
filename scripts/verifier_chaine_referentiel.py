"""Contrôle conservateur des invariants de la chaîne des référentiels publics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

RACINE = Path(__file__).resolve().parents[1]
EMPREINTE = re.compile(r"^[a-f0-9]{64}$")
FICHIERS = {
    "organisation": "institutionnel/statistiques_roae.json",
    "annuaire": "institutionnel/statistiques_annuaire_local.json",
    "territoires": "institutionnel/statistiques_cog.json",
    "resolution_organisation": "institutionnel/resolution_roae_local.json",
    "resolution_territoires": "institutionnel/resolution_annuaire_cog.json",
    "manifest_organisation": "institutionnel/instantanes/roae_manifest.json",
    "manifest_annuaire": "institutionnel/instantanes/annuaire_local_manifest.json",
    "manifest_territoires": "institutionnel/instantanes/cog_manifest.json",
}


def charger(racine: Path = RACINE) -> dict:
    resultat = {}
    for cle, chemin in FICHIERS.items():
        fichier = racine / chemin
        try:
            item = json.loads(fichier.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Fichier de contrôle absent ou incorrect : {chemin}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Fichier de contrôle non structuré : {chemin}")
        resultat[cle] = item
    return resultat


def _exiger(condition: bool, motif: str) -> None:
    if not condition:
        raise ValueError(motif)


def _sha(item: dict, cle: str) -> str:
    valeur = item.get(cle)
    _exiger(isinstance(valeur, str) and EMPREINTE.fullmatch(valeur) is not None,
            f"Empreinte absente ou invalide : {cle}")
    return valeur


def verifier(d: dict) -> dict:
    """Examiner les couvertures sans prétendre valider les contenus scientifiques."""
    roae, ann, cog = (d["organisation"], d["annuaire"], d["territoires"])
    croisee = d["resolution_organisation"]
    territoriale = d["resolution_territoires"]
    m_roae, m_ann, m_cog = (
        d["manifest_organisation"], d["manifest_annuaire"],
        d["manifest_territoires"],
    )
    _exiger(roae.get("source_id") == m_roae.get("source_id") == "dila_roae",
            "Source administrative incohérente.")
    _exiger(ann.get("source_id") == m_ann.get("source_id") == "dila_annuaire_local",
            "Source de l'Annuaire incohérente.")
    _exiger(cog.get("source_id") == m_cog.get("source_id") == "insee_cog",
            "Source territoriale incohérente.")
    _exiger(roae.get("nombre_services_source", 0) >= 5000
            and roae.get("nombre_entites_canoniques") == roae.get("nombre_services_source"),
            "Couverture du référentiel administratif incorrecte.")
    _exiger(
        m_roae.get("nombre_services") == roae.get("nombre_services_source"),
        "Le manifeste administratif diffère du comptage normalisé.",
    )
    _exiger(ann.get("nombre_enregistrements_export_complet", 0) >= 90000
            and ann.get("nombre_services_locaux_source", 0) >= 80000
            and ann.get("nombre_entites_canoniques") == ann.get("nombre_services_locaux_source"),
            "Couverture de l'Annuaire incorrecte.")
    categories = ann.get("categories_export", {})
    _exiger(categories.get("SI") == roae["nombre_entites_canoniques"]
            and sum(categories.get(k, -1) for k in ("SI", "SL", "SIL"))
            == ann["nombre_enregistrements_export_complet"],
            "L'Annuaire ne correspond pas au référentiel administratif.")
    _exiger(m_ann.get("nombre_enregistrements_export_complet")
            == ann["nombre_enregistrements_export_complet"],
            "Le manifeste de l'Annuaire diffère du comptage normalisé.")
    _exiger(croisee.get("restantes_apres_croisement") == 0,
            "Références hiérarchiques administratives non résolues.")
    types = cog.get("types_territoires", {})
    _exiger(30000 <= types.get("COM", 0) <= 40000 and types.get("DEP", 0) >= 100
            and types.get("REG", 0) >= 18 and types.get("CTCD", -1) == 0,
            "Couverture territoriale incohérente.")
    _exiger(cog.get("nombre_territoires", 0) >= 35000
            and cog.get("nombre_relations", 0) > cog.get("nombre_territoires", 0),
            "Graphe territorial incomplet.")
    _exiger(m_cog.get("nombre_territoires") == cog.get("nombre_territoires"),
            "Manifeste territorial incohérent.")
    _exiger(territoriale.get("references_codes_insee", 0) > 80000
            and territoriale.get("taux_resolution", 0) >= 0.95
            and territoriale.get("ambigues") == 0
            and territoriale.get("absentes_sans_trace_historique") == 0
            and territoriale.get("taux_references_expliquees") == 1.0,
            "Raccordement de l'Annuaire aux territoires incomplet.")
    _sha(m_roae, "sha256_zip")
    _sha(m_ann, "sha256_export")
    _sha(m_cog, "sha256_zip")
    _sha(m_ann, "empreinte_dependance_roae")
    _sha(m_cog, "empreinte_dependance_annuaire")
    return {
        "version_schema": "controle-chaine-institutionnelle-v1",
        "coherence_structurelle": True,
        "nombre_organisations_etat": roae["nombre_entites_canoniques"],
        "nombre_services_locaux": ann["nombre_entites_canoniques"],
        "nombre_territoires": cog["nombre_territoires"],
        "nombre_codes_geographiques_inexpliques": territoriale["absentes_sans_trace_historique"],
        "analyse_semantique_independante": False,
        "controle_du_transport_brut": False,
        "publication_effectuee": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--racine", type=Path, default=RACINE)
    args = parser.parse_args()
    try:
        resultat = verifier(charger(args.racine))
    except (ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Chaîne incohérente : {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
