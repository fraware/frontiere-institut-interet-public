"""Essais hors réseau de recherche fédérée BOAMP/DECP et de non-confusion des identités."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.indexer_commande_publique_sqlite import (
    IndexCommandeInvalide, construire, rechercher, bilan, verifier_boamp
)

SIRET = "21750001630066"
RID_AIFE = "db50f1f1-9fe5-4f9e-93dd-d273617d4a26"
RID_XML = "118544f1-b022-43d4-b8e0-3856f66a8b1d"
PAGE_DGFIP = ("https://www.data.gouv.fr/datasets/"
              "donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024")


def avis(ident="26-100001", *, titre="Plateforme quantique", etat="INITIAL"):
    return {
        "id": ident, "objet": titre, "acheteur": "Ville de Paris",
        "avis": f"https://www.boamp.fr/pages/avis/?q=idweb:{ident}",
        "catalogue_source": "https://boamp-datadila.opendatasoft.com/explore/dataset/boamp/",
        "categorie_marche": None, "contenu_integral_copie": False,
        "date_parution": "2026-10-14", "date_limite_reponse": "2026-11-15T12:00:00+00:00",
        "etat_avis": etat,
    }


def marche(*, objet="Fourniture quantique", mid="M-01"):
    return {
        "acheteur_siret": SIRET, "id_marche": mid, "objet": objet,
        "code_cpv": "73100000-3", "nature": "Marché",
        "date_notification": "2026-10-12",
        "date_publication_declaree": "2026-10-14",
        "montant_euros_ht_declare": 100000,
        "offres_recues_declarees": None, "marche_innovant_declare": None,
        "preuve_de_premiere_contribution": False,
        "besoin_encore_ouvert_demontre": False,
    }


def ecrire(racine: Path, *, avis_sources=None, xml_sources=None) -> None:
    b = racine / "institutionnel/besoins_publics"
    d = racine / "institutionnel/decp"
    b.mkdir(parents=True, exist_ok=True)
    d.mkdir(parents=True, exist_ok=True)
    ba = [avis(), avis("26-100002", titre="Informatique documentaire",
                      etat="RECTIFICATIF")] if avis_sources is None else avis_sources
    aife = {
        "version": "decp-fichier-json-v1", "source_catalogue": "aife_api_decp",
        "page_catalogue": "https://www.data.gouv.fr/datasets/api-decp",
        "ressource_id": RID_AIFE, "sha256_fichier_brut": "a" * 64,
        "releve_le": "2026-10-15T12:00:00+00:00",
        "extraits_plafonnes": False,
        "releves": {"marches_uniques_valides": 1},
        "marches_extraits": [marche()],
    }
    lots = [marche(objet="Fourniture quantique nouvelle"),
            marche(objet="Fourniture de capteurs", mid="M-02")]
    if xml_sources is not None:
        lots = xml_sources
    dgfip = {
        "version": "lot-decp-dgfip-xml-v1",
        "source_catalogue": "dgfip_pes_marche",
        "page_catalogue": PAGE_DGFIP,
        "controle_le": "2026-10-15T12:00:00+00:00",
        "fichiers": [{
            "id": RID_XML, "empreinte_sha256": "b" * 64,
            "extraits_plafonnes": False,
            "releves": {"marches_uniques_valides": len(lots)},
            "marches_extraits": lots,
        }],
    }
    (b / "annonces_boamp.json").write_text(
        json.dumps({"version": "avis-boamp-v1", "annonces": ba},
                   ensure_ascii=False), encoding="utf-8")
    (d / "sonde_aife_json.json").write_text(json.dumps(aife), encoding="utf-8")
    (d / "lot_dgfip_xml.json").write_text(json.dumps(dgfip), encoding="utf-8")


def test_recherche_federee_avec_variantes_sans_contrat_commun(tmp_path):
    root = tmp_path / "depot"
    ecrire(root)
    base = tmp_path / "commande.sqlite3"
    resultat = construire(root, base)
    assert resultat["avis_boamp"] == 2
    assert resultat["marches_identites"] == 2
    assert resultat["marches_variantes"] == 3
    assert resultat["marches_attestations"] == 3
    assert resultat["fichiers_decp"] == 2
    assert resultat["liaisons_boamp_decp_prouvees"] == 0
    assert bilan(base)["couverture_nationale_demontree"] is False

    trouve = rechercher(base, expression="quantique")
    assert trouve["resultats_totaux"] == 2
    assert {x["source"] for x in trouve["resultats"]} == {"boamp", "decp"}
    assert trouve["liens_contractuels_inferes"] == 0
    boamp = next(x for x in trouve["resultats"] if x["source"] == "boamp")
    decp = next(x for x in trouve["resultats"] if x["source"] == "decp")
    assert boamp["identifiant"] == "26-100001"
    assert boamp["etat_documentaire"] == "INITIAL"
    assert boamp["date_limite_annoncee"] == "2026-11-15T12:00:00+00:00"
    assert boamp["siret_acheteur"] is None
    assert decp["identifiant"] == SIRET + "/M-01"
    assert decp["versions_documentaires"] == 2
    assert decp["versions_correspondantes"] == 2
    assert decp["attestations"] == 1
    assert decp["nature_date"] == "notification_marche"
    assert decp["besoin_non_satisfait"] == "non_etabli"
    assert rechercher(base, siret=SIRET)["resultats_totaux"] == 2
    assert all(x["source"] == "decp" for x in rechercher(base, siret=SIRET)["resultats"])
    assert rechercher(base, identifiant="26-100002")["resultats"][0][
        "etat_documentaire"] == "RECTIFICATIF"
    assert rechercher(base, identifiant=SIRET + "/M-01")["resultats_totaux"] == 1
    assert rechercher(base, source="boamp", siret=SIRET)["resultats"] == []
    assert rechercher(base, expression="quantique", depuis="2026-10-13")[
        "resultats_totaux"] == 1


def test_pagination_dates_et_termes_litteraux(tmp_path):
    racine = tmp_path / "depot"
    ecrire(racine)
    base = tmp_path / "base.sqlite3"
    construire(racine, base)
    r = rechercher(base, expression="quantique", limite=1, decalage=1)
    assert r["resultats_totaux"] == 2
    assert len(r["resultats"]) == 1
    assert rechercher(base, expression='quantique" OR informatique')[
        "resultats_totaux"] == 0
    assert rechercher(base, expression="quantique", jusqua="2026-02-01")[
        "resultats_totaux"] == 0
    with pytest.raises(IndexCommandeInvalide):
        rechercher(base, expression="quantique", depuis="2026-02-30")
    with pytest.raises(IndexCommandeInvalide):
        rechercher(base, expression="quantique", depuis="2026-10-15",
                  jusqua="2026-10-14")
    with pytest.raises(IndexCommandeInvalide):
        rechercher(base, expression="quantique", limite=0)
    with pytest.raises(IndexCommandeInvalide):
        rechercher(base, expression="quantique", decalage=15001)
    with pytest.raises(IndexCommandeInvalide):
        rechercher(base, expression="quantique; DROP TABLE versions")
    with pytest.raises(IndexCommandeInvalide):
        rechercher(base, siret="SIRET_INCONNU")
    with pytest.raises(IndexCommandeInvalide):
        rechercher(base)


@pytest.mark.parametrize("champ,valeur", [
    ("id", "autre-id"),
    ("date_parution", "2026-02-30"),
    ("date_limite_reponse", "2026-02-30T18:00:00Z"),
    ("date_limite_reponse", "2026-11-01T13:00:00"),
    ("etat_avis", "ATTRIBUE"),
    ("contenu_integral_copie", True),
    ("categorie_marche", "autre"),
    ("avis", "https://autre-site.fr/pages/avis/?q=idweb:26-100001"),
    ("catalogue_source", "https://exemple.invalid"),
])
def test_entrees_boamp_ambigues_refusees(champ, valeur):
    a = avis()
    a[champ] = valeur
    with pytest.raises(IndexCommandeInvalide):
        verifier_boamp({"version": "avis-boamp-v1", "annonces": [a]})


def test_separateurs_lignes_source_preserves_par_empreinte(tmp_path):
    original = avis(titre="Étude scientifique\\nLot 1 et lot 2")
    assert verifier_boamp({"version": "avis-boamp-v1", "annonces": [original]})
    racine = tmp_path / "depot"
    ecrire(racine, avis_sources=[original])
    base = tmp_path / "index.sqlite3"
    construire(racine, base)
    x = rechercher(base, identifiant=original["id"])["resultats"][0]
    assert x["titre"] == "Étude scientifique Lot 1 et lot 2"
    assert x["empreinte_preuve"] == hashlib.sha256(json.dumps(
        original, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def test_identifiant_boamp_duplique_refuse():
    with pytest.raises(IndexCommandeInvalide, match="répété"):
        verifier_boamp({"version": "avis-boamp-v1", "annonces": [avis(), avis()]})


def test_corruption_ne_remplace_pas_la_base_existante(tmp_path):
    root = tmp_path / "depot"
    ecrire(root)
    base = tmp_path / "index.sqlite3"
    construire(root, base)
    ancien = hashlib.sha256(base.read_bytes()).hexdigest()
    ecrire(root, avis_sources=[avis(etat="ATTRIBUE")])
    with pytest.raises(IndexCommandeInvalide):
        construire(root, base, remplacer=True)
    assert hashlib.sha256(base.read_bytes()).hexdigest() == ancien
    assert rechercher(base, expression="quantique")["resultats_totaux"] == 2
    with pytest.raises(IndexCommandeInvalide):
        construire(root, root / "index.sqlite3")


def test_dgfip_incomplete_ou_identites_reduites_refusees(tmp_path):
    root = tmp_path / "depot"
    ecrire(root)
    dg = root / "institutionnel/decp/lot_dgfip_xml.json"
    j = json.loads(dg.read_text())
    j["fichiers"][0]["extraits_plafonnes"] = True
    dg.write_text(json.dumps(j), encoding="utf-8")
    with pytest.raises(IndexCommandeInvalide):
        construire(root, tmp_path / "base.sqlite3")
    assert not (tmp_path / "base.sqlite3").exists()
