"""Essais hors réseau pour la collecte SCDL des délibérations publiques."""
import hashlib
import json

import pytest

from scripts.moissonner_deliberations_publiques import (
    CATALOGUE, MAX_OCTETS_CSV, MAX_OCTETS_META, CollecteInvalide,
    adresse_autorisee, collecter, extraire_csv, reference_document,
    requete, selectionner_datasets,
)

RESSOURCE = "https://static.data.gouv.fr/resources/deliberations-scdl-2026/2026-10-01/test.csv"
JEU = {"id": "jeu-deliberations-2026", "titre": "Délibérations communales",
       "licence": "lov2", "ressources": [{"id": "ressource-csv-001", "url": RESSOURCE}]}
CSV = (
    "COLL_NOM;COLL_SIRET;DELIB_ID;DELIB_DATE;DELIB_OBJET;DELIB_URL;PERSONNE\n"
    "Escalquens;21310145000010;D-2025-07;2025-02-13;"
    "Expérimentation d'un logiciel Delibia;"
    "https://www.escalquens.fr/documents/acte-2025-07.pdf;Nom Personnel\n"
    "Auzeville;21310035000010;D-2025-11;2025-06-18;"
    "Assistant juridique et intelligence artificielle;"
    "https://www.auzeville.fr/documents/acte-2025-11.pdf;Nom Personnel\n"
    "Commune témoin;21310255000011;D-2025-12;2025-06-19;"
    "Réfection de voirie;https://www.exemple.fr/voirie.pdf;Nom Personnel\n"
).encode("utf-8")


def enveloppe(jeux):
    return {"data": jeux, "page": 1, "page_size": 50, "next_page": None}


def jeux_meta():
    return [{
        "id": JEU["id"], "title": JEU["titre"], "license": "lov2",
        "private": False, "resources": [
            {"id": JEU["ressources"][0]["id"], "format": "CSV", "url": RESSOURCE}
        ]
    }]


def faux_charger(url, plafond):
    if url.startswith(CATALOGUE):
        assert plafond == MAX_OCTETS_META
        return json.dumps(enveloppe(jeux_meta())).encode()
    assert url == RESSOURCE and plafond == MAX_OCTETS_CSV
    return CSV


def test_urls_fixes_et_sans_redirections():
    assert adresse_autorisee(RESSOURCE)
    assert not adresse_autorisee("https://evil.example/resources/test.csv")
    assert not adresse_autorisee("http://static.data.gouv.fr/resources/test.csv")
    assert not adresse_autorisee("https://static.data.gouv.fr/secret.csv")
    assert not adresse_autorisee("https://static.data.gouv.fr.evil.test/resources/a.csv")
    assert not reference_document("http://exemple.fr/fichier.pdf")
    assert not reference_document("https://u:p@exemple.fr/fichier.pdf")
    assert reference_document("https://www.escalquens.fr/document.pdf")
    with pytest.raises(CollecteInvalide):
        requete("expression non autorisée")


def test_filtrage_licence_schema_et_domaine():
    candidats = jeux_meta() + [
        {"id": "jeu-prive-2026", "title": "Délibérations", "private": True,
         "license": "lov2", "resources": [{"id": "ressource-prive", "format": "csv", "url": RESSOURCE}]},
        {"id": "jeu-non-libre", "title": "Délibérations", "license": "inconnue",
         "resources": [{"id": "ressource-interdite", "format": "csv", "url": RESSOURCE}]},
        {"id": "jeu-non-officiel", "title": "Délibérations", "license": "lov2",
         "resources": [{"id": "ressource-ailleurs", "format": "csv", "url": "https://tiers.test/data.csv"}]},
    ]
    assert len(selectionner_datasets([enveloppe(candidats)])) == 1


def test_champs_et_protection_du_texte_libre():
    pistes, lus = extraire_csv(
        CSV, jeu=JEU, ressource=JEU["ressources"][0], instant="2026-10-14T02:00:00+00:00",
    )
    assert lus == 3 and len(pistes) == 2
    assert pistes[0]["deliberation_id"] == "D-2025-07"
    assert set(pistes[0]["mots_de_reperage"]) == {
        "experimentations_techniques", "expertise_juridique",
    }
    assert pistes[0]["sha256_csv"] == hashlib.sha256(CSV).hexdigest()
    assert "PERSONNE" not in json.dumps(pistes)
    assert "Nom Personnel" not in json.dumps(pistes)
    assert "Expérimentation" not in json.dumps(pistes)
    assert all(p["preuve_usage_verifiee"] is False for p in pistes)


def test_collecte_idempotente_et_pas_de_double_compte():
    vide = {"version": "pistes-deliberations-v1", "pistes": []}
    registre, bilan = collecter(
        ancien=vide, charger=faux_charger,
        instant="2026-10-14T02:00:00+00:00", patienter=lambda _: None,
    )
    assert bilan["nouvelles_pistes"] == 2
    assert bilan["lignes_scdl_examinees"] == 3
    assert bilan["pages_catalogue_reussies"] == 3
    assert len(registre["pistes"]) == 2
    identifiants = [p["identifiant"] for p in registre["pistes"]]
    nouveau, second = collecter(
        ancien=registre, charger=faux_charger,
        instant="2026-10-15T02:00:00+00:00", patienter=lambda _: None,
    )
    assert [p["identifiant"] for p in nouveau["pistes"]] == identifiants
    assert second["nouvelles_pistes"] == 0
    assert [p["observe_pour_la_premiere_fois"] for p in nouveau["pistes"]] == [
        "2026-10-14T02:00:00+00:00"
    ] * 2


def test_echec_partiel_preserve_historique():
    ancien, _ = collecter(
        ancien={"version": "pistes-deliberations-v1", "pistes": []},
        charger=faux_charger, instant="2026-10-14T02:00:00+00:00",
        patienter=lambda _: None,
    )

    def charger_en_panne(url, plafond):
        if url.startswith(CATALOGUE):
            return faux_charger(url, plafond)
        raise TimeoutError("réseau indisponible")

    resultat, etat = collecter(
        ancien=ancien, charger=charger_en_panne, instant="2026-10-15T02:00:00+00:00",
        patienter=lambda _: None,
    )
    assert resultat == ancien
    assert etat["ressources_csv_telechargees"] == 0
    assert etat["pistes_conservees"] == 2
    assert etat["echecs"][0]["type"] == "csv"


def test_echec_total_refuse_effacement():
    def panne(_url, _plafond):
        raise TimeoutError()

    with pytest.raises(CollecteInvalide, match="Aucune page"):
        collecter(
            ancien={"version": "pistes-deliberations-v1", "pistes": []},
            charger=panne, instant="2026-10-14T02:00:00+00:00",
            patienter=lambda _: None,
        )


def test_refuse_csv_sans_schema():
    with pytest.raises(CollecteInvalide, match="SCDL"):
        extraire_csv(b"titre;description\n1;2\n", jeu=JEU,
                    ressource=JEU["ressources"][0], instant="2026-10-14T02:00:00+00:00")


def test_dates_non_canoniques_et_siret_invalides_ignores():
    mauvais = (
        "COLL_SIRET;DELIB_ID;DELIB_DATE;DELIB_OBJET\n"
        "X;A;2025-02-13;Intelligence artificielle\n"
        "21310255000011;B;13/02/2025;Intelligence artificielle\n"
    ).encode()
    candidats, lus = extraire_csv(mauvais, jeu=JEU, ressource=JEU["ressources"][0],
                                 instant="2026-10-14T02:00:00+00:00")
    assert lus == 2 and candidats == []
