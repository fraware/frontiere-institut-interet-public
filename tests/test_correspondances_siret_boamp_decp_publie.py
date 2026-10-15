"""Verrouiller la filiation et les frontières d'interprétation du relevé figé.

Le résultat 17 avis / 16 SIRET / 2 avis avec un acheteur DECP est celui
d'une enquête bornée, et ne mesure pas la couverture des marchés publics.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "institutionnel" / "besoins_publics"
FICHIER = DOSSIER / "correspondances_siret_boamp_decp_17.json"
EMPREINTE = DOSSIER / "correspondances_siret_boamp_decp_17.sha256"


def test_le_registre_publie_est_identique_au_rapport_original():
    brut = FICHIER.read_bytes()
    texte = EMPREINTE.read_text(encoding="ascii")
    assert re.fullmatch(
        r"[a-f0-9]{64}  correspondances_siret_boamp_decp_17.json\n", texte)
    assert hashlib.sha256(brut).hexdigest() == texte[:64]
    assert texte[:64] == "6dbdd44379ddbc48f2d46f59ae410653613ca880a431a38b716d4a9f7ec544d7"


def test_population_et_preuves_du_releve_sont_coherentes():
    releve = json.loads(FICHIER.read_text(encoding="utf-8"))
    obs = releve["observations"]
    assert releve["version"] == "correspondances-siret-boamp-decp-17-v1"
    assert releve["population"] == "17_avis_boamp_d_un_tirage_independant_non_representatif"
    assert releve["nombre_avis"] == len(obs) == 17
    assert len({o["avis_boamp"] for o in obs}) == 17
    assert len({o["siret_acheteur_sans_schema_dans_avis"] for o in obs}) == releve["nombre_siret_boamp_distincts"] == 16
    assert sum(o["siret_etablissement_exact_dans_api"] for o in obs) == releve["nombre_avis_avec_etablissement_exact_api"] == 17
    assert sum(o["rapprochement_acheteur_documentaire"] for o in obs) == releve["nombre_avis_avec_siret_egal_a_un_acheteur_decp"] == 2
    assert releve["aucune_identite_de_contrat_deduite"] is True
    assert releve["role_acheteur_juridiquement_etabli"] is False
    assert releve["siret_boamp_initialement_sans_schema"] is True
    assert releve["empreintes_sources"]["audit_boamp"] == (
        "3626f84ccf9a39ce6d8882f0d5f7463eb6bde860c90a26904a6992f5fed791e3")

    concordances = {}
    for o in obs:
        assert re.fullmatch(r"[0-9]{14}", o["siret_acheteur_sans_schema_dans_avis"])
        assert re.fullmatch(r"[0-9]{2}-[0-9]{2,8}", o["avis_boamp"])
        assert o["identite_contrat_decp_demonstree"] is False
        assert o["role_acheteur_juridiquement_confirme"] is False
        assert o["rapprochement_acheteur_documentaire"] == (
            o["siret_etablissement_exact_dans_api"]
            and o["marches_decp_identites_meme_siret"] > 0)
        for cle in ("sha256_reponse_boamp", "sha256_reponse_administrative"):
            assert re.fullmatch(r"[a-f0-9]{64}", o["preuves"][cle])
        if o["rapprochement_acheteur_documentaire"]:
            concordances[o["avis_boamp"]] = (
                o["siret_acheteur_sans_schema_dans_avis"],
                o["marches_decp_identites_meme_siret"])
    assert concordances == {
        "25-94670": ("21060027600013", 5),
        "26-62030": ("18002002600019", 1),
    }
