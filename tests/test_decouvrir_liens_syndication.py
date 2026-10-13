"""Essais du repérage sûr des flux RSS et Atom dans les pages publiques."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.decouvrir_liens_syndication import (
    DecouverteInvalide, analyser, executer, normaliser_lien, verifier_config,
)

HTML = """<html><head>
<link rel="alternate" type="application/rss+xml" href="/fr/rss/actus.xml" title="Actualités" />
<link rel="alternate" type="application/atom+xml" href="https://anr.fr/fr/atom.xml" />
<link rel="alternate" type="application/rss+xml" href="https://attacker.invalid/rss"/>
</head><body><a href="/fr/rss/appels.xml">Flux RSS des appels</a>
<a href="javascript:alert('x')">Flux RSS hostile</a>
<a href="https://autre.example/feed/">Flux RSS externe</a></body></html>"""


def config():
    return json.loads(
        Path("institutionnel/canaux_publics/sites_verifies_v1.json").read_text(encoding="utf-8")
    )


def test_liste_fermee_et_injection_de_domaine_refusee():
    c = config()
    verifier_config(c)
    c["pages"][0]["url"] = "https://attacker.invalid/"
    with pytest.raises(DecouverteInvalide):
        verifier_config(c)


def test_liens_rss_atom_memes_hotes_seulement():
    p = config()["pages"][0]
    liens = analyser(p, HTML)
    assert len(liens) == 3
    urls = {x["url"] for x in liens}
    assert "https://anr.fr/fr/rss/actus.xml" in urls
    assert "https://anr.fr/fr/atom.xml" in urls
    assert "https://anr.fr/fr/rss/appels.xml" in urls
    assert all(x["format_confirme"] is False and x["contenu_telecharge"] is False
               for x in liens)


def test_fragment_et_identifiants_nons_publics_refuses():
    p = config()["pages"][0]
    assert normaliser_lien(p["url"], "javascript:alert('x')", "anr.fr") is None
    assert normaliser_lien(p["url"], "https://127.0.0.1/rss", "anr.fr") is None
    assert normaliser_lien(p["url"], "/flux.xml#fragment", "anr.fr") == "https://anr.fr/flux.xml"


def test_releves_repetes_ne_multiplient_pas_les_candidats():
    p = config()["pages"][0]
    h = '<a href="/rss">Flux RSS</a><a href="/rss">Flux RSS</a>'
    assert len(analyser(p, h)) == 1


def test_echec_partiel_preserve_l_ancien_resultat():
    premier = executer(config(), {}, recuperer=lambda _: HTML,
                       instant="2026-10-13T02:00:00+00:00")
    assert premier["sites_reussis"] == 5
    assert premier["formats_des_candidats_verifies"] == 0
    original = next(s for s in premier["sites"] if s["id"] == "anr_flux")
    def reprise(site):
        if site["id"] == "anr_flux":
            raise TimeoutError("panne")
        return "<html></html>"
    suivant = executer(config(), premier, recuperer=reprise,
                       instant="2026-10-13T08:00:00+00:00")
    assert suivant["sites_reussis"] == 4
    assert len(suivant["sites_en_echec"]) == 1
    conserve = next(s for s in suivant["sites"] if s["id"] == "anr_flux")
    assert conserve == original
    assert suivant["couverture_nationale"] is False


def test_une_reponse_indisponible_ne_produit_pas_d_absence():
    with pytest.raises(DecouverteInvalide):
        executer(config(), {}, recuperer=lambda _: (_ for _ in ()).throw(TimeoutError()))


def test_aucun_lien_sur_une_page_n_est_pas_absence_de_canal():
    resultat = executer(config(), {}, recuperer=lambda _: "<html></html>")
    assert resultat["sites_reussis"] == 5
    assert resultat["liens_candidats_dans_les_sites_reussis"] == 0
    assert all(x["aucune_absence_de_flux_prouvee"] for x in resultat["sites"])



def test_page_de_presentation_ne_devient_pas_son_propre_flux():
    """Le lien interne vers la page de présentation n'est pas un nouveau flux."""
    page = config()["pages"][0]
    texte = (
        '<html><a href="/fr/flux-rss-et-reseaux-sociaux/">Flux RSS</a>'
        '<a href="/rss/?news">Actualités</a></html>'
    )
    lignes = analyser(page, texte)
    assert len(lignes) == 1
    assert lignes[0]["url"] == "https://anr.fr/rss/?news"


def test_page_ecologie_sans_candidat_veritable():
    page = next(x for x in config()["pages"] if x["id"] == "ecologie_flux")
    html = '<html><a href="/flux-rss">Flux RSS</a></html>'
    assert analyser(page, html) == []
