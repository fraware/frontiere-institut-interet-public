"""Validation sans réseau du contrôle des publications préqualifiées."""
from datetime import datetime, timezone

import pytest

from scripts.reverifier_qualifications_veille import (
    RevueInvalide, evaluer_revisions, rapport,
)

MAINTENANT = datetime(2026, 10, 14, tzinfo=timezone.utc)
ID = "a" * 64
ORIGINE = "b" * 64
AUTRE = "c" * 64


def qualification():
    return {
        "version": "revue-signaux-v1",
        "observations": [{
            "id_observation": ID,
            "source_id": "anr",
            "empreinte_contenu_reference": ORIGINE,
        }],
    }


def source(empreinte=ORIGINE):
    return {"observations": [{
        "identifiant_publication": ID,
        "source_id": "anr",
        "empreinte_contenu": empreinte,
    }]}


def test_identite_conservee_ne_vaut_pas_validation_scientifique():
    resultat = evaluer_revisions(qualification(), source(), MAINTENANT)
    assert resultat["comptes"]["identique"] == 1
    assert not resultat["nouvelle_validation_scientifique_effectuee"]
    assert resultat["qualifications"][0]["interpretation_validee"] is False


def test_modification_de_contenu_reclame_requalification_sans_bloquer():
    resultat = evaluer_revisions(qualification(), source(AUTRE), MAINTENANT)
    assert resultat["comptes"]["revision_a_requalifier"] == 1
    assert ID in rapport(resultat)


def test_disparition_et_changement_de_producteur_sont_distincts():
    absent = evaluer_revisions(qualification(), {"observations": []}, MAINTENANT)
    assert absent["comptes"]["observation_absente"] == 1
    autre = source()
    autre["observations"][0]["source_id"] = "autre"
    modifie = evaluer_revisions(qualification(), autre, MAINTENANT)
    assert modifie["comptes"]["identite_source_modifiee"] == 1


def test_duplicates_dans_l_archive_sont_refuses():
    archive = source()
    archive["observations"].append(archive["observations"][0])
    with pytest.raises(RevueInvalide, match="dupliqué"):
        evaluer_revisions(qualification(), archive, MAINTENANT)


def test_mauvaise_empreinte_refusee():
    q = qualification()
    q["observations"][0]["empreinte_contenu_reference"] = "non-un-sha"
    with pytest.raises(RevueInvalide, match="empreinte"):
        evaluer_revisions(q, source(), MAINTENANT)
