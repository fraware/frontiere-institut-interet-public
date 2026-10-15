"""Publier les seuls recoupements d'acheteurs BOAMP–DECP vérifiables.

Les 17 avis proviennent d'un tirage indépendant et de réponses BOAMP brutes,
déjà contrôlées et liées à 16 recherches administratives archivées.
Le même SIRET déclaré par deux sources n'établit jamais l'identité de contrat.
Aucune requête réseau n'est faite par ce programme.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from scripts.consolider_attributions_decp import rapports_dgfip
from scripts.indexer_attributions_decp_sqlite import verifier_rapport
from scripts.reconstituer_chaines_acheteurs_boamp_decp import produire as reconstituer

VERSION = "correspondances-siret-boamp-decp-17-v1"
SOURCE = "chaines-documentaires-acheteurs-17-avis-v1"
SIRET = re.compile(r"[0-9]{14}")
SHA = re.compile(r"[0-9a-f]{64}")
AVIS = re.compile(r"[0-9]{2}-[0-9]{2,8}")


class CorrespondanceInvalide(ValueError):
    """Des preuves sources ou un décompte ne concordent pas."""


def sha256(path: Path) -> str:
    """Empreinte sur les octets du relevé source publié."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comptes_marches_decp(aife: Path, dgfip: Path) -> dict[str, int]:
    """Compter les identités de marchés distinctes par SIRET déclaré.

    Les notices répétées dans plusieurs fichiers ne créent pas de nouveaux
    marchés. Les entrées restent des identités documentaires, non juridiques.
    """
    rapports = [json.loads(aife.read_text(encoding="utf-8"))]
    rapports.extend(rapports_dgfip(json.loads(dgfip.read_text(encoding="utf-8"))))
    cles = set()
    for rapport in rapports:
        for marche in verifier_rapport(rapport):
            siret, reference = marche["acheteur_siret"], marche["id_marche"]
            if not SIRET.fullmatch(siret) or not reference:
                raise CorrespondanceInvalide("Identité DECP non exploitable.")
            cles.add((siret, reference))
    comptes = Counter(siret for siret, _ in cles)
    return dict(sorted(comptes.items()))


def construire_correspondances(rapport: dict, decompte_decp: dict[str, int],
                               empreintes_decp: dict[str, str]) -> dict:
    """Qualifier les observations sans promotions d'identité non démontrées."""
    if (not isinstance(rapport, dict) or rapport.get("version") != SOURCE
            or rapport.get("mesures", {}).get("avis") != 17
            or rapport.get("nombre_siret_distincts") != 16
            or rapport.get("liaisons_contractuelles_decp_prouvees") != 0
            or rapport.get("validations_juridiques_du_role_acheteur") != 0
            or not all(SHA.fullmatch(rapport.get(champ, "")) for champ in (
                "sha256_audit_boamp", "sha256_rapport_administratif"))
            or not isinstance(rapport.get("dossiers"), list)
            or len(rapport["dossiers"]) != 17):
        raise CorrespondanceInvalide("Chaînes BOAMP non établies ou incohérentes.")
    if (set(empreintes_decp) != {"aife", "dgfip"} or
            any(not isinstance(h, str) or not SHA.fullmatch(h)
                for h in empreintes_decp.values())):
        raise CorrespondanceInvalide("Empreintes des relevés DECP invalides.")
    for siret, nombre in decompte_decp.items():
        if not SIRET.fullmatch(siret) or type(nombre) is not int or nombre < 1:
            raise CorrespondanceInvalide("Effectifs DECP non admissibles.")

    extraits, numeros, uniques = [], set(), set()
    for item in sorted(rapport["dossiers"], key=lambda d: d["avis_boamp"]):
        id_avis, numero = item["avis_boamp"], item["siret_chiffres_sans_schema_boamp"]
        if (not AVIS.fullmatch(id_avis) or id_avis in uniques
                or not SIRET.fullmatch(numero)
                or not SHA.fullmatch(item.get("empreinte_avis_boamp", ""))
                or not SHA.fullmatch(item.get("sha256_reponse_api", ""))
                or not isinstance(item.get("preuve_siret_dans_boamp"), str)
                or not item["preuve_siret_dans_boamp"].startswith("/results/0/donnees/EFORMS/")
                or not isinstance(item.get("date_parution"), str)
                or not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", item["date_parution"])
                or not isinstance(item.get("presence_etablissement_exact_api"), bool)
                or item.get("role_contractant_juridiquement_confirme") is not False
                or item.get("identite_contrat_decp_etablie") is not False):
            raise CorrespondanceInvalide("Qualification BOAMP non admissible.")
        uniques.add(id_avis)
        numeros.add(numero)
        exact = item["presence_etablissement_exact_api"]
        if exact and not isinstance(item.get("preuve_etablissement_exact_api"), str):
            raise CorrespondanceInvalide("Attestation administrative exacte absente.")
        nombre_decp = decompte_decp.get(numero, 0) if exact else 0
        extraits.append({
            "avis_boamp": id_avis,
            "date_parution": item["date_parution"],
            "siret_acheteur_sans_schema_dans_avis": numero,
            "siret_etablissement_exact_dans_api": exact,
            "statut_administratif": (
                "etablissement_exact_retrouve_dans_reponse_administrative"
                if exact else "etablissement_exact_non_atteste_par_cette_api"
            ),
            "marches_decp_identites_meme_siret": nombre_decp,
            "rapprochement_acheteur_documentaire": bool(nombre_decp),
            "identite_contrat_decp_demonstree": False,
            "role_acheteur_juridiquement_confirme": False,
            "preuves": {
                "sha256_reponse_boamp": item["empreinte_avis_boamp"],
                "chemin_siret_dans_avis": item["preuve_siret_dans_boamp"],
                "sha256_reponse_administrative": item["sha256_reponse_api"],
                "chemin_etablissement_reponse_administrative":
                    item.get("preuve_etablissement_exact_api") if exact else None,
            },
        })
    if len(numeros) != 16 or len(uniques) != 17:
        raise CorrespondanceInvalide("Dénominateur des 17 avis modifié.")
    status = Counter(e["statut_administratif"] for e in extraits)
    return {
        "version": VERSION,
        "population": "17_avis_boamp_d_un_tirage_independant_non_representatif",
        "aucune_identite_de_contrat_deduite": True,
        "role_acheteur_juridiquement_etabli": False,
        "siret_boamp_initialement_sans_schema": True,
        "nombre_avis": len(extraits),
        "nombre_siret_boamp_distincts": len(numeros),
        "nombre_avis_avec_etablissement_exact_api": status[
            "etablissement_exact_retrouve_dans_reponse_administrative"],
        "nombre_avis_avec_siret_egal_a_un_acheteur_decp": sum(
            e["rapprochement_acheteur_documentaire"] for e in extraits),
        "empreintes_sources": {
            "audit_boamp": rapport["sha256_audit_boamp"],
            "rapport_administratif": rapport["sha256_rapport_administratif"],
            "decp": dict(sorted(empreintes_decp.items())),
        },
        "observations": extraits,
        "limite": (
            "Identifiant de quatorze chiffres sans schéma déclaré dans l'avis ; "
            "existence de l'établissement observée séparément dans une API publique "
            "non exhaustive. Une même chaîne SIRET en BOAMP et DECP est un "
            "rapprochement documentaire de l'acheteur, ni un contrat commun "
            "ni une confirmation juridique du rôle ni un besoin ouvert."
        ),
    }


def construire(tirage: Path, releve: Path, audit: Path, administration: Path,
               aife: Path, dgfip: Path) -> dict:
    """Recalculer toutes les preuves avant projection publique limitée."""
    chaines = reconstituer(tirage, releve, audit, administration, aife, dgfip)
    index = comptes_marches_decp(aife, dgfip)
    return construire_correspondances(chaines, index, {
        "aife": sha256(aife), "dgfip": sha256(dgfip)
    })


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tirage", type=Path, required=True)
    p.add_argument("--releve", type=Path, required=True)
    p.add_argument("--audit-boamp", type=Path, required=True)
    p.add_argument("--administration", type=Path, required=True)
    p.add_argument("--aife", type=Path,
                   default=Path("institutionnel/decp/sonde_aife_json.json"))
    p.add_argument("--dgfip", type=Path,
                   default=Path("institutionnel/decp/lot_dgfip_xml.json"))
    p.add_argument("--sortie", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.sortie.exists() or args.sortie.is_symlink():
            raise CorrespondanceInvalide("La sortie existe déjà.")
        resultat = construire(
            args.tirage, args.releve, args.audit_boamp,
            args.administration, args.aife, args.dgfip)
        contenu = json.dumps(resultat, ensure_ascii=False, sort_keys=True,
                             indent=2, allow_nan=False) + "\n"
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_text(contenu, encoding="utf-8")
        print(json.dumps({
            "avis": resultat["nombre_avis"],
            "etablissements_exacts": resultat["nombre_avis_avec_etablissement_exact_api"],
            "avis_meme_siret_decp": resultat["nombre_avis_avec_siret_egal_a_un_acheteur_decp"],
            "contrats_communs_etablis": 0,
        }, ensure_ascii=False, sort_keys=True))
    except (ValueError, TypeError, KeyError, OSError) as erreur:
        p.exit(1, f"Publication de correspondances refusée : {type(erreur).__name__}: {erreur}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
