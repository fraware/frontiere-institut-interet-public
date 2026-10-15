"""Tests de reprise du calendrier TED historique, sans appel réseau."""
from datetime import date
import sqlite3

import pytest

from app.collecteur_ted_continu import StockageTED, _notice
from app.rattrapage_ted import dates_manquantes, passage, DEBUT_INITIAL


def collecteur_simule(appels):
    def obtenir(jour):
        appels.append(jour.isoformat())
        document = {
            "publication-number": f"{100 + jour.day}-{jour.year}",
            "publication-date": jour.isoformat(),
            "notice-title": {"fra": ["Étude technique"]},
            "buyer-name": {"fra": ["Établissement public"]},
            "buyer-country": "FRA",
        }
        return [_notice(document, jour)], 1
    return obtenir


def test_lacunes_et_reprise_sans_reinterroger_les_jours_valides(tmp_path):
    stockage = StockageTED(tmp_path / "ted.sqlite3")
    jours = date(2024, 1, 7)  # fin admissible : le 3 janvier
    appels = []
    premier = passage(
        stockage, debut=DEBUT_INITIAL, maximum=2,
        aujourd_hui=jours, obtenir=collecteur_simule(appels),
    )
    assert premier["jours_couverts_avant"] == 0
    assert premier["jours_tentes"] == 2
    assert premier["jours_importes"] == 2
    assert premier["jours_manquants_apres"] == 1
    assert premier["prochaine_date_manquante"] == "2024-01-03"
    second = passage(
        stockage, debut=DEBUT_INITIAL, maximum=2,
        aujourd_hui=jours, obtenir=collecteur_simule(appels),
    )
    assert second["jours_importes"] == 1
    assert second["jours_manquants_apres"] == 0
    assert second["etat"] == "complet"
    assert appels == ["2024-01-01", "2024-01-02", "2024-01-03"]
    dernier = passage(
        stockage, debut=DEBUT_INITIAL, maximum=2,
        aujourd_hui=jours, obtenir=collecteur_simule(appels),
    )
    assert dernier["jours_tentes"] == 0
    assert len(appels) == 3
    assert stockage.etat()["avis"] == 3


def test_echec_d_une_journee_n_est_pas_enregistre_comme_couverte(tmp_path):
    stockage = StockageTED(tmp_path / "ted.sqlite3")
    appels = []
    valide = collecteur_simule(appels)
    def instable(jour):
        if jour == date(2024, 1, 1):
            raise OSError("source inaccessible")
        return valide(jour)
    first = passage(
        stockage, debut=date(2024, 1, 1), maximum=3,
        aujourd_hui=date(2024, 1, 7), obtenir=instable,
    )
    assert first["jours_importes"] == 2
    assert first["jours_manquants_apres"] == 1
    assert first["etat"] == "partiel_avec_erreurs"
    assert first["erreurs"] == [{
        "jour": "2024-01-01", "erreur": "OSError",
    }]
    second = passage(
        stockage, debut=date(2024, 1, 1), maximum=3,
        aujourd_hui=date(2024, 1, 7), obtenir=valide,
    )
    assert second["jours_tentes"] == 1
    assert second["etat"] == "complet"


def test_jour_sans_publication_est_une_journee_couverte(tmp_path):
    stockage = StockageTED(tmp_path / "ted.sqlite3")
    resultat = passage(
        stockage, debut=date(2024, 1, 1), maximum=3,
        aujourd_hui=date(2024, 1, 6),
        obtenir=lambda _: ([], 1),
    )
    assert resultat["jours_importes"] == 2
    assert resultat["avis_importes"] == 0
    assert resultat["jours_manquants_apres"] == 0
    assert stockage.etat()["jours"] == 2


def test_une_periode_recente_ne_cree_pas_de_capture(tmp_path):
    stockage = StockageTED(tmp_path / "ted.sqlite3")
    bilan = passage(
        stockage, debut=date(2026, 10, 15), maximum=1,
        aujourd_hui=date(2026, 10, 15),
    )
    assert bilan["etat"] == "periode_non_encore_eligible"
    assert stockage.etat()["jours"] == 0


def test_dates_manquantes_bornees_et_validations(tmp_path):
    stockage = StockageTED(tmp_path / "ted.sqlite3")
    jours, couvertes, absentes = dates_manquantes(
        stockage, date(2024, 1, 1), date(2024, 1, 31), maximum=2,
    )
    assert len(jours) == 2
    assert couvertes == 0
    assert absentes == 31
    with pytest.raises(ValueError):
        dates_manquantes(
            stockage, date(2024, 1, 1), date(2024, 1, 31), maximum=13,
        )
    with pytest.raises(ValueError):
        dates_manquantes(
            stockage, date(2024, 2, 1), date(2024, 1, 31),
        )
