"""Vérifier des trajectoires publiques sans confondre passation et usage.

Seuls les écarts entre dates administratives du même épisode sont calculés.
Les dates manquantes de besoin initial et de première utilité restent inconnues.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


VERSION = "episodes-mobilisation-preuves-v1"
NATURES_SOURCES = {
    "avis_attribution_officiel", "avis_publicite_profil_acheteur",
    "annonce_demonstration", "registre_acte_officiel", "pdf_communal",
}
TYPES = {
    "publicite_dispositif", "choix_titulaire_declare",
    "conclusion_contrats_declaree", "publication_attribution",
    "demonstration_annoncee", "deliberation_convention", "publication_acte",
    "experimentation_declaree", "decision_poursuite",
    "utilisation_declaree_par_agent",
}
QUALITES = {
    "date_publication", "date_declaree_dans_avis",
    "annonce_non_confirmation_usage", "titre_et_date_registre",
    "retrospective_sans_date_precise", "decision_institutionnelle",
    "date_temoignage_ni_premier_usage",
}
PDF_SHA = re.compile(r"^[0-9a-f]{64}$")
SIREN = re.compile(r"^[0-9]{9}$")


class PreuveInvalide(ValueError):
    """Une entrée confond des preuves, des circuits ou des dates."""


def date_canonique(valeur: object, champ: str) -> date:
    if not isinstance(valeur, str):
        raise PreuveInvalide(f"{champ} : date obligatoire")
    try:
        d = date.fromisoformat(valeur)
    except ValueError as exc:
        raise PreuveInvalide(f"{champ} : date invalide") from exc
    if d.isoformat() != valeur:
        raise PreuveInvalide(f"{champ} : format ISO attendu")
    return d


def texte(ob: object, cle: str) -> str:
    valeur = ob.get(cle) if isinstance(ob, dict) else None
    if not isinstance(valeur, str) or not valeur.strip():
        raise PreuveInvalide(f"Champ obligatoire absent : {cle}")
    return valeur


def verifier_sources(sources: object, captures: dict) -> dict[str, dict]:
    if not isinstance(sources, list) or not sources:
        raise PreuveInvalide("Inventaire de sources absent")
    source_index: dict[str, dict] = {}
    relevés = captures.get("pieces")
    if captures.get("version") != "observations-pdfs-municipaux-v1" or not isinstance(relevés, list):
        raise PreuveInvalide("Relevé d'empreintes primaires invalide")
    empreintes = {f.get("id_source"): f for f in relevés if isinstance(f, dict)}
    for src in sources:
        sid = texte(src, "id")
        if sid in source_index:
            raise PreuveInvalide("Source dupliquée")
        if src.get("type") not in NATURES_SOURCES:
            raise PreuveInvalide("Nature de source inconnue")
        url = urlsplit(texte(src, "url"))
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise PreuveInvalide("Adresse documentaire incorrecte")
        if not isinstance(src.get("circuits"), list) or not src["circuits"]:
            raise PreuveInvalide("Circuits de preuve absents")
        if src["type"] == "pdf_communal":
            if src.get("lecture_octets_independante") is not True:
                raise PreuveInvalide("Pièce municipale sans relevé d'octets")
            sha = src.get("sha256_pdf")
            if not isinstance(sha, str) or not PDF_SHA.fullmatch(sha):
                raise PreuveInvalide("Empreinte de PDF invalide")
            observation = empreintes.get(texte(src, "capture_id"))
            if (not observation or observation.get("sha256_octets_pdf") != sha
                    or observation.get("url_source_officielle") != src["url"]
                    or observation.get("octets_pdf_republies") is not False):
                raise PreuveInvalide("PDF différent des octets réellement relevés")
            src = dict(src, nombre_pages_capturees=observation["pages"])
        elif src.get("lecture_octets_independante") is not False or src.get("sha256_pdf") is not None:
            raise PreuveInvalide("Empreinte ou téléchargement supposé sans preuve")
        source_index[sid] = src
    return source_index


def verifier_episode(episode: dict, sources: dict[str, dict]) -> dict:
    uid = texte(episode, "id")
    texte(episode, "nature")
    texte(episode, "organisme")
    texte(episode, "reference")
    siren = episode.get("fournisseur_siren_partage")
    if siren is not None and (not isinstance(siren, str) or not SIREN.fullmatch(siren)):
        raise PreuveInvalide("Identifiant légal de fournisseur incorrect")
    if episode.get("relation_contractuelle_avec_autres_episodes_etablie") is not False:
        raise PreuveInvalide("Une identité d'entreprise ne prouve pas une relation inter-circuits")
    if (episode.get("date_besoin_initial") is not None or
            episode.get("date_premiere_contribution_utile") is not None or
            episode.get("mesure_impact_independante") is not None):
        raise PreuveInvalide("Aucune date de besoin/utilité ni effet mesuré n'est établie dans ce corpus")
    events = episode.get("evenements")
    if not isinstance(events, list) or not events:
        raise PreuveInvalide("Événements de l'épisode absents")
    vus: set[str] = set()
    jours, ordre = {}, []
    types = Counter()
    for evt in events:
        eid = texte(evt, "id")
        if eid in vus:
            raise PreuveInvalide("Identifiant événementiel répété")
        vus.add(eid)
        kind = evt.get("type")
        if kind not in TYPES:
            raise PreuveInvalide("Type d'événement inconnu")
        src = sources.get(texte(evt, "source_id"))
        if src is None or uid not in src["circuits"]:
            raise PreuveInvalide("Source associée au mauvais circuit")
        precision = evt.get("precision")
        if precision == "jour":
            if evt.get("annee") is not None:
                raise PreuveInvalide("Année supplémentaire ambiguë")
            jour = date_canonique(evt.get("date"), "evenement.date")
        elif precision == "annee":
            annee = evt.get("annee")
            if evt.get("date") is not None or not isinstance(annee, str) or not re.fullmatch(r"20[0-9]{2}", annee):
                raise PreuveInvalide("Une année qualitative ne vaut pas une date exacte")
            jour = date(int(annee), 1, 1)
            if evt.get("qualite") != "retrospective_sans_date_precise":
                raise PreuveInvalide("Événement annuel interprété comme date précise")
        else:
            raise PreuveInvalide("Précision temporelle non reconnue")
        if evt.get("qualite") not in QUALITES:
            raise PreuveInvalide("Qualité de source non reconnue")
        page = evt.get("page_pdf")
        if src["type"] in {"pdf_communal", "avis_attribution_officiel"}:
            if type(page) is not int or page < 1:
                raise PreuveInvalide("Passage PDF sans page identifiée")
            maximum = src.get("nombre_pages_capturees")
            if maximum is not None and page > maximum:
                raise PreuveInvalide("Page absente du document original")
        elif page is not None:
            raise PreuveInvalide("Numéro de page inventé pour source non PDF")
        if kind == "utilisation_declaree_par_agent" and (
                evt.get("qualite") != "date_temoignage_ni_premier_usage"):
            raise PreuveInvalide("La date du témoignage ne vaut pas premier usage")
        ordre.append(jour)
        types[kind] += 1
        if precision == "jour":
            jours[eid] = jour
    if ordre != sorted(ordre):
        raise PreuveInvalide("Chronologie non ordonnée")
    if uid == "SICTIAM-SAD-2026":
        for code in ("CHOIX-TOMORRO", "CHOIX-AUTRES", "CONTRATS"):
            if code not in jours:
                raise PreuveInvalide("Chaîne de dates SICTIAM incomplète")
        date_contrat = jours["CONTRATS"]
        delais = {
            code: (date_contrat - jours[code]).days
            for code in ("CHOIX-TOMORRO", "CHOIX-AUTRES")
        }
        if any(n < 0 for n in delais.values()):
            raise PreuveInvalide("Choix de titulaire postérieur à la conclusion")
    else:
        delais = {}
    return {
        "id_episode": uid, "organisme": episode["organisme"],
        "nombre_evenements": len(events),
        "nombre_temoignages_utilisation": types["utilisation_declaree_par_agent"],
        "premiere_contribution_utile_exactement_datee": False,
        "delai_besoin_vers_premiere_utilite_jours": None,
        "intervalles_choix_a_conclusion_jours": delais,
    }


def bilan(registre: dict, captures: dict) -> dict:
    if not isinstance(registre, dict) or registre.get("version") != VERSION:
        raise PreuveInvalide("Version de corpus inconnue")
    date_canonique(registre.get("date_recherche"), "date_recherche")
    sources = verifier_sources(registre.get("sources"), captures)
    episodes = registre.get("episodes")
    if not isinstance(episodes, list) or not episodes:
        raise PreuveInvalide("Épisodes absents")
    sortie = [verifier_episode(e, sources) for e in episodes]
    identifiants = [x["id_episode"] for x in sortie]
    if len(set(identifiants)) != len(identifiants):
        raise PreuveInvalide("Identifiant d'épisode dupliqué")
    if len(sortie) != 4 or set(identifiants) != {
        "SICTIAM-SAD-2026", "SICOVAL-2025",
        "ESCALQUENS-2025", "AUZEVILLE-2025",
    }:
        raise PreuveInvalide("Corpus pilote incomplet ou élargi sans validation")
    partage = defaultdict(list)
    for e in episodes:
        if e.get("fournisseur_siren_partage"):
            partage[e["fournisseur_siren_partage"]].append(e["id"])
    return {
        "version": VERSION,
        "date_recherche": registre["date_recherche"],
        "nombre_episodes": len(sortie),
        "nombre_sources": len(sources),
        "nombre_pdfs_municipaux_empreintes": sum(
            s["type"] == "pdf_communal" for s in sources.values()
        ),
        "temoignages_usage_dates_par_document": sum(
            x["nombre_temoignages_utilisation"] for x in sortie
        ),
        "premieres_contributions_utiles_precisement_datees": 0,
        "mesures_effet_independantes": 0,
        "relations_contractuelles_inter_circuits_etablies": 0,
        "identites_legales_communes_sans_filiation_contractuelle": {
            k: sorted(v) for k, v in sorted(partage.items()) if len(v) > 1
        },
        "episodes": sortie,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--episodes", type=Path,
                   default=Path("donnees/episodes_mobilisation_preuves_v1.json"))
    p.add_argument("--captures", type=Path,
                   default=Path("institutionnel/pieces_publiques/observations_pdfs_municipaux.json"))
    p.add_argument("--sortie", type=Path)
    args = p.parse_args()
    try:
        registre = json.loads(args.episodes.read_text(encoding="utf-8"))
        captures = json.loads(args.captures.read_text(encoding="utf-8"))
        texte = json.dumps(bilan(registre, captures), ensure_ascii=False,
                           sort_keys=True, indent=2) + "\n"
        if args.sortie:
            with args.sortie.open("x", encoding="utf-8") as f:
                f.write(texte)
        else:
            print(texte, end="")
    except (OSError, ValueError, json.JSONDecodeError) as err:
        p.exit(1, f"Chaîne d'épisodes non vérifiable : {type(err).__name__}: {err}\n")


if __name__ == "__main__":
    main()
