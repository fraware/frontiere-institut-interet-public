"""Essais sans réseau de l'avancement progressif des ressources XML DGFiP."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.sonder_lot_decp_dgfip import (
    LotDECPInvalide, choisir_ressources, executer,
)

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<marches><marche><id>APPEL-001</id><acheteur><id>21750001630066</id></acheteur>
<objet>Mission de recherche scientifique</objet><codeCPV>73100000-3</codeCPV>
<dateNotification>2026-10-01</dateNotification><montant>1234.50</montant>
</marche></marches>"""


def donnees(nombre=3):
    locaux, distants = [], []
    for numero in range(nombre):
        uid = f"{numero+1:08d}-eeee-4444-8888-1234567890ab"
        locaux.append({
            "id": uid, "format": "xml", "titre": f"decp-{numero}.xml",
            "taille_octets_declaree": len(XML),
            "modifie_le": f"2026-10-{numero+1:02d}T11:00:00+00:00",
        })
        distants.append({
            "id": uid, "format": "xml", "filesize": len(XML),
            "url": f"https://static.data.gouv.fr/resources/decp/{numero}.xml",
        })
    return (
        {"catalogues": [{"source_id": "dgfip_pes_marche",
                          "ressources_recentes": locaux}]},
        {"resources": distants},
    )


def _recevoir(meta, cible):
    cible.write_bytes(XML)
    return len(XML)


def test_prise_en_charge_de_plusieurs_fichiers_et_reprise_sans_doublons():
    local, distant = donnees(4)
    premier = executer(local, distant, {}, recuperer=_recevoir,
                       maximum=2, moment="2026-10-13T04:00:00+00:00")
    assert premier["nombre_fichiers_du_cycle"] == 2
    assert premier["nombre_fichiers_historises"] == 2
    assert all(x["releves"]["marches_uniques_valides"] == 1
               for x in premier["fichiers"])
    assert all(not x["besoin_encore_ouvert_demontre"]
               for x in premier["fichiers"])
    suivant = executer(local, distant, premier, recuperer=_recevoir,
                       maximum=2, moment="2026-10-13T05:00:00+00:00")
    assert suivant["nombre_fichiers_historises"] == 4
    assert len({x["id"] for x in suivant["fichiers"]}) == 4
    assert choisir_ressources(local, distant, suivant, maximum=2) == []
    assert executer(local, distant, suivant, recuperer=_recevoir) == suivant


def test_meme_identifiant_avec_nouvelles_metadonnees_est_repris():
    local, distant = donnees(1)
    first = executer(local, distant, {}, recuperer=_recevoir)
    updated = deepcopy(local)
    updated["catalogues"][0]["ressources_recentes"][0][
        "modifie_le"
    ] = "2026-10-13T06:00:00+00:00"
    second = executer(updated, distant, first, recuperer=_recevoir)
    assert second["nombre_fichiers_historises"] == 2
    assert second["fichiers"][0]["id"] == second["fichiers"][1]["id"]
    assert second["fichiers"][0]["empreinte_sha256"] == second["fichiers"][1]["empreinte_sha256"]


def test_echec_individuel_non_marque_comme_traite():
    local, distant = donnees(2)
    def recup(meta, cible):
        if meta["id"].startswith("00000001"):
            raise TimeoutError("simulateur")
        return _recevoir(meta, cible)
    result = executer(local, distant, {}, recuperer=recup)
    assert result["nombre_fichiers_du_cycle"] == 1
    assert result["echecs_du_dernier_cycle"][0]["type_erreur"] == "TimeoutError"
    assert result["nombre_fichiers_historises"] == 1
    assert len(choisir_ressources(local, distant, result)) == 1


def test_tous_les_echecs_preservent_le_curseur():
    local, distant = donnees(2)
    with pytest.raises(LotDECPInvalide):
        executer(local, distant, {},
                recuperer=lambda meta, path: (_ for _ in ()).throw(TimeoutError()))


def test_incoherence_de_taille_refusee_avant_telechargement():
    local, distant = donnees()
    distant["resources"][0]["filesize"] += 100
    selection = choisir_ressources(local, distant, {})
    assert len(selection) == 2
    assert not any(x["id"].startswith("00000001") for x in selection)


def test_url_exterieure_ne_provoque_aucune_requete():
    local, distant = donnees(1)
    distant["resources"][0]["url"] = "https://exemple.invalid/fichier.xml"
    with pytest.raises(ValueError):
        choisir_ressources(local, distant, {})


def test_document_xml_incorrect_ne_devient_pas_succes():
    local, distant = donnees(1)
    def mauvais(meta, cible):
        cible.write_bytes(b"\x00" * len(XML))
        return len(XML)
    with pytest.raises(LotDECPInvalide):
        executer(local, distant, {}, recuperer=mauvais)



def test_diagnostic_integralement_echoue_sans_contenu_distant():
    local, distant = donnees(1)
    secret = "objet privé présent dans une réponse arbitraire"
    def casse(meta, cible):
        raise ConnectionError(secret)
    with pytest.raises(LotDECPInvalide) as excinfo:
        executer(local, distant, {}, recuperer=casse)
    message = str(excinfo.value)
    assert secret not in message
    assert "ConnectionError" in message
    assert "curseur inchangé" in message



def test_toutes_les_notices_invalides_n_avancent_pas_le_curseur():
    local, distant = donnees(1)
    texte = XML.replace(b"21750001630066", b"IDENTIFIANTXXX")
    assert len(texte) == len(XML)
    def recup(meta, cible):
        cible.write_bytes(texte)
        return len(texte)
    with pytest.raises(LotDECPInvalide, match="Toutes"):
        executer(local, distant, {}, recuperer=recup)



def test_rejouer_un_fichier_historiquement_rejete_sans_effacer_sa_preuve():
    local, distant = donnees(2)
    premier = executer(local, distant, {}, recuperer=_recevoir)
    ancien = deepcopy(premier)
    ancien["fichiers"][0]["releves"] = {
        "notices_lues": 1, "notices_rejetees": 1,
    }
    ancien["fichiers"][0]["marches_extraits"] = []
    ancien["fichiers"][0]["empreinte_sha256"] = "a" * 64
    original = deepcopy(ancien)
    assert len(choisir_ressources(local, distant, ancien)) == 1
    corrige = executer(
        local, distant, ancien, recuperer=_recevoir,
        moment="2026-10-13T09:00:00+00:00",
    )
    assert len(corrige["fichiers"]) == 2
    assert corrige["nombre_fichiers_historiques_rectifies"] == 1
    assert corrige["nombre_fichiers_du_cycle"] == 1
    assert len(corrige["rectifications_historiques"]) == 1
    rectificatif = corrige["rectifications_historiques"][0]
    assert rectificatif["empreinte_fichier_brut"] == "a" * 64
    assert rectificatif["statut"] == "remplace_par_releve_exploitable"
    assert corrige["fichiers"][1]["releves"]["marches_uniques_valides"] == 1
    assert ancien == original
    assert choisir_ressources(local, distant, corrige) == []



def test_relire_seulement_une_ressource_tronquee_sous_nouveau_plafond():
    local, distant = donnees(2)
    original = executer(local, distant, {}, recuperer=_recevoir)
    precedent = deepcopy(original)
    precedent["fichiers"][0]["extraits_plafonnes"] = True
    precedent["fichiers"][0]["marches_extraits"] = []
    selection = choisir_ressources(local, distant, precedent)
    assert len(selection) == 1
    assert selection[0]["id"] == precedent["fichiers"][0]["id"]
    suivant = executer(local, distant, precedent, recuperer=_recevoir,
                      moment="2026-10-13T09:00:00+00:00")
    assert suivant["nombre_fichiers_historiques_rectifies"] == 1
    assert len(suivant["fichiers"]) == 2
    assert len(suivant["rectifications_historiques"]) == 1
    rectification = suivant["rectifications_historiques"][0]
    assert rectification["cause"] == "extraits_tronques_par_plafond_initial"
    assert rectification["notices_detaillees_initialement"] == 0
    assert rectification["statut"] == "remplace_par_releve_exploitable"
    assert all(not x["extraits_plafonnes"] for x in suivant["fichiers"])
    assert choisir_ressources(local, distant, suivant) == []
    assert precedent["fichiers"][0]["extraits_plafonnes"] is True
