"""Auditer les identifiants d'acheteurs sur 36 avis BOAMP indépendants.

Les 36 réponses ont déjà été capturées par l'étude indépendante. Ce programme
n'interroge aucun service distant, contrôle les octets et conserve la distinction
entre SIRET explicite et identifiant à quatorze chiffres sans schéma.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re

try:
    from scripts.collecter_notices_pilotes_boamp import adresse
    from scripts.extraire_references_boamp_decp import (
        references_notice, identifiant_acheteur_14_non_qualifie,
        siret_acheteur_sans_reference_projet,
    )
    from scripts.relever_issues_echantillon_independant import (
        VERSION as VERSION_RELEVE, charger_tirage,
    )
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from collecter_notices_pilotes_boamp import adresse
    from extraire_references_boamp_decp import (
        references_notice, identifiant_acheteur_14_non_qualifie,
        siret_acheteur_sans_reference_projet,
    )
    from relever_issues_echantillon_independant import (
        VERSION as VERSION_RELEVE, charger_tirage,
    )

VERSION = "audit-acheteurs-36-boamp-v1"
SHA = re.compile(r"[0-9a-f]{64}")


class AuditInvalide(ValueError):
    """Archive incohérente ou identité documentaire non contrôlable."""


def sha256(octets: bytes) -> str:
    """Calculer l'empreinte de la source sans réencoder sa représentation."""
    return hashlib.sha256(octets).hexdigest()


def auditer(tirage: Path, releve: Path) -> dict:
    """Rejouer les preuves de chaque avis, sans modifier le tirage ni ses résultats."""
    source = charger_tirage(tirage)
    contenu_tirage = tirage.read_bytes()
    manifeste = json.loads((releve / "rapport.json").read_text(encoding="utf-8"))
    if (not isinstance(manifeste, dict)
            or manifeste.get("version") != VERSION_RELEVE
            or manifeste.get("sha256_fichier_tirage") != sha256(contenu_tirage)
            or manifeste.get("sha256_identifiants_ordonnes")
               != source["sha256_identifiants_ordonnes"]
            or manifeste.get("nombre_cas") != len(source["cas"])):
        raise AuditInvalide("Relevé différent du tirage indépendant publié")
    fiches = manifeste.get("cas")
    if not isinstance(fiches, list) or len(fiches) != len(source["cas"]):
        raise AuditInvalide("Effectif des captures incohérent")
    resultats = []
    statuts = Counter()
    identites = Counter()
    mois = Counter()
    for attendu, fiche in zip(source["cas"], fiches):
        if not isinstance(fiche, dict):
            raise AuditInvalide("Fiche de capture non structurée")
        numero = attendu["avis"]
        nom = numero + ".json"
        if (fiche.get("avis") != numero
                or fiche.get("date_parution_index") != attendu["date_parution"]
                or fiche.get("fichier_reponse") != nom
                or fiche.get("source_officielle") != adresse(numero)):
            raise AuditInvalide("Ordre, date ou adresse des réponses modifiés")
        fichier = releve / nom
        if fichier.is_symlink() or not fichier.is_file():
            raise AuditInvalide("Fichier de réponse absent ou lien symbolique")
        octets = fichier.read_bytes()
        empreinte = fiche.get("sha256_reponse_http")
        if (not isinstance(empreinte, str) or not SHA.fullmatch(empreinte)
                or len(octets) != fiche.get("octets_reponse_http")
                or sha256(octets) != empreinte):
            raise AuditInvalide("Octets officiels ou empreinte incompatibles")
        try:
            enveloppe = json.loads(octets)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuditInvalide("Réponse officielle non JSON") from exc
        if not isinstance(enveloppe, dict):
            raise AuditInvalide("Enveloppe non structurée")
        n, notices = enveloppe.get("total_count"), enveloppe.get("results")
        if (type(n) is not int or n not in (0, 1)
                or not isinstance(notices, list) or len(notices) != n):
            raise AuditInvalide("Réponse officielle ambiguë")
        statut = fiche.get("statut_releve")
        if not isinstance(statut, str):
            raise AuditInvalide("Statut de relevé absent")
        statuts[statut] += 1
        mois[attendu["date_parution"][:7]] += 1
        resultat = {
            "avis": numero,
            "mois": attendu["date_parution"][:7],
            "sha256_reponse_http": empreinte,
            "statut_releve_initial": statut,
            "identite_acheteur": None,
            "champ_identite": None,
            "statut_identite": "inconnu",
            "reference_projet": None,
            "statut_reference": "inconnu",
            "confirmation_juridique_siret": False,
            "correspondance_contractuelle_etablie": False,
        }
        if n == 0:
            if statut != "non_retrouve_lors_du_releve":
                raise AuditInvalide("Statut d'absence contradictoire")
            resultat["statut_identite"] = "avis_non_retrouve"
            resultats.append(resultat)
            identites[resultat["statut_identite"]] += 1
            continue
        notice = notices[0]
        if not isinstance(notice, dict) or notice.get("idweb") != numero:
            raise AuditInvalide("Identifiant BOAMP contradictoire")
        if notice.get("dateparution") != attendu["date_parution"]:
            if statut != "date_officielle_divergente":
                raise AuditInvalide("Divergence de date non déclarée")
            resultat["statut_identite"] = "date_officielle_divergente"
            resultats.append(resultat)
            identites[resultat["statut_identite"]] += 1
            continue
        if statut in {"non_retrouve_lors_du_releve", "date_officielle_divergente"}:
            raise AuditInvalide("Statut absent/divergent incompatible avec l'avis")
        references, statut_ref = references_notice(notice)
        siret_explicite = siret_acheteur_sans_reference_projet(notice)
        non_qualifie = identifiant_acheteur_14_non_qualifie(notice)
        if siret_explicite is not None and non_qualifie is not None:
            raise AuditInvalide("Deux qualifications d'identité contradictoires")
        resultat["statut_reference"] = statut_ref
        if siret_explicite is not None:
            resultat.update({
                "identite_acheteur": siret_explicite["acheteur_siret"],
                "champ_identite": siret_explicite["chemin_preuve"],
                "statut_identite": "siret_explicitement_qualifie_dans_avis",
                "reference_projet": references[0]["id_marche"] if references else None,
            })
        elif non_qualifie is not None:
            resultat.update({
                "identite_acheteur": non_qualifie["identifiant_14_chiffres"],
                "champ_identite": non_qualifie["chemin_preuve"],
                "statut_identite": "identifiant_14_chiffres_sans_schema",
            })
        else:
            resultat["statut_identite"] = "aucune_identite_acheteur_qualifiable"
        # Le SIRET explicitement qualifié et l'identifiant non qualifié
        # ne deviennent jamais des preuves de validité au répertoire SIRENE.
        identites[resultat["statut_identite"]] += 1
        resultats.append(resultat)
    if sum(statuts.values()) != len(fiches):
        raise AuditInvalide("Comptage des statuts incohérent")
    if dict(sorted(statuts.items())) != manifeste.get("statuts_releve"):
        raise AuditInvalide("Distribution de statuts différente du relevé initial")
    return {
        "version": VERSION,
        "source_tirage_sha256": sha256(contenu_tirage),
        "source_manifeste_sha256": sha256(
            (releve / "rapport.json").read_bytes()
        ),
        "nombre_avis_tires": len(resultats),
        "nombre_avis_distincts": len({x["avis"] for x in resultats}),
        "mois": dict(sorted(mois.items())),
        "statuts_releves": dict(sorted(statuts.items())),
        "repartition_identifiants": dict(sorted(identites.items())),
        "identifiants_explicitement_siret": identites[
            "siret_explicitement_qualifie_dans_avis"
        ],
        "identifiants_14_chiffres_non_qualifies": identites[
            "identifiant_14_chiffres_sans_schema"
        ],
        "correspondances_contractuelles_verifiees": 0,
        "verification_registre_sirene_effectuee": False,
        "etude_representative_de_la_france": False,
        "conclusions_sur_competences_autorisees": False,
        "avis": resultats,
    }


def main() -> None:
    """Auditer localement le relevé officiel indépendant, sans écraser de rapport."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--echantillon", required=True, type=Path)
    p.add_argument("--releve", required=True, type=Path)
    p.add_argument("--sortie", required=True, type=Path)
    a = p.parse_args()
    try:
        bilan = auditer(a.echantillon, a.releve)
        if a.sortie.exists() or a.sortie.is_symlink():
            raise AuditInvalide("Rapport déjà présent")
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        a.sortie.write_text(
            json.dumps(bilan, ensure_ascii=False, indent=2,
                       sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "avis": bilan["nombre_avis_tires"],
            "repartition": bilan["repartition_identifiants"],
            "correspondances_contractuelles_verifiees": 0,
        }, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.exit(1, f"Audit indépendant refusé : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
