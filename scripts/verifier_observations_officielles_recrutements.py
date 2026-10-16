"""Valider les observations de pages officielles, sans requête réseau.

Contrôle du type de document et de la portée des conclusions uniquement :
les pages consultées n'ont pas été archivées avec une empreinte cryptographique.
Le validateur ne certifie pas le contenu ni la disponibilité actuelle des URLs.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit

CHEMIN = Path("evaluation/observations_officielles_recrutements_2026-10-15.json")
REFERENCES = {
    "2026-2344611", "2026-2398908", "DEF_04-00070536", "O032260213001234"
}
PRECOBOVE = {"2026-2344611", "2026-2398908"}
CSP = "choisirleservicepublic.gouv.fr"
TERRITORIAL = "www.emploi-territorial.fr"


class PreuveInadmissible(ValueError):
    pass


def verifier(condition: bool, raison: str) -> None:
    if not condition:
        raise PreuveInadmissible(raison)


def date_iso(texte: object) -> date:
    verifier(isinstance(texte, str) and len(texte) == 10, "Date inadmissible.")
    try:
        d = date.fromisoformat(texte)
    except (ValueError, TypeError) as exc:
        raise PreuveInadmissible("Date civile incorrecte.") from exc
    verifier(d.isoformat() == texte and d <= date(2026, 10, 15),
             "Date future ou format non canonique.")
    return d


def url_officielle(texte: object, reference: str) -> bool:
    if not isinstance(texte, str):
        return False
    p = urlsplit(texte)
    if p.scheme != "https" or p.username or p.password or p.port or p.query or p.fragment:
        return False
    if reference == "O032260213001234":
        return p.hostname == TERRITORIAL and p.path == (
            "/offre/o032260213001234-chef-fe-projets-informatiques")
    return p.hostname == CSP and p.path.startswith("/offre-emploi/") and (
        reference in p.path)


def verifier_rapport(r: object) -> dict:
    verifier(isinstance(r, dict) and r.get("version") ==
             "frontiere-observations-officielles-enquetes-v1" and
             r.get("date_observation") == "2026-10-15" and
             r.get("preuves_web_capturees_sha256") is False and
             isinstance(r.get("observations"), list) and
             len(r["observations"]) == 4,
             "Périmètre des observations incompatible.")
    identites = set()
    offres = {}
    for doc in r["observations"]:
        verifier(isinstance(doc, dict), "Source documentaire non structurée.")
        ref = doc.get("reference")
        verifier(ref in REFERENCES and ref not in identites and
                 url_officielle(doc.get("url"), ref) and
                 doc.get("source_historique_archives_csp") in (
                     True, "non_verifiee_dans_ce_registre"),
                 "Source non officielle, répétée ou étrangère.")
        identites.add(ref)
        offres[ref] = doc
        verifier(isinstance(doc.get("institution"), str) and
                 doc["institution"].strip(), "Institution manquante.")
        if ref in PRECOBOVE:
            verifier(doc.get("projet_declare") == "PRECOBOVE" and
                     doc.get("institution") == "École nationale vétérinaire de Toulouse" and
                     len(doc.get("missions_declarees", [])) >= 2 and
                     len(doc.get("qualifications_declarees", [])) >= 3,
                     "Le projet ou ses qualifications ont été modifiés.")
            date_iso(doc.get("date_limite_candidature"))
            # Une prise de poste est annoncée. Le fait ne certifie pas la
            # présence d'un salarié à cette date ; la date actuelle est exclue.
            s = doc.get("prise_de_poste_annoncee")
            verifier(s in ("2026-09-01", "2026-10-15"),
                     "Date de poste annoncé incohérente.")
        if ref == "DEF_04-00070536":
            verifier(doc.get("condition_exercice_annoncee") ==
                     "demande d'habilitation Secret prévue" and
                     doc.get("prise_de_poste_annoncee") == "2026-10-01",
                     "Obligations d'accès modifiées ou déduites.")
        if ref == "O032260213001234":
            verifier(doc.get("information_affichee") ==
                     "délai de candidature expiré et annonce dépubliée" and
                     doc.get("date_publication_affichee") == "2026-02-13",
                     "Statut documentaire territorial incompatible.")
    verifier(identites == REFERENCES, "Référence d'offre absente.")
    verifier(offres["2026-2344611"]["date_limite_candidature"] == "2026-08-09" and
             offres["2026-2398908"]["date_limite_candidature"] == "2026-09-25" and
             offres["2026-2344611"]["contrat_annonce"] == "18 mois" and
             offres["2026-2398908"]["contrat_annonce"] ==
             "12 mois renouvelable de 6 à 12 mois",
             "Les deux annonces PRECOBOVE ont été amalgamées.")
    liens = r.get("recoupements")
    verifier(isinstance(liens, list) and len(liens) == 1 and
             liens[0].get("type") == "meme_acronyme_projet_dans_deux_annonces" and
             set(liens[0].get("references", [])) == PRECOBOVE and
             liens[0].get("lien_juridique_entre_postes") == "non_etabli" and
             liens[0].get("republication_du_meme_poste") == "non_etablie" and
             liens[0].get("recrutement_anterieur_echoue") == "non_etabli" and
             liens[0].get("nombre_de_postes_distincts") == "inconnu",
             "Relation entre annonces présentée comme prouvée.")
    anr = r.get("contexte_financement", {})
    verifier(anr.get("organisme") == "Agence nationale de la recherche" and
             anr.get("reference_projet") == "PrEcoBovE" and
             anr.get("url") ==
             "https://anr.fr/fileadmin/aap/2026/selection/aap-flashpox-2026-selection.pdf" and
             anr.get("etat_paiement") == "non_etabli" and
             "condition" in anr.get("limite", ""),
             "Une sélection à l'ANR a été transformée en versement prouvé.")
    etats = r.get("etats_non_etablis", {})
    verifier(etats == {
        "recrutements_pourvus": 0,
        "deficits_de_capacite_confirmes": 0,
        "insuffisance_dispositifs_existants_confirmee": 0,
        "organisme_contacte_dans_cette_enquete": False
    }, "Conclusion ou contact institutionnel non justifié.")
    return {
        "sources_officielles_referencees": 4,
        "annonces_preco_bove_distinctes": 2,
        "deux_echeances_de_candidature_documentees": True,
        "deficits_de_capacite_confirmes": 0,
        "pages_archives_avec_sha256": False,
        "recrutements_pourvus_confirmes": 0
    }


if __name__ == "__main__":
    import argparse

    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--racine", type=Path, default=Path(__file__).resolve().parents[1])
    args = a.parse_args()
    rapport = json.loads((args.racine / CHEMIN).read_text(encoding="utf-8"))
    print(json.dumps(verifier_rapport(rapport), ensure_ascii=False, sort_keys=True))
