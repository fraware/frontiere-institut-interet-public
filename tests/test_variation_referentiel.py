from scripts.verifier_variation_referentiel import RegleVariation, evaluer_variations, extraire


def test_extraire_valeur_imbriquee():
    assert extraire({"a": {"b": 12}}, "a.b") == 12


def test_petites_variations_sont_acceptees():
    rapport = evaluer_variations(
        {"n": 10_000},
        {"n": 10_120},
        (RegleVariation("n", 0.03, 100),),
    )
    assert rapport["violations"] == []


def test_variation_structurelle_est_refusee():
    rapport = evaluer_variations(
        {"n": 10_000},
        {"n": 8_000},
        (RegleVariation("n", 0.03, 100),),
    )
    assert len(rapport["violations"]) == 1
    assert rapport["violations"][0]["delta"] == -2_000


def test_petit_delta_absolu_ne_declenche_pas_un_blocage():
    rapport = evaluer_variations(
        {"n": 20},
        {"n": 10},
        (RegleVariation("n", 0.03, 100),),
    )
    assert rapport["violations"] == []
