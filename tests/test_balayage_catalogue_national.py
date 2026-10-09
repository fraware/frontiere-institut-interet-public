"""Balayage général progressif : absence de perte, reprise et limites de preuve."""
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.balayer_catalogue_national import (
    ErreurCollecte, preparer_lot, publier_lot, reduire_notice,
    verifier_configuration,
)


def config():
    return {
        "origine": "https://www.data.gouv.fr/api/1/datasets/",
        "tri": "title",
        "taille_page": 10,
        "pages_par_execution": 3,
        "nombre_max_pages": 100,
        "conserver_uniquement_metadonnees": True,
        "secondes_entre_appels": 0,
    }


def fiche(i):
    return {
        "id": f"abcd{i:05d}",
        "title": f"Jeu public n° {i}",
        "license": "lov2",
        "organization": {"name": "Producteur d'essai"},
        "resources": [{"id": "ressource-fictive"}],
    }


def test_la_fiche_reduite_ne_contient_que_des_metadonnees():
    item = reduire_notice(fiche(1))
    assert item["titre"] == "Jeu public n° 1"
    assert item["nombre_ressources"] == 1
    assert "resources" not in item
    assert "description" not in item
    assert item["page"].startswith("https://www.data.gouv.fr/datasets/")


def test_reprise_au_point_suivant_et_reprise_finale(tmp_path: Path):
    appels = []
    def telecharger(url):
        p = int(parse_qs(urlparse(url).query)["page"][0])
        appels.append(p)
        assert "sort=title" in url
        if p == 4:
            return {"data": [fiche(40)], "total": 31}
        return {"data": [fiche(p * 100 + i) for i in range(10)], "total": 31}

    lot, etat = preparer_lot(
        config(), {"page_suivante": 2, "cycles_acheves": 0},
        charge=telecharger, patienter=lambda t: None,
    )
    assert appels == [2, 3, 4]
    assert etat["cycles_acheves"] == 1
    assert etat["page_suivante"] == 1
    assert etat["derniere_execution_est_un_tour_complet"] is True
    assert etat["exhaustivite_du_web"] is False
    publier_lot(lot, etat, tmp_path)
    assert (tmp_path / "balayage_pages/page_00002.jsonl").is_file()
    assert (tmp_path / "balayage_pages/page_00004.jsonl").is_file()


def test_un_echec_garde_la_page_a_reessayer():
    def telecharger(url):
        p = int(parse_qs(urlparse(url).query)["page"][0])
        if p == 3:
            raise OSError("Panne fictive")
        return {"data": [fiche(p * 100 + i) for i in range(10)]}
    lot, etat = preparer_lot(
        config(), {"page_suivante": 2, "cycles_acheves": 2},
        charge=telecharger, patienter=lambda t: None,
    )
    assert len(lot) == 1 and lot[0][0] == 2
    assert etat["page_suivante"] == 3
    assert etat["cycles_acheves"] == 2
    assert etat["erreurs"] == [{"page": 3, "motif": "OSError"}]


def test_aucune_page_reussie_interdit_tout_remplacement():
    with pytest.raises(ErreurCollecte, match="Aucune page valide"):
        preparer_lot(config(), {"page_suivante": 1},
                     charge=lambda url: (_ for _ in ()).throw(OSError("panne")),
                     patienter=lambda t: None)


def test_configuration_refuse_source_externe():
    c = config()
    c["origine"] = "https://hostile.example.org/"
    with pytest.raises(ErreurCollecte):
        verifier_configuration(c)



def test_importation_directe_du_script_charge_ses_validateurs():
    """Reproduire l'importation employée par python scripts/nom_du_fichier.py."""
    import subprocess
    import sys
    racine = Path(__file__).resolve().parents[1]
    code = (
        "from balayer_catalogue_national import reduire_notice; "
        "print(reduire_notice({'id':'abc12345','title':'Référentiel fictif',"
        "'organization':{'name':'Organisme de test'},'resources':[]})['id'])"
    )
    resultat = subprocess.run(
        [sys.executable, "-c", code],
        cwd=racine / "scripts", capture_output=True, text=True, check=False,
    )
    assert resultat.returncode == 0, resultat.stderr
    assert resultat.stdout.strip() == "abc12345"
