"""Orientation documentaire d'un besoin FRONTIÈRE verrouillé.

Relie une requête de capacité du dossier à l'index institutionnel local.
Les correspondances ne prouvent ni une capacité ni sa disponibilité.
Une exécution réussie est inscrite dans le journal d'audit du dossier.
Aucune recherche publique, découverte ni décision n'est créée.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditEvent, CapabilityQuery, Episode, NeedVersion
from scripts.rechercher_capacites_institutionnelles import (
    chercher,
    ouvrir_index,
    termes_recherche,
    verifier_sources,
)

VERSION = "orientation-besoin-institutionnel-v1"
TYPE_EVENEMENT = "ORIENTATION_DOCUMENTAIRE_EXECUTEE"
CATEGORIES = (
    ("correspondances_aux_missions_ou_capacites_publiees", "mission_ou_capacite_publiee"),
    ("correspondances_aux_domaines_scientifiques_publies", "domaine_scientifique_publie"),
    ("correspondances_de_nom_uniquement", "nom_uniquement"),
)
PRIORITE = {nom: rang for rang, (_, nom) in enumerate(CATEGORIES)}
MAX_CRITERES = 12


def empreinte(objet: Any) -> str:
    brut = json.dumps(
        objet, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def liste_criteres(brut: str, champ: str) -> list[str]:
    try:
        valeur = json.loads(brut)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Critères {champ} illisibles : corriger la requête enregistrée.") from exc
    if not isinstance(valeur, list) or len(valeur) > MAX_CRITERES:
        raise ValueError(f"{champ} : liste de zéro à {MAX_CRITERES} éléments attendue.")
    if any(not isinstance(x, str) or not x.strip() or len(x) > 300 for x in valeur):
        raise ValueError(f"{champ} : chaque critère doit être un texte de 1 à 300 caractères.")
    return list(dict.fromkeys(x.strip() for x in valeur))


def clauses_recherche(query: CapabilityQuery) -> list[dict[str, Any]]:
    """Conserve l'origine des clauses et signale celles impropres à une recherche."""
    clauses = [
        ("DOMAINE", "domaine", query.domain, True),
        ("FONCTION", "fonction", query.function, True),
    ]
    imperatifs = liste_criteres(query.must_have_json, "must_have")
    souhaitables = liste_criteres(query.nice_to_have_json, "nice_to_have")
    clauses.extend(
        (f"IMPERATIF-{i}", "critere_imperatif", valeur, False)
        for i, valeur in enumerate(imperatifs, 1)
    )
    clauses.extend(
        (f"SOUHAITABLE-{i}", "critere_souhaitable", valeur, False)
        for i, valeur in enumerate(souhaitables, 1)
    )
    resultat = []
    for identifiant, champ, texte, obligatoire in clauses:
        if not isinstance(texte, str) or not texte.strip():
            raise ValueError(f"{champ} : valeur absente dans la requête verrouillée.")
        try:
            termes = termes_recherche(texte)
            etat, motif = "RECHERCHABLE", None
        except ValueError as exc:
            if obligatoire:
                raise ValueError(f"{champ} : {exc}") from exc
            termes, etat, motif = [], "NON_EXPLOITABLE", str(exc)
        resultat.append({
            "identifiant": identifiant,
            "champ": champ,
            "texte": texte.strip(),
            "termes": termes,
            "etat": etat,
            "motif": motif,
        })
    return resultat


def verifier_dossier(db: Session, code: str) -> tuple[Episode, NeedVersion, CapabilityQuery]:
    ep = db.scalar(select(Episode).where(Episode.code == code))
    if ep is None:
        raise ValueError("Dossier introuvable.")
    # Sans contrôle d'accès, le programme est réservé aux dossiers non sensibles.
    if ep.sensitivity_level != 1:
        raise ValueError("Dossier non admissible à la recherche locale sans contrôle d'accès.")
    besoins = list(db.scalars(select(NeedVersion).where(
        NeedVersion.episode_id == ep.id, NeedVersion.active.is_(True)
    )).all())
    if len(besoins) != 1 or besoins[0].locked_at is None:
        raise ValueError("Le dossier exige une unique version active du besoin verrouillée.")
    besoin = besoins[0]
    requetes = list(db.scalars(select(CapabilityQuery).where(
        CapabilityQuery.episode_id == ep.id, CapabilityQuery.active.is_(True)
    )).all())
    if len(requetes) != 1 or requetes[0].need_id != besoin.id or requetes[0].locked_at is None:
        raise ValueError("Une requête de capacité active et verrouillée doit correspondre au besoin courant.")
    baseline = db.scalar(select(AuditEvent.id).where(
        AuditEvent.episode_id == ep.id,
        AuditEvent.event_type == "CAS_PROSPECTIF_PRE_ENREGISTRE",
    ).limit(1))
    if baseline is not None:
        plan = db.scalar(select(AuditEvent.id).where(
            AuditEvent.episode_id == ep.id,
            AuditEvent.event_type == "COMPARAISON_APPARIEE_PRE_ENREGISTREE",
        ).limit(1))
        if plan is None:
            raise ValueError("Plan de comparaison prospectif absent : orientation interdite.")
    return ep, besoin, requetes[0]


def orienter(
    db: Session,
    index: sqlite3.Connection,
    *,
    code: str,
    limite: int = 8,
) -> dict[str, Any]:
    """Exécute et journalise une orientation sans promouvoir les pistes en découvertes."""
    if type(limite) is not int or not 1 <= limite <= 25:
        raise ValueError("La limite par catégorie doit être comprise entre 1 et 25.")
    ep, besoin, query = verifier_dossier(db, code)
    clauses = clauses_recherche(query)
    info = dict(index.execute("SELECT cle, valeur FROM informations").fetchall())
    if not info.get("empreinte_sources"):
        raise ValueError("Index institutionnel dépourvu d'empreinte de provenance.")
    candidats: dict[str, dict[str, Any]] = {}
    suivi = []
    for clause in clauses:
        if clause["etat"] != "RECHERCHABLE":
            suivi.append({
                "clause": clause["identifiant"], "etat": "NON_EXPLOITABLE",
                "motif": clause["motif"], "nombre_retours": None,
                "recherche_tronquee": None,
            })
            continue
        retour = chercher(index, clause["texte"], limite=limite)
        resultats_retrouves = 0
        for cle, categorie in CATEGORIES:
            for item in retour[cle]:
                resultats_retrouves += 1
                identifiant = item["identifiant"]
                if identifiant not in candidats:
                    candidats[identifiant] = {
                        "identifiant": identifiant,
                        "nom": item["nom"],
                        "famille": item["famille"],
                        "type_institutionnel": item["type_institutionnel"],
                        "observe_le": item["observe_le"],
                        "fichier_indexe": item["fichier_indexe"],
                        "provenance_notice": item["provenance_notice"],
                        "classe_de_preuve": categorie,
                        "correspondances": [],
                        "disponibilite": "INCONNUE",
                        "mobilisabilite": "NON_ETABLIE",
                        "pertinence_pour_le_besoin": "NON_VERIFIEE",
                    }
                candidat = candidats[identifiant]
                if PRIORITE[categorie] < PRIORITE[candidat["classe_de_preuve"]]:
                    candidat["classe_de_preuve"] = categorie
                candidat["correspondances"].append({
                    "clause": clause["identifiant"],
                    "type_correspondance": item["type_correspondance"],
                    "mots_retrouves_dans_les_missions": item["mots_retrouves_dans_les_missions"],
                    "mots_retrouves_dans_les_capacites": item["mots_retrouves_dans_les_capacites"],
                    "mots_retrouves_dans_les_domaines_scientifiques": item[
                        "mots_retrouves_dans_les_domaines_scientifiques"
                    ],
                    "mots_retrouves_dans_le_nom": item["mots_retrouves_dans_le_nom"],
                    "passages_publies": item["passages_publies"],
                })
        suivi.append({
            "clause": clause["identifiant"],
            "etat": "INTERROGEE",
            "motif": None,
            "nombre_retours": resultats_retrouves,
            "recherche_tronquee": retour["recherche_bornee_aux_1000_premiers_candidats"],
            "champs_tronques": retour.get("champs_dont_les_resultats_sont_tronques", []),
            "restitution_par_classe": retour["restitution_par_classe"],
            "restitution_partielle": bool(
                retour["recherche_bornee_aux_1000_premiers_candidats"]
                or any(
                    e["resultat_tronque"] for e in retour["restitution_par_classe"].values()
                )
            ),
        })

    groupes = {categorie: [] for _, categorie in CATEGORIES}
    for candidat in candidats.values():
        correspondances = candidat["correspondances"]
        candidat["nombre_clauses_recoupees"] = len({
            x["clause"] for x in correspondances
        })
        candidat["criteres_imperatifs_recoupes_lexicalement"] = sorted({
            x["clause"] for x in correspondances if x["clause"].startswith("IMPERATIF-")
        })
        groupes[candidat["classe_de_preuve"]].append(candidat)
    restitution_finale = {}
    for categorie in groupes:
        groupes[categorie].sort(
            key=lambda x: (-x["nombre_clauses_recoupees"], x["identifiant"])
        )
        nombre = len(groupes[categorie])
        restitution_finale[categorie] = {
            "candidats_distincts_avant_limite_finale": nombre,
            "candidats_restitues": min(nombre, limite),
            "candidats_ecartes_par_limite": max(0, nombre - limite),
        }
        groupes[categorie] = groupes[categorie][:limite]
    entree = {
        "episode": ep.code,
        "episode_id": ep.id,
        "besoin_id": besoin.id,
        "besoin_version": besoin.version,
        "requete_id": query.id,
        "requete_version": query.version,
        "domaine": query.domain,
        "fonction": query.function,
        "imperatifs": liste_criteres(query.must_have_json, "must_have"),
        "souhaitables": liste_criteres(query.nice_to_have_json, "nice_to_have"),
        "profondeur": query.depth,
        "formes_de_ressource": liste_criteres(query.resource_forms_json, "resource_forms"),
        "contexte_operationnel": query.operational_context,
        "contraintes": query.constraints,
        "echeance_utile": query.latest_useful_date.isoformat() if query.latest_useful_date else None,
    }
    rapport = {
        "version_schema": VERSION,
        "dossier": ep.code,
        "besoin_version": besoin.version,
        "requete_version": query.version,
        "empreinte_sha256_requete_verrouillee": empreinte(entree),
        "empreinte_sha256_referentiel": info["empreinte_sources"],
        "clauses": clauses,
        "recherches": suivi,
        "pistes_par_classe": groupes,
        "nombre_pistes_distinctes_avant_limite": len(candidats),
        "restitution_finale_par_classe": restitution_finale,
        "restitution_potentiellement_partielle": bool(
            any(x.get("restitution_partielle") for x in suivi)
            or any(x["candidats_ecartes_par_limite"] for x in restitution_finale.values())
        ),
        "limite_par_classe": limite,
        "criteres_non_verifies": [
            "Les critères impératifs sont des termes à rechercher, pas des conditions satisfaites.",
            "La profondeur, les formes de ressource, le contexte, les contraintes et l'échéance ne sont pas vérifiés par les notices.",
            "La pertinence effective, l'existence des moyens, la disponibilité et la mobilisabilité ne sont pas établies.",
            "La sélection et la restitution sont plafonnées ; les comptes signalent les pertes éventuelles, sans mesurer le rappel réel.",
            "Une absence de résultat ne prouve pas l'absence de capacité.",
            "Ce rapport ne constitue ni une recherche publique achevée, ni une découverte confirmée.",
        ],
    }
    empreinte_rapport = empreinte(rapport)
    event = AuditEvent(
        episode_id=ep.id,
        entity_type="CAPABILITY_QUERY",
        entity_id=query.id,
        event_type=TYPE_EVENEMENT,
        actor="outil local de recherche documentaire",
        payload_json=json.dumps({
            "version_schema": VERSION,
            "besoin_id": besoin.id,
            "besoin_version": besoin.version,
            "requete_id": query.id,
            "requete_version": query.version,
            "empreinte_sha256_requete": rapport["empreinte_sha256_requete_verrouillee"],
            "empreinte_sha256_referentiel": info["empreinte_sources"],
            "empreinte_sha256_rapport": empreinte_rapport,
            "nombre_pistes_documentaires": len(candidats),
            "nombre_clauses": len(clauses),
        }, ensure_ascii=False, sort_keys=True),
    )
    db.add(event)
    db.flush()
    rapport["journal"] = {
        "evenement_id": event.id,
        "type": TYPE_EVENEMENT,
        "empreinte_sha256_contenu_rapport": empreinte_rapport,
    }
    db.commit()
    return rapport


def executer_sur_dossier(
    db: Session, *,
    code: str, index_path: Path, entites: Path, limite: int = 8,
) -> dict:
    """Refuse tout index local périmé avant d'inscrire l'exécution en base."""
    from contextlib import closing

    # Toute erreur dans l'ouverture ou le contrôle laisse le dossier inchangé.
    with closing(ouvrir_index(index_path)) as index:
        controle = verifier_sources(index, entites)
        if not controle["conforme"]:
            raise ValueError("Index périmé : reconstruire avant toute orientation.")
        resultat = orienter(db, index, code=code, limite=limite)
    resultat["verification_sources"] = controle
    return resultat
