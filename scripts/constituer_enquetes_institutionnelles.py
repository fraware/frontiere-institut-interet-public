"""Reconstituer huit dossiers d'enquête sur les archives vérifiées de recrutement.

Les fiches sont des amorces d'enquête, ni des besoins actuels confirmés
ni une double relecture, et les observations web sont des annotations
manuelles datées dont le HTML n'est pas archivé ici.
Aucun accès réseau, aucun appel à un service externe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from scripts.preparer_relecture_besoins_explicites import (
    EchecPreuve, PARTITIONS, SHA, candidat, date_publique,
    empreinte, filtrer_texte
)

BASE = Path("institutionnel/besoins_publics")
MANIFESTE = BASE / "manifest_offres_postes.json"
REGISTRE = Path("evaluation/enquetes_institutionnelles_8_cibles_v1.json")
VERSION = "frontiere-registre-enquetes-huit-v1"
DATE_ETUDE = "2026-10-15"
DOMAINES = ("https://choisirleservicepublic.gouv.fr/offre-emploi/",
            "https://www.emploi-territorial.fr/offre/")
ETATS_WEB = {
    "annonce_officielle_consultable",
    "annonce_officielle_consultable_date_limite_passee",
    "lien_officiel_redirige_vers_offre_depubliee",
    "delai_candidature_expire_offre_depubliee",
    "page_officielle_non_verifiee",
}
STATUTS_CHAMP = {
    "absent", "tronque", "champ_trop_long_ou_filtre", "court_repris"
}


def verifier(condition: bool, motif: str) -> None:
    if not condition:
        raise EchecPreuve(motif)


def verifier_cibles(cibles: dict) -> dict[str, dict]:
    verifier(cibles.get("version") == "frontiere-cibles-enquete-institutionnelle-v1"
             and cibles.get("date_etude") == DATE_ETUDE
             and cibles.get("source_selection") ==
             "relecture-besoins-csp-38817002674"
             and cibles.get("sha256_registre_24") ==
             "38fb7b7c901391de7fd00e1c92d4f8f775351dfd083843fead976af9f37b3f22"
             and cibles.get("statuts_recrutement_verifies") == 0
             and cibles.get("besoins_non_satisfaits_confirmes") == 0
             and cibles.get("contacts_institutionnels_realises") == 0
             and isinstance(cibles.get("items"), list)
             and len(cibles["items"]) == 8, "Cibles ou limites de preuve incompatibles.")
    resultat = {}
    for item in cibles["items"]:
        ref = item["reference"]
        chemin = item["partition"]
        web = item["preuve_web"]
        verifier(isinstance(ref, str) and 4 <= len(ref) <= 180
                 and ref not in resultat and
                 chemin.startswith((BASE / "offres_postes").as_posix() + "/")
                 and chemin.removeprefix((BASE / "offres_postes").as_posix() + "/")
                 in PARTITIONS and
                 type(item["ligne"]) is int and item["ligne"] > 0 and
                 isinstance(item["sha256_ligne"], str) and
                 SHA.fullmatch(item["sha256_ligne"]) is not None and
                 date_publique(item["date_publication_archives"]) ==
                 item["date_publication_archives"] and
                 filtrer_texte(item["domaine_enquete_hypothese"], 160) and
                 filtrer_texte(item["organisme_cible_enquete"], 240) and
                 filtrer_texte(item["question_institutionnelle"], 550),
                 "Identité ou question de dossier non admissible.")
        verifier(isinstance(web, dict)
                 and web.get("type") in ETATS_WEB
                 and web.get("consultation") == DATE_ETUDE
                 and web.get("statut_recrutement_actuel") == "non_etabli"
                 and web.get("contrat_pourvu") == "non_etabli"
                 and web.get("source_html_non_archivee") is True,
                 "Un état actuel a été affirmé sans preuve.")
        url = web.get("url")
        verifier((url is None and web["type"] == "page_officielle_non_verifiee")
                 or (isinstance(url, str)
                     and any(url.startswith(d) for d in DOMAINES)
                     and web["type"] != "page_officielle_non_verifiee"),
                 "Lien officiel non vérifié ou déclaration de vérification excessive.")
        resultat[ref] = item
    return resultat


def classer_competences(ligne: dict, projection: dict) -> dict:
    valeur = ligne.get("competences_attendues")
    tronque = "competences_attendues" in ligne.get("champs_tronques", [])
    if tronque:
        statut = "tronque"
    elif not isinstance(valeur, str) or not valeur.strip():
        statut = "absent"
    elif projection["competences_attendues_citees_integralement"] is None:
        statut = "champ_trop_long_ou_filtre"
    else:
        statut = "court_repris"
    verifier(statut in STATUTS_CHAMP, "Statut de champ inconnu.")
    return {
        "statut_champ": statut,
        "longueur_caracteres_source": len(valeur.strip()) if isinstance(valeur, str) else 0,
        "citation_publiee": False,
        "commentaire": ("Le contenu potentiellement long ou nominatif du champ "
                        "est conservé uniquement dans la partition source ; "
                        "sa présence ne prouve pas une pénurie.")
    }


def constituer(racine: Path, chemin_cibles: Path | None = None) -> dict:
    chemin_cibles = chemin_cibles or (racine / REGISTRE)
    octets_cibles = chemin_cibles.read_bytes()
    cibles = json.loads(octets_cibles)
    attendu = verifier_cibles(cibles)
    manifest = json.loads((racine / MANIFESTE).read_text(encoding="utf-8"))
    checks = manifest.get("empreintes_partitions")
    verifier(manifest.get("version") == "emplois-publics-extraits-v1"
             and isinstance(checks, dict) and set(checks) == set(PARTITIONS)
             and type(manifest.get("offres_distinctes")) is int
             and manifest["offres_distinctes"] > 0,
             "Manifeste historique incompatible.")
    verifications = {}
    lignes_sources = {}
    nombre_lignes = 0
    for nom in PARTITIONS:
        h = hashlib.sha256()
        chemin = (BASE / "offres_postes" / nom)
        with (racine / chemin).open("rb") as fd:
            for n, ligne in enumerate(fd, 1):
                h.update(ligne)
                nombre_lignes += 1
                verifier(ligne.endswith(b"\n") and len(ligne) <= 24_000,
                         "Ligne source anormale.")
                # Rejeter une mauvaise syntaxe JSON même dans un lot non sélectionné.
                doc = json.loads(ligne)
                verifier(isinstance(doc, dict) and
                         isinstance(doc.get("reference"), str),
                         "Enregistrement source non conforme.")
                ref = doc["reference"]
                if ref in attendu:
                    item = attendu[ref]
                    if item["partition"] == chemin.as_posix() and item["ligne"] == n:
                        verifier(empreinte(ligne) == item["sha256_ligne"],
                                 "Empreinte de ligne source incompatible.")
                        verifier(ref not in lignes_sources,
                                 "Plusieurs lignes possibles pour une preuve.")
                        lignes_sources[ref] = (doc, ligne)
        verifier(h.hexdigest() == checks[nom],
                 "Partition source altérée : " + nom)
        verifications[nom] = h.hexdigest()
    verifier(nombre_lignes == manifest["offres_distinctes"],
             "Le décompte des variantes ne concorde pas.")
    verifier(set(lignes_sources) == set(attendu),
             "Toutes les lignes de preuve n'ont pas été retrouvées.")

    dossiers = []
    for ref, cible in attendu.items():
        source, brut = lignes_sources[ref]
        projection = candidat(source, cible["partition"], cible["ligne"], brut)
        verifier(projection is not None
                 and projection["reference"] == ref
                 and projection["date_publication"] ==
                 cible["date_publication_archives"]
                 and projection["preuve"]["sha256_ligne_jsonl"] ==
                 cible["sha256_ligne"]
                 and projection["revue_humaine"] == "non_effectuee",
                 "Projection initiale incompatible avec la ligne originale.")
        dossier = {
            "reference": ref,
            "titre_exact_source": projection["titre_cite_integralement"],
            "entite_declarante_exacte": projection["entite_declarante"],
            "champ_entite": projection["champ_entite_declarante"],
            "organisme_cible_enquete_a_confirmer": cible["organisme_cible_enquete"],
            "date_debut_publication": projection["date_publication"],
            "fin_diffusion_declaree": date_publique(source.get("publication_fin")),
            "date_vacance_declaree": date_publique(source.get("date_vacance")),
            "statut_poste_historique": filtrer_texte(source.get("statut_poste"), 120),
            "metier_declare": projection["metier_declare"],
            "competences_champ_source": classer_competences(source, projection),
            "hypothese_domaine_a_tester": cible["domaine_enquete_hypothese"],
            "observation_page_officielle_sans_capture": cible["preuve_web"],
            "question_centrale": cible["question_institutionnelle"],
            "verification_humaine": "a_realiser",
            "recrutement_actuel": "inconnu",
            "recrutement_pourvu": "inconnu",
            "competence_publique_disponible": "inconnue",
            "difficulte_de_mobilisation": "non_etablie",
            "besoin_non_satisfait": "non_etabli",
            "preuve_archive": {
                "fichier": cible["partition"],
                "ligne": cible["ligne"],
                "sha256_ligne": cible["sha256_ligne"],
                "cle_enregistrement": projection["cle_enregistrement"],
                "source_instantane": "2026-10-12",
            },
            "prochaines_verifications": [
                "Demander l'issue du recrutement, sans supposer un échec.",
                "Identifier les capacités mobilisées et les solutions déjà essayées.",
                "Distinguer la fin de diffusion d'une clôture de candidature.",
                "Reconstituer la chronologie de décision et les délais de recrutement.",
                "Demander une confirmation non nominative à l'établissement."
            ]
        }
        dossiers.append(dossier)
    comptes = {k: sum(1 for d in dossiers
                      if d["competences_champ_source"]["statut_champ"] == k)
               for k in sorted(STATUTS_CHAMP)}
    return {
        "version": VERSION,
        "origine": "huit_references_issues_du_tirage_csp_de_24",
        "sha256_selection": empreinte(octets_cibles),
        "sha256_archive_candidats_24": cibles["sha256_registre_24"],
        "date_enquete": DATE_ETUDE,
        "partitions_integralement_verifiees": len(verifications),
        "variantes_lues": nombre_lignes,
        "references_examinees": len(dossiers),
        "compteurs_champ_competences": comptes,
        "episodes_de_deficit_de_capacite_confirmes": 0,
        "recrutements_actuels_confirmes": 0,
        "entretiens_realises": 0,
        "validations_independantes_realisees": 0,
        "scope": ("Amorces d'enquête sur publications historiques. "
                  "L'état actuel, la difficulté de recrutement, la disponibilité "
                  "des compétences et l'issue effective exigent une enquête externe."),
        "dossiers": dossiers,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--racine", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--cibles", type=Path)
    p.add_argument("--sortie", type=Path, required=True)
    args = p.parse_args()
    try:
        verifier(not args.sortie.exists() and not args.sortie.is_symlink(),
                 "Refus d'écraser une sortie existante.")
        resultat = constituer(args.racine, args.cibles)
        data = (json.dumps(resultat, ensure_ascii=False, sort_keys=True,
                           indent=2, allow_nan=False) + "\n").encode("utf-8")
        verifier(len(data) < 100_000, "Rapport d'enquête excessif.")
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_bytes(data)
        print(json.dumps({
            "cas": len(resultat["dossiers"]),
            "variantes": resultat["variantes_lues"],
            "comptes_competences": resultat["compteurs_champ_competences"],
            "deficits_confirmes": 0,
            "recrutements_confirmes": 0
        }, ensure_ascii=False, sort_keys=True))
    except (OSError, EchecPreuve, ValueError, KeyError, TypeError) as exc:
        p.exit(1, f"Construction d'enquête refusée : {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
