"""Évaluer les limites du rapprochement lexical sur des cas exclusivement fictifs.

Les jugements du jeu sont rédigés par les concepteurs du banc artificiel :
les ratios qui en découlent ne représentent aucune efficacité institutionnelle.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import (
    AuditEvent, CapabilityQuery, Discovery, Episode, NeedVersion, Organization,
    Resource, SearchRun,
)
from app.orientation import TYPE_EVENEMENT, executer_sur_dossier
from scripts.rechercher_capacites_institutionnelles import construire_index

RACINE = Path(__file__).resolve().parents[1]
FICHIER_PAR_DEFAUT = RACINE / "evaluation" / "jeu_orientation_synthetique_v1.json"
TYPES = (
    "mission_ou_capacite_publiee",
    "domaine_scientifique_publie",
    "nom_uniquement",
)


def verifier_jeu(donnees: dict) -> None:
    if not isinstance(donnees, dict) or donnees.get("version_schema") != "jeu-orientation-synthetique-v1":
        raise ValueError("Version du jeu artificiel absente ou incorrecte.")
    if donnees.get("nature") != "EXCLUSIVEMENT_ARTIFICIELLE":
        raise ValueError("Le jeu doit être explicitement identifié comme artificiel.")
    structures = donnees.get("structures")
    cas = donnees.get("cas")
    if not isinstance(structures, list) or not structures or not isinstance(cas, list) or not cas:
        raise ValueError("Structures et cas synthétiques obligatoires.")
    codes = set()
    for objet in structures:
        if not isinstance(objet, dict) or not isinstance(objet.get("code"), str):
            raise ValueError("Structure synthétique invalide.")
        code = objet["code"]
        if code in codes or not code.startswith("S-") or len(code) > 35:
            raise ValueError("Identifiant de structure absent, répété ou invalide.")
        codes.add(code)
        if not isinstance(objet.get("nom"), str) or not objet["nom"].strip():
            raise ValueError("Structure fictive sans nom.")
        if objet.get("etat") not in {"ACTIF", "SUPPRIME"}:
            raise ValueError("État de structure artificielle invalide.")
        for champ in ("mission", "domaine"):
            if champ in objet and not isinstance(objet[champ], str):
                raise ValueError("Texte de mission ou domaine artificiel invalide.")
    identifiants_cas = set()
    for dossier in cas:
        if not isinstance(dossier, dict) or not isinstance(dossier.get("code"), str):
            raise ValueError("Cas artificiel sans identifiant.")
        code = dossier["code"]
        if code in identifiants_cas or len(code) > 38:
            raise ValueError("Cas artificiel répété ou trop long.")
        identifiants_cas.add(code)
        if any(not isinstance(dossier.get(c), str) or not dossier[c].strip()
               for c in ("domaine", "fonction", "raison")):
            raise ValueError("Besoin artificiel sans domaine, fonction ou motif.")
        imperatifs = dossier.get("imperatifs")
        if not isinstance(imperatifs, list) or any(not isinstance(x, str) for x in imperatifs):
            raise ValueError("Critères impératifs artificiels invalides.")
        attendus = dossier.get("attendus")
        if not isinstance(attendus, dict) or set(attendus) != set(TYPES):
            raise ValueError("Les trois classes de repères doivent être déclarées.")
        for categorie in TYPES:
            valeurs = attendus[categorie]
            if not isinstance(valeurs, list) or len(valeurs) != len(set(valeurs)):
                raise ValueError("Repères dupliqués ou invalides.")
            if any(x not in codes for x in valeurs):
                raise ValueError("Repère documentaire absent du répertoire fictif.")


def notice_artificielle(item: dict) -> dict:
    def publiés(champ: str) -> list[dict]:
        texte = item.get(champ)
        if not texte:
            return []
        return [{"texte": texte, "source_id": "corpus-fictif",
                 "nature": "PUBLIEE"}]

    identifiant = item["code"]
    return {
        "id": f"FRONTIERE-INST-{identifiant}",
        "nom_officiel": item["nom"],
        "etat": item["etat"],
        "famille": "recherche_publique" if item.get("domaine") else "organisation_administrative_etat",
        "type_institutionnel": "Structure fictive",
        "observe_le": "2026-10-08",
        "missions": publiés("mission"),
        "capacites": [],
        "domaines_recherche": publiés("domaine"),
        "provenance": [{
            "source_id": "corpus-fictif",
            "identifiant_source": identifiant,
            "url": "https://example.org/structures-entierement-artificielles",
            "collecte_le": "2026-10-08",
            "empreinte": hashlib.sha256(
                json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }],
    }


def mesurer_cas(db: Session, dossier: dict, index_path: Path, repertoire: Path) -> dict:
    org = db.scalar(select(Organization).where(Organization.name == "Administration fictive d'essai"))
    if org is None:
        org = Organization(name="Administration fictive d'essai")
        db.add(org)
        db.flush()
    code = f"EP-SYN-{dossier['code']}"
    ep = Episode(
        code=code, organization_id=org.id, title="Essai artificiel",
        sensitivity_level=1, synthetic=True,
    )
    db.add(ep)
    db.flush()
    verrou = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
    besoin = NeedVersion(
        episode_id=ep.id, version=1, active=True,
        current_situation="Expérience artificielle sur une demande",
        desired_outcome="Pistes documentaires seulement",
        locked_at=verrou,
    )
    db.add(besoin)
    db.flush()
    query = CapabilityQuery(
        episode_id=ep.id, need_id=besoin.id, version=1, active=True,
        raw_request=dossier["domaine"] + " — " + dossier["fonction"],
        domain=dossier["domaine"], function=dossier["fonction"],
        must_have_json=json.dumps(dossier["imperatifs"], ensure_ascii=False),
        nice_to_have_json="[]", resource_forms_json="[]",
        locked_at=verrou, compiler="synthetique",
    )
    db.add(query)
    db.commit()
    orientation = executer_sur_dossier(
        db, code=code, index_path=index_path, entites=repertoire, limite=25,
    )
    if orientation["restitution_potentiellement_partielle"]:
        raise ValueError(
            f"Le cas {dossier['code']} ne peut être comparé intégralement : "
            "certaines pistes documentaires ont été limitées."
        )
    classes = orientation["pistes_par_classe"]
    retrouvés = {}
    omis = {}
    supplementaires = {}
    pour_chaque = {}
    for classe in TYPES:
        observés = {
            x["identifiant"].removeprefix("FRONTIERE-INST-")
            for x in classes[classe]
        }
        attendus = set(dossier["attendus"][classe])
        retrouves_cas = sorted(observés & attendus)
        omis_cas = sorted(attendus - observés)
        supplementaires_cas = sorted(observés - attendus)
        retrouvés[classe] = retrouves_cas
        omis[classe] = omis_cas
        supplementaires[classe] = supplementaires_cas
        pour_chaque[classe] = {
            "nombre_reperes_attendus": len(attendus),
            "nombre_pistes_restituees": len(observés),
            "nombre_reperes_retrouves": len(retrouves_cas),
            "nombre_reperes_omis": len(omis_cas),
            "nombre_pistes_hors_reperes": len(supplementaires_cas),
        }
    if any(
        item["disponibilite"] != "INCONNUE"
        or item["mobilisabilite"] != "NON_ETABLIE"
        or item["pertinence_pour_le_besoin"] != "NON_VERIFIEE"
        for categorie in classes.values() for item in categorie
    ):
        raise ValueError("Une notice artificielle a été promue en ressource opérationnelle.")
    return {
        "cas": dossier["code"],
        "raison_du_cas": dossier["raison"],
        "observations_par_classe": pour_chaque,
        "reperes_retrouves": retrouvés,
        "reperes_omis": omis,
        "pistes_hors_reperes": supplementaires,
        "verification_sources": orientation["verification_sources"]["conforme"],
        "empreinte_sha256_reponse": orientation["journal"]["empreinte_sha256_contenu_rapport"],
    }


def evaluer(donnees: dict) -> dict:
    verifier_jeu(donnees)
    with tempfile.TemporaryDirectory(prefix="frontiere-test-artificiel-") as tmp:
        racine = Path(tmp)
        dossier = racine / "entites" / "fictives"
        dossier.mkdir(parents=True)
        index = racine / "recherche.sqlite3"
        (dossier / "notices.jsonl").write_text(
            "".join(
                json.dumps(notice_artificielle(x), ensure_ascii=False) + "\n"
                for x in donnees["structures"]
            ), encoding="utf-8",
        )
        analyse_index = construire_index(racine / "entites", index)
        moteur = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(moteur)
        try:
            with Session(moteur, expire_on_commit=False) as db:
                evaluations = [
                    mesurer_cas(db, cas, index, racine / "entites")
                    for cas in donnees["cas"]
                ]
                nombres = {
                    "journalisations": db.scalar(select(func.count(AuditEvent.id)).where(
                        AuditEvent.event_type == TYPE_EVENEMENT
                    )),
                    "recherches_publiques_creees": db.scalar(select(func.count(SearchRun.id))),
                    "ressources_creees": db.scalar(select(func.count(Resource.id))),
                    "decouvertes_creees": db.scalar(select(func.count(Discovery.id))),
                }
        finally:
            moteur.dispose()
    if nombres != {
        "journalisations": len(donnees["cas"]),
        "recherches_publiques_creees": 0,
        "ressources_creees": 0,
        "decouvertes_creees": 0,
    }:
        raise ValueError("Le protocole artificiel a produit des écritures inattendues.")
    nombre_attendu = sum(
        ligne["nombre_reperes_attendus"]
        for evaluation in evaluations
        for ligne in evaluation["observations_par_classe"].values()
    )
    nombre_retrouve = sum(
        ligne["nombre_reperes_retrouves"]
        for evaluation in evaluations
        for ligne in evaluation["observations_par_classe"].values()
    )
    autres = sum(
        ligne["nombre_pistes_hors_reperes"]
        for evaluation in evaluations
        for ligne in evaluation["observations_par_classe"].values()
    )
    contenu = json.dumps(
        donnees, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return {
        "version_schema": "rapport-orientation-synthetique-v1",
        "nature": "EXCLUSIVEMENT_ARTIFICIELLE",
        "empreinte_sha256_jeu": hashlib.sha256(contenu).hexdigest(),
        "nombre_notices_fictives": analyse_index["nombre_entites"],
        "nombre_cas_fictifs": len(evaluations),
        "reperes_attendus": nombre_attendu,
        "reperes_retrouves": nombre_retrouve,
        "reperes_omis": nombre_attendu - nombre_retrouve,
        "pistes_hors_reperes": autres,
        "ratio_de_reperage_sur_reperes_fictifs": (
            nombre_retrouve / nombre_attendu if nombre_attendu else None
        ),
        "integrite_operations": nombres,
        "cas": evaluations,
        "limite": (
            "Les repères ont été rédigés par les auteurs du jeu artificiel. "
            "Les pistes hors repères ne prouvent pas une erreur scientifique ; "
            "les omissions mesurent les cas artificiels seulement. "
            "Ce résultat ne mesure ni la pertinence institutionnelle, "
            "ni la disponibilité, ni la valeur ajoutée de FRONTIÈRE."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Éprouver le rapprochement documentaire sur des besoins et des structures fictifs."
    )
    parser.add_argument("--jeu", type=Path, default=FICHIER_PAR_DEFAUT)
    args = parser.parse_args()
    try:
        donnees = json.loads(args.jeu.read_text(encoding="utf-8"))
        resultat = evaluer(donnees)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Évaluation synthétique refusée : {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
