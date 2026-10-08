"""Régression du raccordement entre requête verrouillée et répertoire local.

Toutes les ressources et les situations des essais sont artificielles.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.main import _interventions_existantes
from app.models import (
    AuditEvent, CapabilityQuery, Episode, NeedVersion, Organization, Resource,
    SearchRun, Discovery,
)
from app.orientation import (
    TYPE_EVENEMENT, clauses_recherche, empreinte, executer_sur_dossier, orienter,
    verifier_dossier,
)
from scripts.rechercher_capacites_institutionnelles import (
    construire_index, ouvrir_index,
)


def etablissement(code, nom, *, mission=None, domaine=None):
    return {
        "id": "FRONTIERE-INST-" + code,
        "nom_officiel": nom,
        "etat": "ACTIF",
        "famille": "recherche_publique" if domaine else "organisation_administrative_etat",
        "type_institutionnel": "Organisme fictif",
        "observe_le": "2026-10-08",
        "missions": (
            [{"texte": mission, "source_id": "source-fictive", "nature": "PUBLIEE"}]
            if mission else []
        ),
        "capacites": [],
        "domaines_recherche": (
            [{"texte": domaine, "source_id": "source-fictive", "nature": "PUBLIEE"}]
            if domaine else []
        ),
        "provenance": [{
            "source_id": "source-fictive",
            "identifiant_source": code,
            "url": "https://example.org/structure-fictive",
            "collecte_le": "2026-10-08",
            "empreinte": "f" * 64,
        }],
    }


@pytest.fixture
def environnement(tmp_path):
    moteur = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(moteur)
    with Session(moteur, expire_on_commit=False) as db:
        org = Organization(name="Administration fictive des mesures")
        db.add(org)
        db.flush()
        episode = Episode(
            code="EP-ESSAI-ORIENTATION", organization_id=org.id,
            title="Étude artificielle d'une ressource scientifique",
            sensitivity_level=1, synthetic=True,
        )
        db.add(episode)
        db.flush()
        verrou = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
        besoin = NeedVersion(
            episode_id=episode.id, version=1, active=True,
            current_situation="Étude de démonstration",
            desired_outcome="Trouver une piste à qualifier",
            locked_at=verrou,
        )
        db.add(besoin)
        db.flush()
        requete = CapabilityQuery(
            episode_id=episode.id, need_id=besoin.id, version=1, active=True,
            raw_request="Identifier une ressource pour une analyse scientifique.",
            domain="chimie",
            function="spectrométrie",
            depth="expert",
            operational_context="démonstration",
            constraints="délai expérimental de dix jours",
            resource_forms_json=json.dumps(["LABORATOIRE", "EQUIPE"]),
            must_have_json=json.dumps(["spectrométrie de masse", "expérience terrain"]),
            nice_to_have_json=json.dumps(["de la recherche publique", "coopération technique"]),
            locked_at=verrou,
        )
        db.add(requete)
        db.commit()

        dossier = tmp_path / "entites"
        source = dossier / "fictives"
        source.mkdir(parents=True)
        chemin = source / "notices.jsonl"
        organismes = [
            etablissement(
                "MISSION", "Centre des eaux",
                mission="Recherche en chimie, analyses spectrométriques des eaux.",
            ),
            etablissement(
                "DISCIPLINE", "Institut des matériaux",
                domaine="Chimie analytique et spectrométrie de masse.",
            ),
            etablissement("NOM", "Institut de spectrométrie scientifique"),
            etablissement("AUTRE", "Centre administratif de proximité"),
        ]
        chemin.write_text(
            "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in organismes),
            encoding="utf-8",
        )
        index = tmp_path / "institutionnel.sqlite3"
        construire_index(dossier, index)
        yield db, episode, besoin, requete, dossier, index, chemin
    moteur.dispose()


def test_orientation_reproductible_et_preuves_separees(environnement):
    db, episode, besoin, requete, dossier, chemin_index, _ = environnement
    rapport = executer_sur_dossier(
        db, code=episode.code, index_path=chemin_index, entites=dossier,
    )
    assert rapport["version_schema"] == "orientation-besoin-institutionnel-v1"
    assert rapport["besoin_version"] == 1
    assert rapport["requete_version"] == 1
    assert rapport["verification_sources"]["conforme"] is True
    assert [x["identifiant"] for x in rapport["clauses"]] == [
        "DOMAINE", "FONCTION", "IMPERATIF-1", "IMPERATIF-2",
        "SOUHAITABLE-1", "SOUHAITABLE-2",
    ]
    assert rapport["clauses"][4]["etat"] == "NON_EXPLOITABLE"
    assert "distinctif" in rapport["clauses"][4]["motif"]
    assert rapport["recherches"][4]["nombre_retours"] is None

    groupes = rapport["pistes_par_classe"]
    assert {x["identifiant"] for x in groupes["mission_ou_capacite_publiee"]} == {
        "FRONTIERE-INST-MISSION",
    }
    assert {x["identifiant"] for x in groupes["domaine_scientifique_publie"]} == {
        "FRONTIERE-INST-DISCIPLINE",
    }
    assert {x["identifiant"] for x in groupes["nom_uniquement"]} == {
        "FRONTIERE-INST-NOM",
    }
    assert all(
        x["disponibilite"] == "INCONNUE"
        and x["mobilisabilite"] == "NON_ETABLIE"
        and x["pertinence_pour_le_besoin"] == "NON_VERIFIEE"
        for sous_groupe in groupes.values() for x in sous_groupe
    )
    affirmations = groupes["domaine_scientifique_publie"][0]
    assert affirmations["nombre_clauses_recoupees"] >= 2
    assert "IMPERATIF-1" in affirmations["criteres_imperatifs_recoupes_lexicalement"]
    assert affirmations["correspondances"][0]["passages_publies"]
    assert all("source_id" in p for c in affirmations["correspondances"]
               for p in c["passages_publies"])
    assert db.scalar(select(func.count(SearchRun.id))) == 0
    assert db.scalar(select(func.count(Resource.id))) == 0
    assert db.scalar(select(func.count(Discovery.id))) == 0
    journal = db.scalar(select(AuditEvent).where(AuditEvent.event_type == TYPE_EVENEMENT))
    assert journal is not None and rapport["journal"]["evenement_id"] == journal.id
    preuve = json.loads(journal.payload_json)
    assert preuve["requete_id"] == requete.id
    assert preuve["besoin_id"] == besoin.id
    assert preuve["empreinte_sha256_rapport"] == rapport["journal"]["empreinte_sha256_contenu_rapport"]
    contenu_hache = {k: v for k, v in rapport.items() if k not in ("journal", "verification_sources")}
    assert empreinte(contenu_hache) == preuve["empreinte_sha256_rapport"]
    assert "orientation documentaire déjà effectuée" in _interventions_existantes(db, episode)


def test_journalise_chaque_execution_identique_sans_creer_de_recherche_publique(environnement):
    db, ep, _, _, dossier, chemin_index, _ = environnement
    premiere = executer_sur_dossier(
        db, code=ep.code, index_path=chemin_index, entites=dossier,
    )
    seconde = executer_sur_dossier(
        db, code=ep.code, index_path=chemin_index, entites=dossier,
    )
    assert premiere["journal"]["empreinte_sha256_contenu_rapport"] == seconde["journal"]["empreinte_sha256_contenu_rapport"]
    assert premiere["journal"]["evenement_id"] != seconde["journal"]["evenement_id"]
    assert db.scalar(select(func.count(AuditEvent.id))) == 2
    assert db.scalar(select(func.count(SearchRun.id))) == 0


def test_sources_modifiees_refusees_sans_evenement(environnement):
    db, ep, _, _, dossier, chemin_index, fichier = environnement
    fichier.write_text(fichier.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="périmé"):
        executer_sur_dossier(db, code=ep.code, index_path=chemin_index, entites=dossier)
    assert db.scalar(select(func.count(AuditEvent.id))) == 0


def test_besoin_non_verrouille_et_requete_ancienne_refuses(environnement):
    db, ep, besoin, requete, _, chemin_index, _ = environnement
    with ouvrir_index(chemin_index) as index:
        besoin.locked_at = None
        db.flush()
        with pytest.raises(ValueError, match="verrouillée"):
            orienter(db, index, code=ep.code)
        besoin.locked_at = datetime(2026, 10, 8, tzinfo=timezone.utc)
        nouveau = NeedVersion(
            episode_id=ep.id, version=2, active=True,
            current_situation="Nouvelle formulation fictive",
            desired_outcome="Nouvel objectif",
            locked_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
        )
        besoin.active = False
        db.add(nouveau)
        db.flush()
        with pytest.raises(ValueError, match="correspondre"):
            orienter(db, index, code=ep.code)
    assert db.scalar(select(func.count(AuditEvent.id))) == 0


def test_prospectif_sans_plan_bloque_l_orientation(environnement):
    db, ep, _, _, dossier, chemin_index, _ = environnement
    db.add(AuditEvent(
        episode_id=ep.id, entity_type="EPISODE", entity_id=ep.id,
        event_type="CAS_PROSPECTIF_PRE_ENREGISTRE",
        payload_json='{"source":"essai artificiel"}',
    ))
    db.commit()
    avant = db.scalar(select(func.count(AuditEvent.id)))
    with pytest.raises(ValueError, match="Plan de comparaison prospectif absent"):
        executer_sur_dossier(db, code=ep.code, index_path=chemin_index, entites=dossier)
    assert db.scalar(select(func.count(AuditEvent.id))) == avant

    db.add(AuditEvent(
        episode_id=ep.id, entity_type="EPISODE", entity_id=ep.id,
        event_type="COMPARAISON_APPARIEE_PRE_ENREGISTREE",
        payload_json='{"source":"essai artificiel"}',
    ))
    db.commit()
    rapport = executer_sur_dossier(
        db, code=ep.code, index_path=chemin_index, entites=dossier,
    )
    assert rapport["journal"]["type"] == TYPE_EVENEMENT


def test_dossier_sensible_refuse_sans_preuve_d_autorisation(environnement):
    db, ep, _, _, dossier, chemin_index, _ = environnement
    ep.sensitivity_level = 2
    db.commit()
    with pytest.raises(ValueError, match="non admissible"):
        executer_sur_dossier(db, code=ep.code, index_path=chemin_index, entites=dossier)
    assert db.scalar(select(func.count(AuditEvent.id))) == 0


def test_donnees_de_criteres_invalides_refusees_sans_journal(environnement):
    db, ep, _, query, dossier, chemin_index, _ = environnement
    query.must_have_json = '{"malforme": true}'
    db.commit()
    with pytest.raises(ValueError, match="must_have"):
        executer_sur_dossier(db, code=ep.code, index_path=chemin_index, entites=dossier)
    assert db.scalar(select(func.count(AuditEvent.id))) == 0


def test_domaine_generique_refuse_sans_journal(environnement):
    db, ep, _, query, dossier, chemin_index, _ = environnement
    query.domain = "la recherche publique"
    db.commit()
    with pytest.raises(ValueError, match="domaine"):
        executer_sur_dossier(db, code=ep.code, index_path=chemin_index, entites=dossier)
    assert db.scalar(select(func.count(AuditEvent.id))) == 0


def test_raccourci_vers_requete_non_verrouillee_refuse(environnement):
    db, ep, _, query, dossier, chemin_index, _ = environnement
    query.locked_at = None
    db.commit()
    with pytest.raises(ValueError, match="verrouillée"):
        executer_sur_dossier(db, code=ep.code, index_path=chemin_index, entites=dossier)


def test_recherche_tronquee_et_limite_d_entrees(environnement):
    db, ep, _, query, _, chemin_index, _ = environnement
    with ouvrir_index(chemin_index) as index:
        with pytest.raises(ValueError, match="limite"):
            orienter(db, index, code=ep.code, limite=0)
        with pytest.raises(ValueError, match="limite"):
            orienter(db, index, code=ep.code, limite=True)
    assert db.scalar(select(func.count(AuditEvent.id))) == 0
