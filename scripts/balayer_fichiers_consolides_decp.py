"""Balayer trois fichiers consolidés DECP complets contre sept références BOAMP.

Aucun résultat négatif n'est extrapolé au catalogue national. Le fichier est
lu en flux et son empreinte exacte est liée au manifeste de la ressource.
Les références de procédure, de lot et de contrat sont distinguées.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError, URLError

try:
    from scripts.collecter_catalogues_decp import telecharger as lire_fiche_officielle
    from scripts.ingerer_fichier_decp_json import (
        iterer_documents, normaliser_marche, DocumentDECPInvalide,
    )
    from scripts.rapprocher_references_decp_boamp import reference_normalisee
    from scripts.sonder_ressource_decp_aife import (
        _url_officielle, RedirectionsRestreintes,
    )
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from collecter_catalogues_decp import telecharger as lire_fiche_officielle
    from ingerer_fichier_decp_json import (
        iterer_documents, normaliser_marche, DocumentDECPInvalide,
    )
    from rapprocher_references_decp_boamp import reference_normalisee
    from sonder_ressource_decp_aife import (
        _url_officielle, RedirectionsRestreintes,
    )

from urllib.request import Request, build_opener

VERSION = "balayage-contrats-consolides-decp-v1"
SOURCE = "mef_decp_consolides"
CATALOGUE_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "donnees-essentielles-de-la-commande-publique-fichiers-consolides/"
)
MOIS = ("2025-08", "2026-02", "2026-04")
FICHIERS = {f"decp-{mois}.json" for mois in MOIS}
PLAFOND_PAR_FICHIER = 110_000_000
PLAFOND_TOTAL = 250_000_000
PLAFOND_RESULTATS = 1000
SHA = re.compile(r"[0-9a-f]{64}")
SIRET = re.compile(r"[0-9]{14}")


class BalayageInvalide(ValueError):
    """Un périmètre, un fichier ou une preuve ne satisfait pas au protocole."""


def empreinte(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as entree:
        for bloc in iter(lambda: entree.read(1_048_576), b""):
            h.update(bloc)
    return h.hexdigest()


def cibles(rapport: Path) -> tuple[dict, dict]:
    """N'admettre que les sept références contractuelles du rapport archivé."""
    source = json.loads(rapport.read_text(encoding="utf-8"))
    if (not isinstance(source, dict)
            or source.get("version") != "chaines-documentaires-acheteurs-17-avis-v1"
            or source.get("liaisons_contractuelles_decp_prouvees") != 0
            or source.get("nombre_siret_distincts") != 16):
        raise BalayageInvalide("Rapport BOAMP initial non conforme")
    mesures = source.get("mesures", {})
    if (mesures.get("avis") != 17
            or mesures.get("references_contrat_comparables") != 7):
        raise BalayageInvalide("Population cible BOAMP altérée")
    dossiers = source.get("dossiers")
    if not isinstance(dossiers, list) or len(dossiers) != 17:
        raise BalayageInvalide("Dossiers sources absents")
    resultat: dict[tuple[str, str], list[dict]] = {}
    chemins = set()
    for dossier in dossiers:
        numero_avis = dossier.get("avis_boamp")
        acheteur = dossier.get("siret_chiffres_sans_schema_boamp")
        if not isinstance(numero_avis, str) or not SIRET.fullmatch(acheteur or ""):
            raise BalayageInvalide("Avis ou identité acheteur invalides")
        contrats = dossier.get("contrats_locaux")
        if not isinstance(contrats, list):
            raise BalayageInvalide("Contrats locaux absents")
        for contrat in contrats:
            if not contrat.get("reference_contrat_comparable_decp"):
                continue
            brute = contrat.get("reference_contrat_declaree")
            cle = reference_normalisee(brute)
            if not cle:
                raise BalayageInvalide("Référence déclarée non comparable")
            identite = (numero_avis, contrat["reference_locale"])
            if identite in chemins:
                raise BalayageInvalide("Même contrat répété dans l'avis")
            chemins.add(identite)
            resultat.setdefault((acheteur, cle), []).append({
                "avis": numero_avis,
                "siret_acheteur": acheteur,
                "reference_contrat_source": brute,
                "code_contrat_local": contrat["reference_locale"],
                "preuve_champ_contrat": contrat["origine_reference_contrat"],
            })
    if len(chemins) != 7:
        raise BalayageInvalide("Sept références contractuelles attendues")
    return resultat, {
        "sha256_rapport_chainage": empreinte(rapport),
        "nombre_references_contractuelles": len(chemins),
        "nombre_couples_candidats_distincts": len(resultat),
        "nombre_avis_cibles": len({x["avis"] for v in resultat.values() for x in v}),
    }


def choisir_ressources(registre: dict, fiche: dict) -> list[dict]:
    """Croiser catalogue déjà observé et fiche officielle au même identifiant."""
    if not isinstance(registre, dict) or not isinstance(fiche, dict):
        raise BalayageInvalide("Catalogue non structuré")
    local = next((x for x in registre.get("catalogues", [])
                  if x.get("source_id") == SOURCE), None)
    if local is None or not isinstance(local.get("ressources_recentes"), list):
        raise BalayageInvalide("Inventaire local des ressources consolidées absent")
    distantes = fiche.get("resources")
    if not isinstance(distantes, list):
        raise BalayageInvalide("Références de fichiers officiels absentes")
    index = {}
    for x in distantes:
        if isinstance(x, dict) and isinstance(x.get("id"), str):
            if x["id"] in index:
                raise BalayageInvalide("Identifiant distant de ressource dupliqué")
            index[x["id"]] = x
    retenues = {}
    for localitem in local["ressources_recentes"]:
        titre = localitem.get("titre")
        if titre not in FICHIERS:
            continue
        if titre in retenues:
            raise BalayageInvalide("Fichier mensuel déclaré plusieurs fois")
        distant = index.get(localitem.get("id"))
        taille = localitem.get("taille_octets_declaree")
        if (distant is None
                or type(taille) is not int
                or not 0 < taille <= PLAFOND_PAR_FICHIER
                or type(distant.get("filesize")) is not int
                or distant["filesize"] != taille
                or localitem.get("format") != "json"
                or str(distant.get("format", "")).lower() != "json"
                or distant.get("title") != titre):
            raise BalayageInvalide("Métadonnées mensuelles divergentes")
        retenues[titre] = {
            "titre": titre, "ressource_id": localitem["id"],
            "date_modification_declaree": localitem.get("modifie_le"),
            "taille_octets": taille,
            "url": _url_officielle(distant.get("url")),
        }
    if set(retenues) != FICHIERS:
        raise BalayageInvalide("Un ou plusieurs des trois mois manquent")
    selection = [retenues[f"decp-{m}.json"] for m in MOIS]
    if sum(x["taille_octets"] for x in selection) > PLAFOND_TOTAL:
        raise BalayageInvalide("Budget d'octets des trois mois dépassé")
    return selection


def recevoir(selection: dict, fichier: Path) -> None:
    """Conserver les octets sans dépassement, téléchargement non suivi hors domaine."""
    url = _url_officielle(selection["url"])
    demande = Request(url, headers={
        "Accept": "application/json,application/octet-stream",
        "User-Agent": "FRONTIERE-recherche-contrats-DECP/1.0",
    })
    compte = 0
    with build_opener(RedirectionsRestreintes()).open(demande, timeout=150) as reponse:
        if reponse.status != 200:
            raise BalayageInvalide("Réponse source non HTTP 200")
        _url_officielle(reponse.geturl())
        with fichier.open("wb") as sortie:
            while True:
                morceaux = reponse.read(min(1_048_576, PLAFOND_PAR_FICHIER - compte + 1))
                if not morceaux:
                    break
                compte += len(morceaux)
                if compte > PLAFOND_PAR_FICHIER:
                    raise BalayageInvalide("Dépassement du plafond par source")
                sortie.write(morceaux)
    if compte != selection["taille_octets"]:
        raise BalayageInvalide("Volume téléchargé différent des métadonnées vérifiées")


def analyser(chemin: Path, selection: dict, cibles_par_identite: dict) -> dict:
    """Parcourir intégralement le fichier ; conserver les seuls candidats."""
    if chemin.stat().st_size != selection["taille_octets"]:
        raise BalayageInvalide("Taille réelle du fichier incorrecte")
    sig = empreinte(chemin)
    stats = Counter()
    erreurs = Counter()
    identites_vues = set()
    correspondances = []
    references = {cle for (_, cle) in cibles_par_identite}
    with chemin.open("r", encoding="utf-8-sig") as flux:
        for type_objet, objet in iterer_documents(flux):
            stats["objets_lus"] += 1
            if type_objet == "contrat-concession":
                stats["concessions_exclues"] += 1
                continue
            stats["notices_marche_lues"] += 1
            # Le champ officiel offresRecues="NC" signifie effectif non
            # communiqué. Cette valeur facultative ne doit pas masquer une
            # identité contractuelle valide ; elle ne signifie jamais zéro.
            if isinstance(objet, dict) and objet.get("offresRecues") == "NC":
                objet = {**objet, "offresRecues": None}
                stats["offres_recues_non_communiquees_nc"] += 1
            try:
                ligne = normaliser_marche(objet)
            except DocumentDECPInvalide as exc:
                stats["notices_marche_rejetees"] += 1
                erreurs[str(exc)[:180]] += 1
                continue
            stats["notices_normalisees"] += 1
            identite = (ligne["acheteur_siret"], ligne["id_marche"])
            if identite not in identites_vues:
                identites_vues.add(identite)
                stats["identites_distinctes_normalisees"] += 1
            else:
                stats["repetitions_identites"] += 1
            ref = reference_normalisee(ligne["id_marche"])
            if ref not in references:
                continue
            if len(correspondances) >= PLAFOND_RESULTATS:
                raise BalayageInvalide("Plafond de candidats dépassé")
            candidats = cibles_par_identite.get((ligne["acheteur_siret"], ref), [])
            correspondances.append({
                "reference_marche_decp": ligne["id_marche"],
                "siret_acheteur_decp": ligne["acheteur_siret"],
                "date_notification_decp": ligne["date_notification"],
                "date_publication_declaree_decp": ligne["date_publication_declaree"],
                "releve_mensuel": selection["titre"],
                "egalite_reference_normalisee": True,
                "avis_sources_meme_acheteur": [{
                    **c, "egalite_litterale_id": c["reference_contrat_source"] == ligne["id_marche"],
                } for c in candidats],
                "meme_siret_acheteur": bool(candidats),
                "identite_juridique_contrat_demonstree": False,
            })
            stats["references_communes_tous_acheteurs"] += 1
            if candidats:
                stats["candidats_avec_siret_acheteur_concordant"] += 1
            else:
                stats["homonymies_reference_autres_acheteurs"] += 1
    if stats["notices_marche_lues"] < 1 or stats["notices_normalisees"] == 0:
        raise BalayageInvalide("Fichier mensuel sans marchés normalisés")
    if (stats["notices_marche_lues"] !=
            stats["notices_normalisees"] + stats["notices_marche_rejetees"]):
        raise BalayageInvalide("Dénominateurs incohérents")
    return {
        "source_catalogue": SOURCE,
        "nom_fichier": selection["titre"],
        "ressource_id": selection["ressource_id"],
        "url_fichier_officiel": selection["url"],
        "date_modification_declaree": selection["date_modification_declaree"],
        "octets_source": selection["taille_octets"],
        "sha256_source_brute": sig,
        "mesures": dict(sorted(stats.items())),
        "rejets_par_categorie": dict(sorted(erreurs.items())),
        "candidats": correspondances,
        "fichier_integral_parcouru": True,
        "corpus_national_exhaustif": False,
    }


def executer(chaine: Path, etat: dict, fiche: dict, sorties: Path,
             *, recuperer=recevoir, instant: datetime | None = None) -> dict:
    """Publier le rapport seulement si les trois fichiers sont complets."""
    objectifs, preuve = cibles(chaine)
    choix = choisir_ressources(etat, fiche)
    instant = instant or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise BalayageInvalide("Date de consultation non située")
    if sorties.exists() or sorties.is_symlink():
        raise BalayageInvalide("Refus d'écraser un bilan existant")
    sorties.mkdir(parents=True)
    sources = sorties / "fichiers-officiels"
    sources.mkdir()
    try:
        analyses = []
        for choix_fichier in choix:
            fichier = sources / choix_fichier["titre"]
            recuperer(choix_fichier, fichier)
            analyses.append(analyser(fichier, choix_fichier, objectifs))
        stats = Counter()
        for source in analyses:
            stats.update(source["mesures"])
        rapport = {
            "version": VERSION,
            "analyse_le": instant.astimezone(timezone.utc).isoformat(),
            **preuve,
            "mois_examines": list(MOIS),
            "nombre_fichiers_analyses": len(analyses),
            "statistiques_globales_avec_repetitions_possibles": dict(sorted(stats.items())),
            "identites_distinctes_entre_mois_non_dedoublonnees": True,
            "candidats_decp_meme_siret": stats["candidats_avec_siret_acheteur_concordant"],
            "contrats_juridiquement_demontrés": 0,
            "extension_a_tous_les_marches_francais": False,
            "sources": analyses,
        }
        (sorties / "rapport.json").write_text(
            json.dumps(rapport, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        return rapport
    except BaseException:
        # Conserver uniquement les collectes réussies si toutes les étapes
        # atteignent leur terme ; le chemin des résultats partiels est détruit.
        import shutil
        shutil.rmtree(sorties, ignore_errors=True)
        raise


def reexaminer_archive(chaine: Path, precedente: Path, sortie: Path) -> dict:
    """Rejouer les octets du premier passage, sans nouveau téléchargement.

    Le manifeste initial demeure intact. Chaque fichier archivé doit avoir
    exactement son empreinte d'origine, son identifiant et sa taille.
    """
    if sortie.exists() or sortie.is_symlink():
        raise BalayageInvalide("Refus d'écraser une relecture existante")
    objectifs, preuve = cibles(chaine)
    original = precedente / "rapport.json"
    if not original.is_file() or original.is_symlink():
        raise BalayageInvalide("Rapport original absent")
    primaires = json.loads(original.read_text(encoding="utf-8"))
    if (primaires.get("version") != VERSION
            or primaires.get("sha256_rapport_chainage")
               != preuve["sha256_rapport_chainage"]
            or primaires.get("mois_examines") != list(MOIS)
            or primaires.get("nombre_fichiers_analyses") != 3
            or not isinstance(primaires.get("sources"), list)
            or len(primaires["sources"]) != 3):
        raise BalayageInvalide("Rapport source incompatible avec la relecture")
    sources = precedente / "fichiers-officiels"
    resultats, taille_totale = [], 0
    for mois, entree in zip(MOIS, primaires["sources"]):
        nom = f"decp-{mois}.json"
        if (not isinstance(entree, dict) or entree.get("nom_fichier") != nom
                or entree.get("source_catalogue") != SOURCE
                or not isinstance(entree.get("ressource_id"), str)
                or not isinstance(entree.get("sha256_source_brute"), str)
                or not SHA.fullmatch(entree["sha256_source_brute"])
                or type(entree.get("octets_source")) is not int
                or not 0 < entree["octets_source"] <= PLAFOND_PAR_FICHIER):
            raise BalayageInvalide("Identité primaire de ressource incohérente")
        fichier = sources / nom
        if not fichier.is_file() or fichier.is_symlink():
            raise BalayageInvalide("Fichier primaire absent ou lien symbolique")
        if (fichier.stat().st_size != entree["octets_source"]
                or empreinte(fichier) != entree["sha256_source_brute"]):
            raise BalayageInvalide("Octets de source différents de la première capture")
        taille_totale += entree["octets_source"]
        if taille_totale > PLAFOND_TOTAL:
            raise BalayageInvalide("Budget total de fichiers dépassé")
        selection = {
            "titre": nom, "ressource_id": entree["ressource_id"],
            "url": _url_officielle(entree["url_fichier_officiel"]),
            "date_modification_declaree": entree["date_modification_declaree"],
            "taille_octets": entree["octets_source"],
        }
        resultat = analyser(fichier, selection, objectifs)
        if resultat["sha256_source_brute"] != entree["sha256_source_brute"]:
            raise BalayageInvalide("Empreinte de relecture incohérente")
        if (resultat["mesures"].get("objets_lus")
                != entree["mesures"].get("objets_lus")
                or resultat["mesures"].get("notices_marche_lues")
                != entree["mesures"].get("notices_marche_lues")
                or resultat["mesures"].get("concessions_exclues")
                != entree["mesures"].get("concessions_exclues")):
            raise BalayageInvalide("Population primaire modifiée pendant la relecture")
        resultats.append(resultat)
    stats = Counter()
    for entree in resultats:
        stats.update(entree["mesures"])
    rapport = {
        "version": VERSION,
        "relecture_de_sources_archivees": True,
        "source_rapport_precedent_sha256": empreinte(original),
        "retelechargement_officiel_effectue": False,
        "relecture_le": datetime.now(timezone.utc).isoformat(),
        **preuve,
        "mois_examines": list(MOIS),
        "nombre_fichiers_analyses": 3,
        "statistiques_globales_avec_repetitions_possibles": dict(sorted(stats.items())),
        "identites_distinctes_entre_mois_non_dedoublonnees": True,
        "candidats_decp_meme_siret": stats["candidats_avec_siret_acheteur_concordant"],
        "contrats_juridiquement_demontrés": 0,
        "extension_a_tous_les_marches_francais": False,
        "interpretation_nc": "effectif_offres_non_communique_jamais_zero",
        "sources": resultats,
    }
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(
        json.dumps(rapport, ensure_ascii=False, indent=2,
                   sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return rapport


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chaines", type=Path, required=True)
    p.add_argument("--etat", type=Path,
                   default=Path("institutionnel/decp/etat_ressources.json"))
    p.add_argument("--sortie", type=Path, required=True)
    p.add_argument("--archives", type=Path,
                   help="Relecture locale des trois sources déjà archivées, sans accès réseau")
    a = p.parse_args()
    try:
        if a.archives is not None:
            rapport = reexaminer_archive(a.chaines, a.archives, a.sortie)
        else:
            etat = json.loads(a.etat.read_text(encoding="utf-8"))
            fiche = lire_fiche_officielle({"url": CATALOGUE_URL})
            rapport = executer(a.chaines, etat, fiche, a.sortie)
        print(json.dumps({
            "fichiers": rapport["nombre_fichiers_analyses"],
            "notices": rapport["statistiques_globales_avec_repetitions_possibles"].get(
                "notices_marche_lues", 0
            ),
            "normalisees": rapport["statistiques_globales_avec_repetitions_possibles"].get(
                "notices_normalisees", 0
            ),
            "candidats_meme_siret": rapport["candidats_decp_meme_siret"],
            "liaisons_contractuelles_prouvees": 0,
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError, HTTPError, URLError) as exc:
        p.exit(1, f"Balayage DECP interrompu : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
