from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[1]

SOURCE_ID = "dila_annuaire_local"
SOURCE_ROAE_ID = "dila_roae"
VERSION_TRANSFORMATION = "2.1"

PAGE_SOURCE = "https://www.data.gouv.fr/datasets/service-public-gouv-fr-annuaire-de-ladministration-base-de-donnees-locales"
URL_SOURCE = (
    "https://api-lannuaire.service-public.gouv.fr/api/explore/v2.1/catalog/"
    "datasets/api-lannuaire-administration/exports/json"
)
URL_COMPETENCE = (
    "https://api-lannuaire.service-public.gouv.fr/api/explore/v2.1/catalog/"
    "datasets/api-lannuaire-administration-locale-competence-geographique"
)
NOM_SOURCE = "api-lannuaire-administration.json"

DOSSIER_ENTITES = RACINE / "institutionnel" / "entites" / "locales"
DOSSIER_RELATIONS = RACINE / "institutionnel" / "relations" / "locales"
MANIFESTE = RACINE / "institutionnel" / "instantanes" / "annuaire_local_manifest.json"
STATISTIQUES = RACINE / "institutionnel" / "statistiques_annuaire_local.json"
ANOMALIES = RACINE / "institutionnel" / "anomalies_annuaire_local.json"
RESOLUTION_CROISEE = RACINE / "institutionnel" / "resolution_roae_local.json"

DOSSIER_ROAE = RACINE / "institutionnel" / "entites" / "roae"
ANOMALIES_ROAE = RACINE / "institutionnel" / "anomalies_roae.json"

N_PARTITIONS_ENTITES = 128
N_PARTITIONS_RELATIONS = 32
TAILLE_BLOC = 1024 * 1024

CATEGORIES_LOCALES = {"SL", "SIL"}


def maintenant_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def nettoyer_texte(valeur: Any) -> str | None:
    if valeur is None:
        return None
    texte = str(valeur).strip()
    return texte or None


def decoder_json_embarque(valeur: Any) -> Any:
    if not isinstance(valeur, str):
        return valeur
    texte = valeur.strip()
    if not texte or texte[0] not in "[{":
        return valeur
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        return valeur


def liste(valeur: Any) -> list[Any]:
    valeur = decoder_json_embarque(valeur)
    if valeur is None or valeur == "":
        return []
    return valeur if isinstance(valeur, list) else [valeur]


def compact_sha256(objet: Any) -> str:
    brut = json.dumps(
        objet,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def sha256_fichier(chemin: Path) -> str:
    hachage = hashlib.sha256()
    with chemin.open("rb") as fichier:
        for bloc in iter(lambda: fichier.read(4 * TAILLE_BLOC), b""):
            hachage.update(bloc)
    return hachage.hexdigest()


def compacter(objet: Any) -> Any:
    if isinstance(objet, dict):
        resultat = {}
        for cle, valeur in objet.items():
            nettoye = compacter(valeur)
            if nettoye not in (None, "", [], {}):
                resultat[cle] = nettoye
        return resultat
    if isinstance(objet, list):
        resultat = [compacter(valeur) for valeur in objet]
        return [valeur for valeur in resultat if valeur not in (None, "", [], {})]
    return objet


def id_canonique_local(id_dila: str) -> str:
    nettoye = re.sub(r"[^A-Za-z0-9-]", "-", id_dila).upper()
    return f"FRONTIERE-INST-DILA-LOCAL-{nettoye}"


def telecharger(url: str, destination: Path) -> dict[str, str]:
    requete = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FRONTIERE-referentiel-institutionnel/2.0",
            "Accept": "application/json,*/*",
        },
    )
    total = 0
    with urllib.request.urlopen(requete, timeout=180) as reponse:
        entetes = {cle.lower(): valeur for cle, valeur in reponse.headers.items()}
        with destination.open("wb") as fichier:
            while True:
                bloc = reponse.read(TAILLE_BLOC)
                if not bloc:
                    break
                fichier.write(bloc)
                total += len(bloc)
                if total and total % (64 * TAILLE_BLOC) < TAILLE_BLOC:
                    print(f"Téléchargé: {total // TAILLE_BLOC} Mio", flush=True)
    entetes["octets_lus"] = str(total)
    return entetes


def charger_export(chemin: Path) -> list[dict[str, Any]]:
    with chemin.open("r", encoding="utf-8-sig") as fichier:
        donnees = json.load(fichier)

    if isinstance(donnees, list):
        return [item for item in donnees if isinstance(item, dict)]

    if isinstance(donnees, dict):
        for cle in ("results", "records", "data", "items"):
            valeur = donnees.get(cle)
            if isinstance(valeur, list):
                return [item for item in valeur if isinstance(item, dict)]

    raise ValueError("Structure de l'export API Annuaire non reconnue.")


def filtrer_services_locaux(
    enregistrements: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter]:
    categories = Counter(
        nettoyer_texte(item.get("categorie")) or "Non précisée"
        for item in enregistrements
    )
    locaux = [
        item
        for item in enregistrements
        if (nettoyer_texte(item.get("categorie")) or "") in CATEGORIES_LOCALES
    ]
    return locaux, categories


def valeurs_liens(valeur: Any) -> list[dict[str, Any]]:
    resultat = []
    for item in liste(valeur):
        if isinstance(item, dict):
            resultat.append(compacter(item))
        elif nettoyer_texte(item):
            resultat.append({"valeur": nettoyer_texte(item)})
    return resultat


def normaliser_responsables(service: dict[str, Any]) -> list[dict[str, Any]]:
    resultat = []
    for affectation in liste(service.get("affectation_personne")):
        if not isinstance(affectation, dict):
            continue
        personne = affectation.get("personne")
        if not isinstance(personne, dict):
            personne = {}
        resultat.append(
            {
                "fonction": nettoyer_texte(affectation.get("fonction"))
                or "Fonction non précisée",
                "nom": nettoyer_texte(personne.get("nom")),
                "prenom": nettoyer_texte(personne.get("prenom")),
                "civilite": nettoyer_texte(personne.get("civilite")),
                "grade": nettoyer_texte(personne.get("grade")),
                "telephone": nettoyer_texte(affectation.get("telephone")),
                "adresses_courriel": valeurs_liens(personne.get("adresse_courriel")),
                "textes_reference": valeurs_liens(personne.get("texte_reference")),
                "source_id": SOURCE_ID,
                "valide_depuis": None,
                "valide_jusqua": None,
            }
        )
    return resultat


def normaliser_coordonnees(service: dict[str, Any]) -> list[dict[str, Any]]:
    resultat: list[dict[str, Any]] = []

    for adresse in liste(service.get("adresse")):
        if isinstance(adresse, dict):
            resultat.append({"type": "ADRESSE", **compacter(adresse)})

    for courriel in liste(service.get("adresse_courriel")):
        if isinstance(courriel, dict):
            resultat.append({"type": "COURRIEL", **compacter(courriel)})
        elif nettoyer_texte(courriel):
            resultat.append({"type": "COURRIEL", "valeur": nettoyer_texte(courriel)})

    for telephone in liste(service.get("telephone")):
        if isinstance(telephone, dict):
            resultat.append({"type": "TELEPHONE", **compacter(telephone)})
        elif nettoyer_texte(telephone):
            resultat.append({"type": "TELEPHONE", "valeur": nettoyer_texte(telephone)})

    for telephone in liste(service.get("telephone_accessible")):
        if isinstance(telephone, dict):
            resultat.append({"type": "TELEPHONE_ACCESSIBLE", **compacter(telephone)})
        elif nettoyer_texte(telephone):
            resultat.append(
                {"type": "TELEPHONE_ACCESSIBLE", "valeur": nettoyer_texte(telephone)}
            )

    for telecopie in liste(service.get("telecopie")):
        if isinstance(telecopie, dict):
            resultat.append({"type": "TELECOPIE", **compacter(telecopie)})
        elif nettoyer_texte(telecopie):
            resultat.append({"type": "TELECOPIE", "valeur": nettoyer_texte(telecopie)})

    for cle, type_coord in (
        ("site_internet", "SITE_INTERNET"),
        ("formulaire_contact", "FORMULAIRE"),
        ("sve", "SAISINE_ELECTRONIQUE"),
        ("reseau_social", "RESEAU_SOCIAL"),
        ("tchat", "TCHAT"),
        ("application_mobile", "APPLICATION_MOBILE"),
        ("organigramme", "ORGANIGRAMME"),
        ("annuaire", "ANNUAIRE"),
    ):
        for item in valeurs_liens(service.get(cle)):
            resultat.append({"type": type_coord, **item})

    return resultat


def normaliser_textes(service: dict[str, Any]) -> list[dict[str, Any]]:
    resultat = []
    for item in valeurs_liens(service.get("texte_reference")):
        resultat.append(
            {
                "libelle": nettoyer_texte(item.get("libelle")),
                "url": nettoyer_texte(item.get("valeur")),
                "source_id": SOURCE_ID,
            }
        )
    return resultat


def normaliser_aliases(service: dict[str, Any]) -> list[str]:
    resultat = []
    for item in liste(service.get("ancien_nom")):
        texte = nettoyer_texte(item)
        if texte and texte not in resultat:
            resultat.append(texte)
    return resultat


def types_service_local(service: dict[str, Any]) -> list[str]:
    resultat: list[str] = []
    for pivot in liste(service.get("pivot")):
        if isinstance(pivot, dict):
            valeur = (
                nettoyer_texte(pivot.get("type_service_local"))
                or nettoyer_texte(pivot.get("code_type_service_local"))
            )
        else:
            valeur = nettoyer_texte(pivot)
        if valeur and valeur not in resultat:
            resultat.append(valeur)
    return sorted(resultat)


def codes_insee_pivot(service: dict[str, Any]) -> list[str]:
    resultat: list[str] = []

    for pivot in liste(service.get("pivot")):
        if not isinstance(pivot, dict):
            continue
        for code in liste(pivot.get("code_insee_commune")):
            texte = nettoyer_texte(code)
            if texte and texte not in resultat:
                resultat.append(texte)

    for code in liste(service.get("code_insee_commune")):
        texte = nettoyer_texte(code)
        if texte and texte not in resultat:
            resultat.append(texte)

    return sorted(resultat)


def statut_entite(service: dict[str, Any]) -> str:
    diffusion = service.get("statut_de_diffusion")
    if diffusion in (False, "false", "FALSE", 0):
        return "INCONNU"
    return "ACTIF"


CHAMPS_CANONISES = {
    "id",
    "nom",
    "ancien_nom",
    "sigle",
    "categorie",
    "type_repertoire",
    "type_organisme",
    "pivot",
    "ancien_code_pivot",
    "code_insee_commune",
    "adresse",
    "telephone",
    "telephone_accessible",
    "telecopie",
    "site_internet",
    "adresse_courriel",
    "formulaire_contact",
    "texte_reference",
    "sve",
    "reseau_social",
    "tchat",
    "application_mobile",
    "organigramme",
    "annuaire",
    "siren",
    "siret",
    "ancien_identifiant",
    "itm_identifiant",
    "partenaire_identifiant",
    "partenaire",
    "information_complementaire",
    "mission",
    "copyright",
    "partenaire_date_modification",
    "service_disponible",
    "statut_de_diffusion",
    "date_creation",
    "date_creation_datetime",
    "date_modification",
    "date_modification_datetime",
    "date_diffusion",
    "plage_ouverture",
    "commentaire_plage_ouverture",
    "hierarchie",
    "affectation_personne",
    "version_type",
    "version_source",
    "version_etat_modification",
    "url_service_public",
}


def donnees_operationnelles(service: dict[str, Any]) -> dict[str, Any]:
    donnees = {
        "categorie": service.get("categorie"),
        "type_repertoire": service.get("type_repertoire"),
        "pivot": decoder_json_embarque(service.get("pivot")),
        "ancien_code_pivot": decoder_json_embarque(service.get("ancien_code_pivot")),
        "plage_ouverture": decoder_json_embarque(service.get("plage_ouverture")),
        "commentaire_plage_ouverture": decoder_json_embarque(
            service.get("commentaire_plage_ouverture")
        ),
        "information_complementaire": service.get("information_complementaire"),
        "service_disponible": service.get("service_disponible"),
        "partenaire": service.get("partenaire"),
        "partenaire_date_modification": service.get("partenaire_date_modification"),
        "copyright": service.get("copyright"),
        "url_service_public": service.get("url_service_public"),
        "dates_source": {
            "creation": service.get("date_creation"),
            "creation_datetime": service.get("date_creation_datetime"),
            "modification": service.get("date_modification"),
            "modification_datetime": service.get("date_modification_datetime"),
            "diffusion": service.get("date_diffusion"),
        },
        "version_source": {
            "type": service.get("version_type"),
            "source": service.get("version_source"),
            "etat_modification": service.get("version_etat_modification"),
        },
    }
    extras = {
        cle: valeur
        for cle, valeur in service.items()
        if cle not in CHAMPS_CANONISES
    }
    if extras:
        donnees["champs_non_mappes"] = extras
    return compacter(donnees)


def charger_index_jsonl(dossier: Path, cle: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    if not dossier.exists():
        return index
    for chemin in sorted(dossier.glob("*.jsonl")):
        with chemin.open("r", encoding="utf-8") as fichier:
            for ligne in fichier:
                if not ligne.strip():
                    continue
                objet = json.loads(ligne)
                valeur = nettoyer_texte(objet.get(cle))
                if valeur:
                    index[valeur] = objet
    return index


def charger_index_roae() -> dict[str, str]:
    resultat: dict[str, str] = {}
    if not DOSSIER_ROAE.exists():
        return resultat
    for chemin in sorted(DOSSIER_ROAE.glob("*.jsonl")):
        with chemin.open("r", encoding="utf-8") as fichier:
            for ligne in fichier:
                if not ligne.strip():
                    continue
                entite = json.loads(ligne)
                identifiants = entite.get("identifiants") or {}
                dila_id = nettoyer_texte(identifiants.get("dila_id"))
                canonique = nettoyer_texte(entite.get("id"))
                if dila_id and canonique:
                    resultat[dila_id] = canonique
    return resultat


def provenance_precedente(precedent: dict[str, Any] | None) -> dict[str, Any] | None:
    if not precedent:
        return None
    provenance = precedent.get("provenance")
    if isinstance(provenance, list) and provenance and isinstance(provenance[0], dict):
        return provenance[0]
    return None


def canonicaliser_service(
    service: dict[str, Any],
    observe_le: str,
    precedent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dila_id = nettoyer_texte(service.get("id"))
    nom = nettoyer_texte(service.get("nom"))
    if not dila_id or not nom:
        raise ValueError("Chaque guichet local doit posséder id et nom.")

    empreinte = compact_sha256(service)
    provenance_ancienne = provenance_precedente(precedent)
    inchange = bool(
        precedent
        and provenance_ancienne
        and provenance_ancienne.get("empreinte") == empreinte
    )
    date_observation = precedent.get("observe_le") if inchange else observe_le
    date_collecte = (
        provenance_ancienne.get("collecte_le")
        if inchange and provenance_ancienne
        else observe_le
    )

    codes_service = types_service_local(service)
    type_institutionnel = (
        nettoyer_texte(service.get("type_organisme"))
        or nettoyer_texte(service.get("type_repertoire"))
        or (
            "Service local — " + ", ".join(codes_service)
            if codes_service
            else "Guichet public local"
        )
    )
    mission = nettoyer_texte(service.get("mission"))

    entite: dict[str, Any] = {
        "id": id_canonique_local(dila_id),
        "nom_officiel": nom,
        "famille": "administration_territoriale",
        "etat": statut_entite(service),
        "provenance": [
            {
                "source_id": SOURCE_ID,
                "identifiant_source": dila_id,
                "url": nettoyer_texte(service.get("url_service_public")) or PAGE_SOURCE,
                "collecte_le": date_collecte,
                "empreinte": empreinte,
            }
        ],
        "observe_le": date_observation,
    }

    options = {
        "sigle": nettoyer_texte(service.get("sigle")),
        "aliases": normaliser_aliases(service),
        "type_institutionnel": type_institutionnel,
        "nature_juridique": nettoyer_texte(service.get("type_organisme")),
        "identifiants": compacter(
            {
                "dila_local_id": dila_id,
                "itm_identifiant": nettoyer_texte(service.get("itm_identifiant")),
                "siren": nettoyer_texte(service.get("siren")),
                "siret": nettoyer_texte(service.get("siret")),
                "partenaire_identifiant": nettoyer_texte(
                    service.get("partenaire_identifiant")
                ),
                "ancien_identifiant": liste(service.get("ancien_identifiant")),
            }
        ),
        "territoires": codes_insee_pivot(service),
        "types_service_local": codes_service,
        "missions": (
            [
                {
                    "texte": mission,
                    "source_id": SOURCE_ID,
                    "nature": "PUBLIEE",
                    "valide_depuis": None,
                    "valide_jusqua": None,
                }
            ]
            if mission
            else []
        ),
        "responsables": normaliser_responsables(service),
        "coordonnees": normaliser_coordonnees(service),
        "fondements_juridiques": normaliser_textes(service),
        "donnees_annuaire_local": donnees_operationnelles(service),
    }

    for cle, valeur in options.items():
        if valeur not in (None, "", [], {}):
            entite[cle] = valeur

    return entite


def cibles_hierarchie(lien: dict[str, Any]) -> list[str]:
    resultat = []
    for item in liste(lien.get("service")):
        if isinstance(item, str):
            valeur = nettoyer_texte(item)
        elif isinstance(item, dict):
            valeur = (
                nettoyer_texte(item.get("id"))
                or nettoyer_texte(item.get("identifiant"))
                or nettoyer_texte(item.get("service_id"))
            )
        else:
            valeur = None
        if valeur and valeur not in resultat:
            resultat.append(valeur)
    return resultat


def relation_id(source: str, cible: str, type_source: str, source_id: str) -> str:
    cle = "|".join((source, cible, type_source, source_id))
    return "FRONTIERE-REL-DILA-LOCAL-" + hashlib.sha256(
        cle.encode("utf-8")
    ).hexdigest()[:24].upper()


def construire_relations_locales(
    services: list[dict[str, Any]],
    ids_locaux: set[str],
    roae: dict[str, str],
    observe_le: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    relations: dict[tuple[str, str, str], dict[str, Any]] = {}
    anomalies: list[dict[str, Any]] = []

    for parent in services:
        parent_dila = nettoyer_texte(parent.get("id"))
        if not parent_dila:
            continue
        parent_canonique = id_canonique_local(parent_dila)

        for lien in liste(parent.get("hierarchie")):
            if not isinstance(lien, dict):
                anomalies.append(
                    {
                        "type": "LIEN_HIERARCHIQUE_MALFORME",
                        "parent_id_dila": parent_dila,
                        "parent_nom": parent.get("nom"),
                        "representation_source": lien,
                    }
                )
                continue

            type_source = (
                nettoyer_texte(lien.get("type_hierarchie"))
                or nettoyer_texte(lien.get("type"))
                or "HIERARCHIE_DILA"
            )
            cibles = cibles_hierarchie(lien)
            resolues = 0
            for enfant_dila in cibles:
                if enfant_dila in ids_locaux:
                    enfant_canonique = id_canonique_local(enfant_dila)
                elif enfant_dila in roae:
                    enfant_canonique = roae[enfant_dila]
                else:
                    continue

                resolues += 1
                cle = (enfant_canonique, parent_canonique, type_source)
                relations[cle] = {
                    "id": relation_id(
                        enfant_canonique,
                        parent_canonique,
                        type_source,
                        SOURCE_ID,
                    ),
                    "source_entite": enfant_canonique,
                    "type_relation": "DEPEND_DE",
                    "cible_entite": parent_canonique,
                    "qualificatifs": {
                        "type_hierarchie_dila": type_source,
                        "origine_relation": "annuaire_local",
                    },
                    "provenance": [
                        {
                            "source_id": SOURCE_ID,
                            "identifiant_source": parent_dila,
                            "url": PAGE_SOURCE,
                            "collecte_le": observe_le,
                            "empreinte": compact_sha256(lien),
                        }
                    ],
                    "observe_le": observe_le,
                    "statut_validation": "VALIDE",
                }

            if resolues == 0:
                anomalies.append(
                    {
                        "type": "LIEN_HIERARCHIQUE_NON_RESOLU",
                        "parent_id_dila": parent_dila,
                        "parent_nom": parent.get("nom"),
                        "type_hierarchie_dila": type_source,
                        "candidats_id": cibles,
                        "representation_source": lien,
                    }
                )

    return sorted(relations.values(), key=lambda item: item["id"]), anomalies


def charger_anomalies_roae() -> list[dict[str, Any]]:
    if not ANOMALIES_ROAE.exists():
        return []
    try:
        donnees = json.loads(ANOMALIES_ROAE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    valeur = donnees.get("liens_hierarchiques_non_resolus")
    return valeur if isinstance(valeur, list) else []


def resoudre_anomalies_roae(
    ids_locaux: set[str],
    roae: dict[str, str],
    observe_le: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    resolues: list[dict[str, Any]] = []
    restantes: list[dict[str, Any]] = []

    for anomalie in charger_anomalies_roae():
        parent_dila = nettoyer_texte(anomalie.get("parent_id_dila"))
        type_source = nettoyer_texte(anomalie.get("type_hierarchie_dila")) or "HIERARCHIE_DILA"
        cibles = [
            str(valeur)
            for valeur in liste(anomalie.get("candidats_id"))
            if nettoyer_texte(valeur)
        ]
        parent_canonique = roae.get(parent_dila or "")

        trouve = False
        if parent_canonique:
            for cible in cibles:
                if cible not in ids_locaux:
                    continue
                enfant_canonique = id_canonique_local(cible)
                relations.append(
                    {
                        "id": relation_id(
                            enfant_canonique,
                            parent_canonique,
                            type_source,
                            SOURCE_ROAE_ID,
                        ),
                        "source_entite": enfant_canonique,
                        "type_relation": "DEPEND_DE",
                        "cible_entite": parent_canonique,
                        "qualificatifs": {
                            "type_hierarchie_dila": type_source,
                            "origine_relation": "resolution_croisee_roae_local",
                        },
                        "provenance": [
                            {
                                "source_id": SOURCE_ROAE_ID,
                                "identifiant_source": parent_dila,
                                "url": PAGE_SOURCE,
                                "collecte_le": observe_le,
                                "empreinte": compact_sha256(anomalie),
                            }
                        ],
                        "observe_le": observe_le,
                        "statut_validation": "VALIDE",
                    }
                )
                trouve = True

        if trouve:
            resolues.append(anomalie)
        else:
            restantes.append(anomalie)

    rapport = {
        "version": "1",
        "observe_le": observe_le,
        "anomalies_roae_initiales": len(resolues) + len(restantes),
        "resolues_par_annuaire_local": len(resolues),
        "restantes_apres_croisement": len(restantes),
        "anomalies_resolues": resolues,
        "anomalies_restantes": restantes,
    }
    return relations, rapport


def appliquer_parent_principal(
    entites: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> dict[str, Any]:
    parents: dict[str, set[str]] = defaultdict(set)
    for relation in relations:
        if relation.get("qualificatifs", {}).get("type_hierarchie_dila") == "Service Fils":
            parents[relation["source_entite"]].add(relation["cible_entite"])

    index = {entite["id"]: entite for entite in entites}
    multiples = []
    avec_parent = 0

    for identifiant, candidats in parents.items():
        entite = index.get(identifiant)
        if entite is None:
            continue
        ordonnes = sorted(candidats)
        if len(ordonnes) == 1:
            entite["parent_id"] = ordonnes[0]
            avec_parent += 1
        elif len(ordonnes) > 1:
            multiples.append(
                {
                    "entite_id": identifiant,
                    "nom_officiel": entite["nom_officiel"],
                    "parents": ordonnes,
                }
            )

    return {
        "avec_parent_principal": avec_parent,
        "sans_parent_principal": len(entites) - avec_parent,
        "parents_directs_multiples": multiples,
    }


def index_partition(cle: str, nombre: int) -> int:
    return int(hashlib.sha256(cle.encode("utf-8")).hexdigest()[:8], 16) % nombre


def ecrire_jsonl_partitionne(
    objets: list[dict[str, Any]],
    dossier: Path,
    prefixe: str,
    nombre_partitions: int,
    cle_id: str,
) -> list[dict[str, Any]]:
    if dossier.exists():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True, exist_ok=True)

    partitions: list[list[dict[str, Any]]] = [[] for _ in range(nombre_partitions)]
    for objet in objets:
        cle = nettoyer_texte(objet.get(cle_id))
        if not cle:
            raise ValueError(f"Clé de partition absente: {cle_id}")
        partitions[index_partition(cle, nombre_partitions)].append(objet)

    manifeste = []
    for idx, items in enumerate(partitions):
        items.sort(key=lambda item: str(item[cle_id]))
        chemin = dossier / f"{prefixe}_{idx:03d}.jsonl"
        texte = "".join(
            json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
            for item in items
        )
        chemin.write_text(texte, encoding="utf-8")
        brut = texte.encode("utf-8")
        manifeste.append(
            {
                "fichier": str(chemin.relative_to(RACINE)),
                "nombre": len(items),
                "sha256": hashlib.sha256(brut).hexdigest(),
                "octets": len(brut),
            }
        )
    return manifeste


def source_deja_traitee(sha_export: str) -> bool:
    if not MANIFESTE.exists():
        return False
    try:
        precedent = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(
        precedent.get("sha256_export") == sha_export
        and precedent.get("version_transformation") == VERSION_TRANSFORMATION
    )


def construire_statistiques(
    enregistrements: list[dict[str, Any]],
    categories_export: Counter,
    services: list[dict[str, Any]],
    entites: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    anomalies_hierarchie: list[dict[str, Any]],
    parentage: dict[str, Any],
    resolution_croisee: dict[str, Any],
    observe_le: str,
) -> dict[str, Any]:
    types = Counter(
        nettoyer_texte(service.get("type_organisme"))
        or nettoyer_texte(service.get("type_repertoire"))
        or (
            "Service local — " + ", ".join(types_service_local(service))
            if types_service_local(service)
            else "Guichet public local"
        )
        for service in services
    )
    codes_types = Counter(
        code
        for service in services
        for code in types_service_local(service)
    )

    taille_entites = sum(
        chemin.stat().st_size for chemin in DOSSIER_ENTITES.glob("*.jsonl")
    )
    taille_relations = sum(
        chemin.stat().st_size for chemin in DOSSIER_RELATIONS.glob("*.jsonl")
    )

    return {
        "version": "2",
        "source_id": SOURCE_ID,
        "observe_le": observe_le,
        "nombre_enregistrements_export_complet": len(enregistrements),
        "categories_export": dict(categories_export.most_common()),
        "nombre_services_locaux_source": len(services),
        "nombre_entites_canoniques": len(entites),
        "nombre_relations_hierarchiques": len(relations),
        "hierarchie": {
            "avec_parent_principal": parentage["avec_parent_principal"],
            "sans_parent_principal": parentage["sans_parent_principal"],
            "entites_a_parents_directs_multiples": len(
                parentage["parents_directs_multiples"]
            ),
            "anomalies": len(anomalies_hierarchie),
        },
        "resolution_croisee_roae": {
            "anomalies_roae_initiales": resolution_croisee[
                "anomalies_roae_initiales"
            ],
            "resolues_par_annuaire_local": resolution_croisee[
                "resolues_par_annuaire_local"
            ],
            "restantes_apres_croisement": resolution_croisee[
                "restantes_apres_croisement"
            ],
        },
        "couverture": {
            "avec_siren": sum(
                bool((entite.get("identifiants") or {}).get("siren"))
                for entite in entites
            ),
            "avec_siret": sum(
                bool((entite.get("identifiants") or {}).get("siret"))
                for entite in entites
            ),
            "avec_mission": sum(bool(entite.get("missions")) for entite in entites),
            "avec_responsable": sum(
                bool(entite.get("responsables")) for entite in entites
            ),
            "avec_coordonnees": sum(
                bool(entite.get("coordonnees")) for entite in entites
            ),
            "avec_territoire_direct": sum(
                bool(entite.get("territoires")) for entite in entites
            ),
            "avec_fondement_juridique": sum(
                bool(entite.get("fondements_juridiques")) for entite in entites
            ),
        },
        "competence_geographique": {
            "mode": "interrogation_live",
            "dataset": "api-lannuaire-administration-locale-competence-geographique",
            "url": URL_COMPETENCE,
            "raison_non_materialisation_git": (
                "Le jeu de compétence géographique comporte plusieurs millions "
                "d'enregistrements. Il est interrogé à la demande afin de garder "
                "le dépôt Git exploitable et l'information fraîche."
            ),
        },
        "stockage": {
            "octets_entites": taille_entites,
            "octets_relations": taille_relations,
            "octets_total_canonique": taille_entites + taille_relations,
        },
        "types_institutionnels_source": dict(types.most_common()),
        "types_service_local": dict(codes_types.most_common()),
    }


def executer(
    export_json: Path,
    entetes: dict[str, str],
    observe_le: str | None = None,
) -> dict[str, Any]:
    observe_le = observe_le or maintenant_iso()
    sha_export = sha256_fichier(export_json)

    if source_deja_traitee(sha_export):
        return {
            "etat": "inchange",
            "manifest": json.loads(MANIFESTE.read_text(encoding="utf-8")),
            "stats": json.loads(STATISTIQUES.read_text(encoding="utf-8")),
        }

    enregistrements = charger_export(export_json)
    services, categories_export = filtrer_services_locaux(enregistrements)

    ids = [nettoyer_texte(service.get("id")) for service in services]
    ids_non_vides = [identifiant for identifiant in ids if identifiant]
    if len(ids_non_vides) != len(services):
        raise ValueError("Le flux local contient au moins un guichet sans identifiant.")
    if len(ids_non_vides) != len(set(ids_non_vides)):
        raise ValueError("Le flux local contient des identifiants DILA en doublon.")

    ids_locaux = set(ids_non_vides)
    roae = charger_index_roae()
    anciennes_entites = charger_index_jsonl(DOSSIER_ENTITES, "id")

    entites = []
    for service in services:
        dila_id = nettoyer_texte(service.get("id"))
        assert dila_id is not None
        canonique_id = id_canonique_local(dila_id)
        entites.append(
            canonicaliser_service(
                service,
                observe_le,
                precedent=anciennes_entites.get(canonique_id),
            )
        )
    entites.sort(key=lambda item: item["id"])

    relations_locales, anomalies_hierarchie = construire_relations_locales(
        services,
        ids_locaux,
        roae,
        observe_le,
    )
    relations_croisees, resolution_croisee = resoudre_anomalies_roae(
        ids_locaux,
        roae,
        observe_le,
    )
    relations = sorted(
        {
            relation["id"]: relation
            for relation in [*relations_locales, *relations_croisees]
        }.values(),
        key=lambda item: item["id"],
    )
    parentage = appliquer_parent_principal(entites, relations)

    partitions_entites = ecrire_jsonl_partitionne(
        entites,
        DOSSIER_ENTITES,
        "annuaire_local",
        N_PARTITIONS_ENTITES,
        "id",
    )
    partitions_relations = ecrire_jsonl_partitionne(
        relations,
        DOSSIER_RELATIONS,
        "hierarchie_locale",
        N_PARTITIONS_RELATIONS,
        "id",
    )

    stats = construire_statistiques(
        enregistrements,
        categories_export,
        services,
        entites,
        relations,
        anomalies_hierarchie,
        parentage,
        resolution_croisee,
        observe_le,
    )

    STATISTIQUES.parent.mkdir(parents=True, exist_ok=True)
    STATISTIQUES.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ANOMALIES.write_text(
        json.dumps(
            {
                "version": "2",
                "source_id": SOURCE_ID,
                "observe_le": observe_le,
                "nombre_anomalies_hierarchiques": len(anomalies_hierarchie),
                "parents_directs_multiples": parentage["parents_directs_multiples"],
                "anomalies_hierarchiques": anomalies_hierarchie,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    RESOLUTION_CROISEE.write_text(
        json.dumps(
            resolution_croisee,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    manifeste = {
        "version": "2",
        "version_transformation": VERSION_TRANSFORMATION,
        "source_id": SOURCE_ID,
        "producteur": "Direction de l'information légale et administrative",
        "paternite": "Service-Public.gouv.fr / DILA",
        "licence": "Licence Ouverte 2.0",
        "page_source": PAGE_SOURCE,
        "url_export": URL_SOURCE,
        "url_competence_geographique": URL_COMPETENCE,
        "nom_fichier_telecharge": NOM_SOURCE,
        "observe_le": observe_le,
        "derniere_modification_http": entetes.get("last-modified"),
        "etag_http": entetes.get("etag"),
        "octets_http": entetes.get("content-length"),
        "sha256_export": sha_export,
        "nombre_enregistrements_export_complet": len(enregistrements),
        "nombre_services_locaux": len(services),
        "nombre_relations": len(relations),
        "partitions_entites": partitions_entites,
        "partitions_relations": partitions_relations,
        "competence_geographique": {
            "dataset": "api-lannuaire-administration-locale-competence-geographique",
            "mode": "interrogation_live",
        },
    }
    MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
    MANIFESTE.write_text(
        json.dumps(manifeste, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {"etat": "actualise", "manifest": manifeste, "stats": stats}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingère les services locaux de l'API Annuaire de l'administration."
    )
    parser.add_argument("--source", default=URL_SOURCE, help="URL de l'export JSON.")
    parser.add_argument(
        "--fichier",
        type=Path,
        help="Export JSON local à utiliser à la place du téléchargement.",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="frontiere-annuaire-") as temp:
        if args.fichier:
            export_json = args.fichier
            entetes: dict[str, str] = {}
        else:
            export_json = Path(temp) / NOM_SOURCE
            entetes = telecharger(args.source, export_json)

        resultat = executer(export_json, entetes)

    stats = resultat["stats"]
    print(
        json.dumps(
            {
                "etat": resultat["etat"],
                "export_complet": stats["nombre_enregistrements_export_complet"],
                "services_locaux": stats["nombre_services_locaux_source"],
                "relations": stats["nombre_relations_hierarchiques"],
                "parents_principaux": stats["hierarchie"]["avec_parent_principal"],
                "anomalies_hierarchie": stats["hierarchie"]["anomalies"],
                "anomalies_roae_resolues": stats["resolution_croisee_roae"][
                    "resolues_par_annuaire_local"
                ],
                "octets_canonique": stats["stockage"]["octets_total_canonique"],
                "sha256_export": resultat["manifest"]["sha256_export"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
