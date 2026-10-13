"""Essais sans réseau de la vérification administrative non exhaustive."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.verifier_identifiants_acheteurs_api_entreprises import (
    VerificationInvalide, classer_reponse, charger_identifiants,
    luhn, verifier,
)

NUMEROS = (
    "48262252900022", "11000201100044", "13002269200011",
    "21060027600013", "12006401900074", "21973360700010",
    "13001779100018", "26950015300011", "51018963200035",
    "18009214000037", "22080004900011", "20007188400106",
    "26630746100019", "26750045201928", "18002002600019",
    "19761904200017",
)


def audit_fictif(tmp_path):
    avis = []
    for i in range(36):
        numero = NUMEROS[i % 16] if i < 17 else None
        avis.append({
            "avis": f"26-{10000+i}",
            "statut_identite": (
                "identifiant_14_chiffres_sans_schema" if numero
                else "aucune_identite_acheteur_qualifiable"
            ),
            "identite_acheteur": numero,
            "champ_identite": "/results/0/donnees/EFORMS/acheteur"
                              if numero else None,
            "sha256_reponse_http": "a" * 64,
        })
    fichier = tmp_path / "audit.json"
    fichier.write_text(json.dumps({
        "version": "audit-acheteurs-36-boamp-v1",
        "avis": avis,
        "nombre_avis_tires": 36,
        "nombre_avis_distincts": 36,
        "identifiants_14_chiffres_non_qualifies": 17,
        "verification_registre_sirene_effectuee": False,
        "correspondances_contractuelles_verifiees": 0,
    }), encoding="utf-8")
    return fichier


def reponse(numero, *, exact=True, aucune=False, correspondants=True):
    if aucune:
        return b'{"results":[],"total_results":0}'
    unite = {"siren": numero[:9], "nom_complet": "ORGANISME PUBLIC",
             "matching_etablissements": [
                 {"siret": numero if exact else numero[:9] + "99999"}
             ] if correspondants else []}
    return json.dumps({"results": [unite], "total_results": 1}).encode("utf-8")


def test_nombre_distinct_et_occurrences_sans_dedoublement(tmp_path):
    source = audit_fictif(tmp_path)
    _, numeros, preuves = charger_identifiants(source)
    assert len(numeros) == 16
    assert preuves["observations"] == 17
    assert len(preuves["occurrences_par_numero"][NUMEROS[0]]) == 2
    assert all(luhn(x) for x in numeros)
    assert not luhn("12345678901234")


def test_exact_matching_etablissements_est_seul_positif():
    numero = NUMEROS[0]
    positif = classer_reponse(numero, reponse(numero))
    assert positif["classe"] == "siret_exact_retourne_par_api_publique"
    assert positif["siret_exact_dans_etablissement"] is True
    assert positif["chemin_siret"] == "/results/0/matching_etablissements/0/siret"
    assert positif["existence_sirene_exhaustivement_verifiee"] is False
    assert positif["rattachement_acheteur_avis_confirme"] is False
    assert positif["identite_contractuelle_confirmee"] is False


def test_siege_exact_atteste_aussi_un_etablissement():
    numero = NUMEROS[1]
    original = {"results": [{"siren": numero[:9], "siege": {
        "siret": numero
    }}], "total_results": 1}
    resultat = classer_reponse(numero, json.dumps(original).encode())
    assert resultat["chemin_siret"] == "/results/0/siege/siret"


def test_siren_seul_natteste_pas_un_siret():
    numero = NUMEROS[0]
    incertain = classer_reponse(numero, reponse(numero, exact=False))
    assert incertain["classe"] == "unite_legale_associee_etablissement_non_atteste"
    assert incertain["siret_exact_dans_etablissement"] is False


def test_absence_api_non_exhaustive_nest_pas_inexistence():
    resultat = classer_reponse(NUMEROS[0], reponse(NUMEROS[0], aucune=True))
    assert resultat["classe"] == "non_retrouve_dans_api_non_exhaustive"
    assert resultat["existence_sirene_exhaustivement_verifiee"] is False


def test_reponse_dun_autre_siren_natteste_pas_identite():
    numero = NUMEROS[0]
    objet = json.dumps({"results": [{
        "siren": "999999999",
        "matching_etablissements": [{"siret": numero}],
    }], "total_results": 1}).encode()
    resultat = classer_reponse(numero, objet)
    assert resultat["classe"] == "reponse_sans_identite_exacte"
    assert resultat["siret_exact_dans_etablissement"] is False


@pytest.mark.parametrize("contenu", [
    b"non-json",
    b'{"results": [], "total_results": 1}',
    b'{"results": [], "total_results": "0"}',
    b'{"results": [{"siren": 111}], "total_results": 1}',
    b'{"results": [{"siren": "120064019", "matching_etablissements": {}}], "total_results": 1}',
])
def test_schema_incompatible_refuse(contenu):
    with pytest.raises(VerificationInvalide):
        classer_reponse(NUMEROS[0], contenu)


def test_archivage_atome_et_provenance(tmp_path):
    audit = audit_fictif(tmp_path)
    appels = []
    attente = []
    def obtenir(url):
        numero = parse_qs(urlparse(url).query)["q"][0]
        appels.append(numero)
        return reponse(numero, aucune=numero == NUMEROS[0])

    destination = tmp_path / "resultats"
    resultat = verifier(
        audit, destination, obtenir=obtenir, pause=attente.append,
        instant=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    assert len(appels) == 16
    assert len(attente) == 15
    assert all(d == 1.25 for d in attente)
    assert resultat["nombre_occurrences_identifiants"] == 17
    assert resultat["nombre_identifiants_distincts"] == 16
    assert resultat["contrats_juridiquement_identifies"] == 0
    assert resultat["rattachements_acheteurs_verifies"] == 0
    assert resultat["identites_etablissements_mentionnees_explicitement"] == 15
    for identite in resultat["identifiants"]:
        raw = (destination / identite["fichier_reponse"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == identite["sha256_reponse"]
    assert (destination / "rapport.json").is_file()
    with pytest.raises(VerificationInvalide, match="écraser"):
        verifier(audit, destination, obtenir=obtenir, pause=lambda _: None)


def test_erreur_reseau_interrompt_sans_publier_de_rapport(tmp_path):
    audit = audit_fictif(tmp_path)
    compteur = 0
    def obtenir(url):
        nonlocal compteur
        compteur += 1
        if compteur == 3:
            raise VerificationInvalide("Simuler API indisponible")
        return reponse(parse_qs(urlparse(url).query)["q"][0])

    destination = tmp_path / "resultats"
    with pytest.raises(VerificationInvalide):
        verifier(audit, destination, obtenir=obtenir, pause=lambda _: None)
    assert not destination.exists()


def test_registre_mute_ou_malforme_refuse(tmp_path):
    chemin = audit_fictif(tmp_path)
    j = json.loads(chemin.read_text())
    j["avis"][0]["statut_identite"] = "siret_explicitement_qualifie_dans_avis"
    chemin.write_text(json.dumps(j))
    with pytest.raises(VerificationInvalide):
        charger_identifiants(chemin)
