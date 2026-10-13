"""Étendre le balayage DECP à sept mois avec déduplication documentaire.

Les trois fichiers originaux sont relus depuis l'archive officielle scellée par
empreintes ; seuls quatre mois supplémentaires sont téléchargés. Toutes les
identités documentaires (SIRET acheteur, identifiant de marché) sont comparées
entre les sept mois. Les variantes normalisées restent séparées.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

try:
    from scripts.balayer_fichiers_consolides_decp import (
        VERSION as VERSION_PRECEDENTE, SOURCE, CATALOGUE_URL,
        MOIS as MOIS_PRECEDENTS, BalayageInvalide, analyser, cibles,
        choisir_ressources, empreinte, recevoir, lire_fiche_officielle,
    )
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from balayer_fichiers_consolides_decp import (
        VERSION as VERSION_PRECEDENTE, SOURCE, CATALOGUE_URL,
        MOIS as MOIS_PRECEDENTS, BalayageInvalide, analyser, cibles,
        choisir_ressources, empreinte, recevoir, lire_fiche_officielle,
    )

VERSION = "extension-decp-sept-mois-v1"
MOIS_NOUVEAUX = ("2025-10", "2025-12", "2026-03", "2026-05")
PLAFOND_PAR_FICHIER = 160_000_000
PLAFOND_QUATRE_FICHIERS = 430_000_000
EMP = re.compile(r"[0-9a-f]{64}")


class ExtensionInvalide(BalayageInvalide):
    """Archives, identités ou ressources incohérentes."""


class IndexIntermois:
    """Index limité aux identités composites et empreintes de versions."""

    def __init__(self):
        self.index: dict[tuple[str, str], dict] = {}
        self.observations = 0
        self.repetitions_exactes = 0
        self.variantes_supplementaires = 0

    def observer(self, ligne: dict, mois: str) -> None:
        cle = ligne["acheteur_siret"], ligne["id_marche"]
        signature = hashlib.sha256(json.dumps(
            ligne, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
        self.observations += 1
        if cle not in self.index:
            self.index[cle] = {"signatures": {signature}, "mois": {mois}}
            return
        entree = self.index[cle]
        entree["mois"].add(mois)
        if signature in entree["signatures"]:
            self.repetitions_exactes += 1
        else:
            entree["signatures"].add(signature)
            self.variantes_supplementaires += 1

    def bilan(self) -> dict:
        versions = sum(len(x["signatures"]) for x in self.index.values())
        multi_mois = sum(len(x["mois"]) > 1 for x in self.index.values())
        plusieurs_variantes = sum(len(x["signatures"]) > 1 for x in self.index.values())
        if versions != len(self.index) + self.variantes_supplementaires:
            raise ExtensionInvalide("Nombre de variantes incohérent")
        if self.observations != versions + self.repetitions_exactes:
            raise ExtensionInvalide("Décompte intermensuel incohérent")
        return {
            "observations_marche_normalisees": self.observations,
            "identites_distinctes_siret_et_id_marche": len(self.index),
            "variantes_documentaires_distinctes": versions,
            "repetitions_de_variantes_identiques": self.repetitions_exactes,
            "observations_de_variantes_nouvelles": self.variantes_supplementaires,
            "identites_apparaissant_dans_plusieurs_mois": multi_mois,
            "identites_avec_plusieurs_variantes": plusieurs_variantes,
            "dates_publication_non_assimilees_dates_execution": True,
        }


def sources_anciennes(archive: Path, empreinte_attendue: str | None = None) -> tuple[list[dict], str]:
    """Revérifier les trois ressources originelles sans nouvelle requête HTTP."""
    rapport = archive / "rapport.json"
    if rapport.is_symlink() or not rapport.is_file():
        raise ExtensionInvalide("Ancien rapport source absent")
    sha_rapport = empreinte(rapport)
    if empreinte_attendue is not None and sha_rapport != empreinte_attendue:
        raise ExtensionInvalide("Empreinte du rapport antérieur différente")
    ancien = json.loads(rapport.read_text(encoding="utf-8"))
    fiches = ancien.get("sources")
    if (ancien.get("version") != VERSION_PRECEDENTE
            or ancien.get("mois_examines") != list(MOIS_PRECEDENTS)
            or ancien.get("nombre_fichiers_analyses") != 3
            or not isinstance(fiches, list) or len(fiches) != 3):
        raise ExtensionInvalide("Protocole des trois premiers mois inconnu")
    selections = []
    for mois, fiche in zip(MOIS_PRECEDENTS, fiches):
        nom = f"decp-{mois}.json"
        if (not isinstance(fiche, dict) or fiche.get("nom_fichier") != nom
                or fiche.get("source_catalogue") != SOURCE
                or type(fiche.get("octets_source")) is not int
                or not 0 < fiche["octets_source"] <= 110_000_000
                or not isinstance(fiche.get("sha256_source_brute"), str)
                or not EMP.fullmatch(fiche["sha256_source_brute"])):
            raise ExtensionInvalide("Métadonnées d'un ancien fichier incorrectes")
        entree = archive / "fichiers-officiels" / nom
        if (entree.is_symlink() or not entree.is_file()
                or entree.stat().st_size != fiche["octets_source"]
                or empreinte(entree) != fiche["sha256_source_brute"]):
            raise ExtensionInvalide("Fichier historique altéré ou incomplet")
        selections.append({
            "titre": nom, "ressource_id": fiche["ressource_id"],
            "taille_octets": fiche["octets_source"],
            "url": fiche["url_fichier_officiel"],
            "date_modification_declaree": fiche["date_modification_declaree"],
            "fichier": entree,
            "sha_attendu": fiche["sha256_source_brute"],
            "nombre_objets_attendu": fiche["mesures"].get("objets_lus"),
            "nombre_marches_attendu": fiche["mesures"].get("notices_marche_lues"),
        })
    return selections, sha_rapport


def rapprocher_et_dedoublonner(
    premiers: list[dict], nouveaux: list[dict], cibles_boamp: dict,
    *, rapport_initial: str,
) -> dict:
    """Analyser sept fichiers complets, en une passe de normalisation chacun."""
    if len(premiers) != 3 or len(nouveaux) != 4:
        raise ExtensionInvalide("Sept ressources attendues")
    index = IndexIntermois()
    bilans = []
    stats = Counter()
    mois_vus = set()
    candidats = {}
    for entree in premiers + nouveaux:
        nom = entree["titre"]
        if nom in mois_vus:
            raise ExtensionInvalide("Ressource mensuelle répétée")
        mois_vus.add(nom)
        analyse = analyser(entree["fichier"], entree, cibles_boamp, observer=index.observer)
        if analyse["sha256_source_brute"] != entree["sha_attendu"]:
            raise ExtensionInvalide("Source différente de l'empreinte déclarée")
        if "nombre_objets_attendu" in entree:
            if (analyse["mesures"].get("objets_lus") != entree["nombre_objets_attendu"]
                    or analyse["mesures"].get("notices_marche_lues") != entree["nombre_marches_attendu"]):
                raise ExtensionInvalide("Population historique modifiée")
        stats.update(analyse["mesures"])
        for fiche in analyse["candidats"]:
            cle = fiche["siret_acheteur_decp"], fiche["reference_marche_decp"]
            item = candidats.setdefault(cle, {
                "siret_acheteur_decp": cle[0],
                "reference_marche_decp": cle[1],
                "meme_siret_acheteur_boamp": fiche["meme_siret_acheteur"],
                "avis_sources_meme_acheteur": fiche["avis_sources_meme_acheteur"],
                "mois_observes": set(),
                "dates_notification_declarees": set(),
                "contrat_juridiquement_identifie": False,
            })
            if (item["meme_siret_acheteur_boamp"] != fiche["meme_siret_acheteur"]
                    or item["avis_sources_meme_acheteur"] != fiche["avis_sources_meme_acheteur"]):
                raise ExtensionInvalide("Identité de candidat contradictoire")
            item["mois_observes"].add(nom)
            if fiche["date_notification_decp"]:
                item["dates_notification_declarees"].add(fiche["date_notification_decp"])
        bilans.append({k: v for k, v in analyse.items() if k != "candidats"})
    resultat_index = index.bilan()
    if index.observations != stats["notices_normalisees"]:
        raise ExtensionInvalide("Index intermensuel incomplet")
    pistes = []
    for cle, candidat in sorted(candidats.items()):
        pistes.append({
            **{k: v for k, v in candidat.items()
               if k not in ("mois_observes", "dates_notification_declarees")},
            "mois_observes": sorted(candidat["mois_observes"]),
            "dates_notification_declarees": sorted(
                candidat["dates_notification_declarees"]
            ),
        })
    return {
        "version": VERSION,
        "capture_precedente_sha256_rapport": rapport_initial,
        "mois_anterieurs": list(MOIS_PRECEDENTS),
        "mois_nouveaux": list(MOIS_NOUVEAUX),
        "nombre_fichiers_intacts_lus": len(bilans),
        "mois_effectivement_parcourus": sorted(mois_vus),
        "statistiques": dict(sorted(stats.items())),
        "dedoublonnage_intermois": resultat_index,
        "nombre_pistes_avec_siret_acheteur_identique": sum(
            bool(p["meme_siret_acheteur_boamp"]) for p in pistes
        ),
        "nombre_references_collisions_autres_acheteurs": sum(
            not p["meme_siret_acheteur_boamp"] for p in pistes
        ),
        "pistes_documentaires": pistes,
        "sources": bilans,
        "contrats_juridiquement_demontrés": 0,
        "couverture_nationale_exhaustive": False,
        "rejets_signales_et_non_assimiles_absences": True,
    }


def executer(
    chaines: Path, anciennes: Path, inventaire: dict, catalogue: dict,
    sortie: Path, *, recuperer=recevoir, empreinte_rapport_initial: str | None = None,
) -> dict:
    """Produire atomiquement une archive si et seulement si tout le lot réussit."""
    if sortie.exists() or sortie.is_symlink():
        raise ExtensionInvalide("Répertoire de destination déjà présent")
    objectifs, provenance = cibles(chaines)
    precedents, sha_initial = sources_anciennes(anciennes, empreinte_rapport_initial)
    selection = choisir_ressources(
        inventaire, catalogue, mois=MOIS_NOUVEAUX,
        plafond_fichier=PLAFOND_PAR_FICHIER,
        plafond_total=PLAFOND_QUATRE_FICHIERS,
    )
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=sortie.parent, prefix=".decp-sept-mois-",
    ) as temp:
        transitoire = Path(temp)
        dossier = transitoire / "fichiers-officiels"
        dossier.mkdir()
        nouveaux = []
        for ressource in selection:
            fichier = dossier / ressource["titre"]
            if recuperer is recevoir:
                recuperer(ressource, fichier, plafond=PLAFOND_PAR_FICHIER)
            else:
                recuperer(ressource, fichier)
            if (not fichier.is_file()
                    or fichier.stat().st_size != ressource["taille_octets"]):
                raise ExtensionInvalide("Fichier mensuel non reçu dans sa totalité")
            nouveaux.append({
                **ressource, "fichier": fichier, "sha_attendu": empreinte(fichier),
            })
        rapport = rapprocher_et_dedoublonner(
            precedents, nouveaux, objectifs, rapport_initial=sha_initial,
        )
        rapport["capture_des_cibles_sha256"] = provenance["sha256_rapport_chainage"]
        rapport["execute_le"] = datetime.now(timezone.utc).isoformat()
        (transitoire / "rapport.json").write_text(
            json.dumps(rapport, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n", encoding="utf-8",
        )
        os.replace(transitoire, sortie)
    return rapport


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chaines", type=Path, required=True)
    parser.add_argument("--archives-precedentes", type=Path, required=True)
    parser.add_argument("--inventaire", type=Path, default=Path(
        "institutionnel/decp/etat_ressources.json"
    ))
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    try:
        etat = json.loads(args.inventaire.read_text(encoding="utf-8"))
        fiche = lire_fiche_officielle({"url": CATALOGUE_URL})
        rapport = executer(
            args.chaines, args.archives_precedentes, etat, fiche, args.sortie,
        )
        print(json.dumps({
            "mois": len(rapport["mois_effectivement_parcourus"]),
            "marches_normalises": rapport["statistiques"]["notices_normalisees"],
            "marches_rejetes": rapport["statistiques"].get(
                "notices_marche_rejetees", 0
            ),
            "identites_distinctes": rapport["dedoublonnage_intermois"][
                "identites_distinctes_siret_et_id_marche"
            ],
            "pistes_avec_meme_siret": rapport[
                "nombre_pistes_avec_siret_acheteur_identique"
            ],
            "liaisons_juridiques": 0,
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"Extension du balayage DECP interrompue : {exc}\n")


if __name__ == "__main__":
    main()
