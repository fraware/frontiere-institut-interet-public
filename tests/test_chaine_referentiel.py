"""Vérifier les invariants de la chaîne avec le corpus de référence, sans réseau."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.verifier_chaine_referentiel import charger, verifier

RACINE = Path(__file__).resolve().parents[1]


def test_chaine_courante_est_structurellement_coherente():
    rapport = verifier(charger())
    assert rapport["coherence_structurelle"] is True
    assert rapport["nombre_organisations_etat"] >= 5000
    assert rapport["nombre_services_locaux"] >= 80000
    assert rapport["nombre_territoires"] >= 35000
    assert rapport["analyse_semantique_independante"] is False
    assert rapport["publication_effectuee"] is False


@pytest.mark.parametrize("mutation,raison", [
    (lambda x: x["annuaire"]["categories_export"].update({"SI": 1}),
     "L'Annuaire ne correspond pas"),
    (lambda x: x["resolution_organisation"].update({"restantes_apres_croisement": 10}),
     "hiérarchiques"),
    (lambda x: x["resolution_territoires"].update({"absentes_sans_trace_historique": 3}),
     "Raccordement"),
    (lambda x: x["manifest_annuaire"].update({"sha256_export": "non-empreinte"}),
     "Empreinte"),
    (lambda x: x["manifest_territoires"].update({"nombre_territoires": 1}),
     "Manifeste territorial"),
])
def test_la_chaine_refuse_un_decalage_structurel(mutation, raison):
    exemple = copy.deepcopy(charger())
    mutation(exemple)
    with pytest.raises(ValueError, match=raison):
        verifier(exemple)


def test_la_procedure_ne_publie_jamais_sans_ordre_explicite():
    chemin = RACINE / ".github/workflows/preparer-proposition-referentiel.yml"
    texte = chemin.read_text(encoding="utf-8")
    assert "  workflow_dispatch:" in texte
    assert "default: false" in texte
    assert 'cron: "47 5 * * *"' in texte
    assert "  push:" not in texte
    assert "persist-credentials: false" in texte
    assert "cancel-in-progress: false" in texte
    assert "if: ${{ github.event_name != 'schedule' && !inputs.publier }}" in texte
    assert "if: ${{ github.event_name == 'schedule' || inputs.publier }}" in texte
    assert "scripts/publier_mise_a_jour_institutionnelle.py --source referentiel --publier" in texte
    assert "git push" not in texte


def test_importations_liees_executees_dans_un_ordre_fixe():
    texte = (RACINE / ".github/workflows/preparer-proposition-referentiel.yml").read_text(encoding="utf-8")
    noms = [
        "python scripts/ingerer_roae.py",
        "python scripts/verifier_variation_referentiel.py --source roae",
        "python scripts/ingerer_annuaire_local.py",
        "python scripts/verifier_variation_referentiel.py --source annuaire",
        "python scripts/ingerer_cog.py",
        "python scripts/verifier_variation_referentiel.py --source cog",
        "python scripts/actualiser_resume_referentiel.py --verifier",
        "python scripts/verifier_chaine_referentiel.py",
    ]
    indices = [texte.index(nom) for nom in noms]
    assert indices == sorted(indices)
