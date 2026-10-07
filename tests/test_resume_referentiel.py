from scripts.actualiser_resume_referentiel import bloc_cog, bloc_readme, remplacer_bloc


def donnees():
    roae = {"nombre_entites_canoniques": 7905, "nombre_relations_hierarchiques": 8073}
    local = {
        "nombre_enregistrements_export_complet": 93782,
        "nombre_entites_canoniques": 85877,
        "nombre_relations_hierarchiques": 4155,
    }
    cog = {
        "nombre_territoires": 40345,
        "nombre_relations": 150421,
        "anomalies_relations": 0,
        "observe_le": "2026-10-07T12:06:44+00:00",
        "types_territoires": {"COM": 34875, "COMD": 2105, "CAN": 2293, "COMA": 471, "ARR": 333, "DEP": 101, "ARM": 45, "REG": 18, "COMER": 9, "COMER-COM": 95},
        "resolution_annuaire": {
            "resolues": 305447,
            "references_codes_insee": 305454,
            "absentes": 7,
            "absentes_courantes_expliquees_historiquement": 7,
            "absentes_sans_trace_historique": 0,
            "ambigues": 0,
            "entites_annuaire_avec_territoire": 85579,
            "taux_resolution": 0.999977,
            "taux_references_expliquees": 1.0,
        },
    }
    return roae, local, cog


def test_bloc_readme_repose_sur_les_statistiques_courantes_et_reste_lisible():
    roae, local, cog = donnees()
    bloc = bloc_readme(roae, local, cog)
    assert "7 905" in bloc
    assert "85 877" in bloc
    assert "305 447 / 305 454" in bloc
    assert "Référentiel de l’organisation administrative de l’État" in bloc
    assert "Entités SI" not in bloc
    assert "SL/SIL" not in bloc
    assert "snapshot" not in bloc


def test_bloc_cog_distingue_resolution_courante_et_explication_historique():
    _, _, cog = donnees()
    bloc = bloc_cog(cog)
    assert "305 447 références" in bloc
    assert "7 références restantes" in bloc
    assert "100,0 %" in bloc
    assert "unités territoriales actuelles" in bloc


def test_remplacer_bloc_preserve_le_reste_du_document():
    source = "avant\n<!-- D -->\nancien\n<!-- F -->\naprès\n"
    resultat = remplacer_bloc(source, "<!-- D -->", "<!-- F -->", "nouveau")
    assert resultat == "avant\n<!-- D -->\nnouveau\n<!-- F -->\naprès\n"
