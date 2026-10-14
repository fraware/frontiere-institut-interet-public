"""Contrôles hors réseau des captures municipales : octets, dates et portée."""
import hashlib
import json

import pytest

from scripts.relever_pdfs_municipaux import (
    CIBLES, SourceInvalide, analyser_pdf, executer, verifier_sources,
)

PDF = b"%PDF-1.4\nTEST\n%%EOF\n"


def config():
    return {
        "version": "sources-pdf-communaux-v1",
        "sources": [
            {"id": ident, "url": url, "commune": ident, "type": "proces-verbal",
             "repere": "point 3", "mots": ["delibia", "service juridique"]}
            for ident, url in CIBLES.items()
        ],
    }


def test_refuser_source_externe_et_injection_identite():
    sources = config()
    assert len(verifier_sources(sources)) == 3
    sources["sources"][0]["url"] = "https://tiers.example/PV.pdf"
    with pytest.raises(SourceInvalide, match="Identité"):
        verifier_sources(sources)


def test_refuser_liste_partielle_de_sources():
    sources = config()
    sources["sources"].pop()
    with pytest.raises(SourceInvalide, match="Effectif"):
        verifier_sources(sources)


def test_analyse_conserve_octets_sans_texte_libre():
    src = config()["sources"][0]
    fiche = analyser_pdf(PDF, src, instant="2026-10-14T00:00:00+00:00",
                        extracteur=lambda _: ["Le logiciel Delibia.",
                                              "La commune manque de service juridique."])
    assert fiche["sha256_octets_pdf"] == hashlib.sha256(PDF).hexdigest()
    assert fiche["pages"] == 2
    assert fiche["pages_contenant_termes"]["delibia"] == [1]
    assert fiche["pages_contenant_termes"]["service juridique"] == [2]
    assert fiche["utilisation_effective_prouvee"] is False
    assert "manque de service" not in json.dumps(fiche)
    assert fiche["octets_pdf_republies"] is False


def test_refuse_fichier_non_pdf_ou_tronque():
    src = config()["sources"][0]
    for donnees in (b"pas un pdf", b"%PDF-1.4 sans fin"):
        with pytest.raises(SourceInvalide):
            analyser_pdf(donnees, src, instant="2026-10-14T00:00:00+00:00",
                        extracteur=lambda _: ["test"])


def test_idempotence_et_echec_partiel_sans_effacement():
    initial = {"version": "observations-pdfs-municipaux-v1", "pieces": []}
    x = executer(config(), ancien=initial, telecharger=lambda _: PDF,
                 extracteur=lambda _: ["Delibia et le service juridique"],
                 instant="2026-10-14T00:00:00+00:00")
    assert x["pieces_avec_empreinte"] == 3
    assert x["pieces_nouvelles_ou_changees"] == 3
    y = executer(config(), ancien=x, telecharger=lambda _: PDF,
                 extracteur=lambda _: ["Delibia et le service juridique"],
                 instant="2026-10-15T00:00:00+00:00")
    assert y["pieces_nouvelles_ou_changees"] == 0
    assert y["pieces"][0]["observation_le"] == "2026-10-14T00:00:00+00:00"

    def indisponible(url):
        if "auzeville.fr" in url:
            raise TimeoutError("indisponible")
        return PDF
    z = executer(config(), ancien=x, telecharger=indisponible,
                 extracteur=lambda _: ["Delibia"],
                 instant="2026-10-16T00:00:00+00:00")
    assert z["pieces_avec_empreinte"] == 3
    assert z["echecs"] == [{"source_id": "auz-2025-06-18",
                            "motif": "TimeoutError"}]


def test_zero_pieces_ne_doit_pas_ecraser_le_releve():
    with pytest.raises(SourceInvalide, match="Aucune pièce"):
        executer(
            config(),
            ancien={"version": "observations-pdfs-municipaux-v1", "pieces": []},
            telecharger=lambda _: (_ for _ in ()).throw(TimeoutError()),
            extracteur=lambda _: ["inutilisé"],
            instant="2026-10-14T00:00:00+00:00",
        )


def test_le_proces_verbal_n_est_pas_confondu_avec_la_deliberation():
    urls = config()["sources"]
    pv = next(x for x in urls if x["id"] == "esc-2025-02-13-pv")
    dossier = next(x for x in urls if x["id"] == "esc-2025-02-13")
    assert pv["url"].endswith("/PV-CM-2025-02-13.pdf")
    assert dossier["url"] != pv["url"]
    assert len({x["id"] for x in urls}) == 3


def test_ne_confond_pas_presence_du_terme_et_action():
    fiche = analyser_pdf(
        PDF, config()["sources"][0],
        instant="2026-10-14T00:00:00+00:00",
        extracteur=lambda _: ["La consultation Delibia aura lieu dans six mois."],
    )
    assert fiche["pages_contenant_termes"]["delibia"] == [1]
    assert fiche["qualification"].endswith("sans_validation_usage")
    assert fiche["utilisation_effective_prouvee"] is False
