"""Contrôler la provenance des affiliations sans inférer les partenaires SAPS–CPPE."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

RACINE = Path(__file__).resolve().parents[1]
AFFILIATIONS = RACINE / "institutionnel/programmes_scientifiques/affiliations_datsum_exact_2026_v1.json"
COMPARATEURS = RACINE / "institutionnel/programmes_scientifiques/comparateurs_saps_cppe_2026_v1.json"
HOTES = {"anr.fr", "www.imt-atlantique.fr", "www.marsouin.org", "app.inrae.fr", "www.inrae.fr"}


def test_identite_officielle_et_preuves_limitees():
    preuve = json.loads(AFFILIATIONS.read_text(encoding="utf-8"))
    comparateurs = json.loads(COMPARATEURS.read_text(encoding="utf-8"))
    fiches = {f["id"]: f for f in comparateurs["cas"]}
    assert preuve["version"] == 1
    assert preuve["examen_le"] == "2026-10-14"
    assert preuve["source_selection_projets"] == comparateurs["source_primaire"]
    assert {p["id"] for p in preuve["projets"]} == {"DATSUM", "EXACT"}
    for projet in preuve["projets"]:
        identifiant = projet["id"]
        assert projet["coordinateur_selection"] == fiches[identifiant]["coordinateur"]
        assert fiches[identifiant]["statut_selection"] == "selectionne"
        assert projet["preuves_specifiques_projet"] == ["selection_anr"]
        assert projet["statut_identification_partenaires"] == "non_etabli"
        assert len(projet["affiliations_publiques"]) >= 2
        assert "administrations_partenaires" in projet["non_etablis"]
        assert "etablissement_beneficiaire_de_l_aide" in projet["non_etablis"]
        assert "convention_individuelle" in projet["non_etablis"]
        for source in projet["affiliations_publiques"]:
            url = urlsplit(source["url"])
            assert url.scheme == "https"
            assert url.hostname in HOTES
            assert source["organisation"] and source["nature"] and source["element"]


def test_une_affiliation_ne_devient_jamais_un_partenaire_du_projet():
    preuve = json.loads(AFFILIATIONS.read_text(encoding="utf-8"))
    interdit = {"partenaire_administratif_du_projet", "beneficiaire_contractuel_du_projet"}
    for projet in preuve["projets"]:
        for source in projet["affiliations_publiques"]:
            assert source["nature"] not in interdit
        assert "usage_operationnel" in projet["non_etablis"]
