"""Archives BeauAMP : attribution, intégrité et sélection de fichiers autorisés."""
from datetime import date
import hashlib
import json

import pytest

from scripts.collecter_beauamp import (
    RefusFichier, collecter, selectionner, telecharger_fichier,
)


def ressource(jour="08-10-2026", contenu=b"acheteur;objet\nService;Etude\n"):
    return {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "title": f"beauamp-{jour}.csv",
        "format": "csv",
        "filesize": len(contenu),
        "last_modified": "2026-10-09",
        "url": "https://static.data.gouv.fr/resources/base-de-marches/20261009-093001/beauamp.csv",
    }


def test_selection_donnees_recentes_et_exclusion_des_sources_non_autorisees():
    recent = ressource()
    ancien = ressource("01-01-2025")
    hors_domaine = dict(ressource("09-10-2026"), url="https://localhost/donnees.csv")
    volumineux = dict(ressource("07-10-2026"), filesize=5_000_000)
    invalide = dict(ressource("33-10-2026"))
    liste = selectionner(
        [recent, ancien, hors_domaine, volumineux, invalide],
        instant=date(2026, 10, 9),
    )
    assert len(liste) == 1
    assert liste[0]["jour"] == "2026-10-08"


def test_archive_reelle_de_fichier_fictif_et_attribution(tmp_path):
    octets = b"acheteur;objet\nCommune;Mission scientifique\n"
    record = ressource(contenu=octets)
    sortie = collecter(
        tmp_path,
        obtenir_source=lambda: {"license": "cc-by-sa", "resources": [record]},
        obtenir_fichier=lambda fiche: octets,
        instant=date(2026, 10, 9),
    )
    assert sortie["fichiers_telecharges_et_verifies"] == 1
    path = tmp_path / "quotidiens" / "2026-10-08.csv"
    assert path.read_bytes() == octets
    manifeste = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifeste["producteur"] == "Adrien Deschamps"
    assert manifeste["licence"] == "cc-by-sa"
    assert manifeste["fichiers"][0]["sha256"] == hashlib.sha256(octets).hexdigest()
    assert manifeste["completude_historique"] is False
    assert sortie["couverture_integrale_de_tous_les_marches"] is False


def test_modification_des_octets_officiels_recree_une_archive_verified(tmp_path):
    ancien = b"acheteur;objet\nCommune;Premier\n"
    nouveau = b"acheteur;objet\nCommune;Nouveau\n"
    octets = [ancien, nouveau]
    for valeur in octets:
        collecter(
            tmp_path,
            obtenir_source=lambda x=valeur: {
                "license": "cc-by-sa-4.0", "resources": [ressource(contenu=x)]
            },
            obtenir_fichier=lambda fiche, x=valeur: x,
            instant=date(2026, 10, 9),
        )
    assert (tmp_path / "quotidiens" / "2026-10-08.csv").read_bytes() == nouveau


def test_inconnue_licence_stoppe_la_republication(tmp_path):
    with pytest.raises(RefusFichier, match="Licence"):
        collecter(tmp_path,
                  obtenir_source=lambda: {"license": "unknown",
                                          "resources": [ressource()]},
                  instant=date(2026, 10, 9))
    assert not (tmp_path / "manifest.json").exists()


def test_une_erreur_ne_detruit_pas_une_archive_existante(tmp_path):
    donnees = b"acheteur;objet\nService;Expert\n"
    collecter(
        tmp_path,
        obtenir_source=lambda: {"license": "cc-by-sa", "resources": [ressource(contenu=donnees)]},
        obtenir_fichier=lambda fiche: donnees,
        instant=date(2026, 10, 9),
    )
    with pytest.raises(RefusFichier, match="Aucun fichier"):
        collecter(
            tmp_path,
            obtenir_source=lambda: {"license": "cc-by-sa", "resources": [ressource(contenu=donnees)]},
            obtenir_fichier=lambda fiche: (_ for _ in ()).throw(OSError("panne")),
            instant=date(2026, 10, 9),
        )
    assert (tmp_path / "quotidiens" / "2026-10-08.csv").read_bytes() == donnees


def test_taille_declares_and_entete_verifies():
    item = selectionner([ressource()], instant=date(2026, 10, 9))[0]
    with pytest.raises(RefusFichier, match="Taille"):
        telecharger_fichier(item, lambda fiche: b"trop court")
    with pytest.raises(RefusFichier, match="CSV"):
        telecharger_fichier(item, lambda fiche: b"\x00" * fiche["octets_declares"])
