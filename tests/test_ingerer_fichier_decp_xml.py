"""Vérifications hors réseau des documents XML de la commande publique."""
import json
from pathlib import Path
import pytest

from scripts.ingerer_fichier_decp_xml import (
    XMLDECPInvalide, analyser_fichier, normaliser_xml,
)
from xml.etree import ElementTree as ET

RID = "118544f1-b022-43d4-b8e0-3856f66a8b1d"


def echantillon(namespace="", autre=False):
    n = f' xmlns="{namespace}"' if namespace else ""
    second = (
        '<marche><id>M-2</id><acheteur><id>21750001630066</id></acheteur>'
        '<objet>Appui informatique</objet><codeCPV>72000000-5</codeCPV>'
        '<montant>100.35</montant><dateNotification>2026-09-30</dateNotification>'
        '</marche>'
    ) if autre else ""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<marches{n}>
 <marche>
   <id>M-1</id><acheteur><id>21750001630066</id></acheteur>
   <nature>Marché</nature><objet>Étude sur les matériaux</objet>
   <codeCPV>73100000-3</codeCPV><montant>12500.25</montant>
   <dateNotification>2026-10-10</dateNotification>
   <datePublicationDonnees>2026-10-12</datePublicationDonnees>
   <offresRecues>2</offresRecues><marcheInnovant>oui</marcheInnovant>
   <titulaires><titulaire><id>99999999999999</id></titulaire></titulaires>
 </marche>
 {second}
 <contrat-concession><id>C-1</id><objet>Concession distincte</objet></contrat-concession>
</marches>'''


@pytest.mark.parametrize("uri", ["", "urn:commande:publique"])
def test_xml_marche_et_concession_distingues(uri, tmp_path):
    fichier = tmp_path / "marches.xml"
    fichier.write_text(echantillon(uri, autre=True), encoding="utf-8")
    bilan = analyser_fichier(fichier, source_id="dgfip_pes_marche", ressource_id=RID)
    assert bilan["releves"]["notices_lues"] == 2
    assert bilan["releves"]["objets_documentaires_lus"] == 3
    assert bilan["releves"]["concessions_non_normalisees"] == 1
    assert bilan["releves"]["marches_uniques_valides"] == 2
    assert len(bilan["marches_extraits"]) == 2
    assert bilan["marches_extraits"][0]["marche_innovant_declare"] is True
    assert bilan["marches_extraits"][0]["montant_euros_ht_declare"] == 12500.25
    assert bilan["rejets_par_categorie"] == {}
    assert bilan["categories_cpv_prefixe_2"] == {"72": 1, "73": 1}
    assert bilan["correspondances_boamp_verifiees"] == 0


def test_exemple_officiel_avec_meme_identite_compte_comme_doublon(tmp_path):
    """L'exemple XML officiel contient deux marchés de même identité."""
    original = echantillon()
    premier = original.split("<marche>")[1].split("</marche>")[0]
    original = original.replace("</marche>", "</marche>", 1).replace(
        "</marche>\n ", "</marche>\n <marche>" + premier + "</marche>\n ", 1
    )
    fichier = tmp_path / "deux.xml"
    fichier.write_text(original, encoding="utf-8")
    bilan = analyser_fichier(fichier, source_id="dgfip_pes_marche", ressource_id=RID)
    assert bilan["releves"]["doublons_exacts_dans_fichier"] == 1
    assert bilan["releves"]["marches_uniques_valides"] == 1


@pytest.mark.parametrize("xml", [
    '<!DOCTYPE marches [<!ENTITY cible "contenu">]><marches><marche>&cible;</marche></marches>',
    '<marches><marche><id>M</id></marches>',
    '<autre><marche/></autre>',
])
def test_document_inadmissible_est_refuse(xml, tmp_path):
    fichier = tmp_path / "invalid.xml"
    fichier.write_text(xml, encoding="utf-8")
    with pytest.raises(XMLDECPInvalide):
        analyser_fichier(fichier, source_id="dgfip_pes_marche", ressource_id=RID)


def test_notice_incomplete_est_comptee_sans_inventer_des_identifiants(tmp_path):
    xml = echantillon().replace("<id>M-1</id>", "<id></id>")
    fichier = tmp_path / "incomplete.xml"
    fichier.write_text(xml, encoding="utf-8")
    bilan = analyser_fichier(fichier, source_id="dgfip_pes_marche", ressource_id=RID)
    assert bilan["releves"]["notices_lues"] == 1
    assert bilan["releves"]["notices_rejetees"] == 1
    assert bilan["releves"].get("marches_uniques_valides", 0) == 0
    assert bilan["rejets_par_categorie"]


def test_montant_invalide_rejete_comme_notice(tmp_path):
    fichier = tmp_path / "invalide.xml"
    fichier.write_text(echantillon().replace("<montant>12500.25</montant>",
                                            "<montant>inf</montant>"), encoding="utf-8")
    bilan = analyser_fichier(fichier, source_id="dgfip_pes_marche", ressource_id=RID)
    assert bilan["releves"]["notices_rejetees"] == 1


def test_depassement_du_plafond_de_retenue_ne_falsifie_pas_le_compte(tmp_path):
    fichier = tmp_path / "marches.xml"
    fichier.write_text(echantillon(autre=True), encoding="utf-8")
    bilan = analyser_fichier(fichier, source_id="dgfip_pes_marche",
                            ressource_id=RID, limite_extraits=1)
    assert bilan["extraits_plafonnes"] is True
    assert len(bilan["marches_extraits"]) == 1
    assert bilan["releves"]["marches_uniques_valides"] == 2
