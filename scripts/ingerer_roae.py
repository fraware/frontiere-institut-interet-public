from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

RACINE = Path(__file__).resolve().parents[1]
URL_SOURCE = "https://echanges.dila.gouv.fr/OPENDATA/RefOrgaAdminEtat/FluxAnneeCourante/dila_refOrga_admin_Etat_fr_latest.zip"
PAGE_SOURCE = "https://www.data.gouv.fr/datasets/referentiel-de-lorganisation-administrative-de-letat"
NOM_SOURCE = "dila_refOrga_admin_Etat_fr_latest.zip"
SOURCE_ID = "dila_roae"

DOSSIER_ENTITES = RACINE / "institutionnel" / "entites" / "roae"
DOSSIER_RELATIONS = RACINE / "institutionnel" / "relations" / "roae"
MANIFESTE = RACINE / "institutionnel" / "instantanes" / "roae_manifest.json"
STATISTIQUES = RACINE / "institutionnel" / "statistiques_roae.json"

N_PARTITIONS_ENTITES = 32
N_PARTITIONS_RELATIONS = 16

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def maintenant_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def compact_sha256(objet: Any) -> str:
    brut = json.dumps(
        objet,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def lire_url(url: str) -> tuple[bytes, dict[str, str]]:
    requete = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FRONTIERE-referentiel-institutionnel/1.0",
            "Accept": "application/zip,application/octet-stream,*/*",
        },
    )
    with urllib.request.urlopen(requete, timeout=90) as reponse:
        contenu = reponse.read()
        entetes = {cle.lower(): valeur for cle, valeur in reponse.headers.items()}
    return contenu, entetes


def charger_services_depuis_zip(contenu_zip: bytes) -> tuple[list[dict[str, Any]], str]:
    with zipfile.ZipFile(io.BytesIO(contenu_zip)) as archive:
        noms = [nom for nom in archive.namelist() if nom.lower().endswith(".json")]
        if len(noms) != 1:
            raise ValueError(
                f"Le flux DILA doit contenir un fichier JSON unique, trouvé: {len(noms)}"
            )
        nom_json = noms[0]
        donnees = json.loads(archive.read(nom_json).decode("utf-8-sig"))

    services = trouver_liste_services(donnees)
    return services, nom_json


def trouver_liste_services(donnees: Any) -> list[dict[str, Any]]:
    if isinstance(donnees, list):
        services = [item for item in donnees if isinstance(item, dict)]
        if services:
            return services

    if isinstance(donnees, dict):
        for cle in ("services", "service", "results", "data", "items"):
            valeur = donnees.get(cle)
            if isinstance(valeur, list):
                services = [item for item in valeur if isinstance(item, dict)]
                if services:
                    return services

        listes = [
            valeur
            for valeur in donnees.values()
            if isinstance(valeur, list)
            and valeur
            and all(isinstance(item, dict) for item in valeur[:20])
        ]
        if listes:
            listes.sort(key=len, reverse=True)
            return listes[0]

    raise ValueError("Structure JSON DILA non reconnue.")


def liste(valeur: Any) -> list[Any]:
    if valeur is None or valeur == "":
        return []
    if isinstance(valeur, list):
        return valeur
    return [valeur]


def nettoyer_texte(valeur: Any) -> str | None:
    if valeur is None:
        return None
    texte = str(valeur).strip()
    return texte or None


def id_canonique(id_dila: str) -> str:
    nettoye = re.sub(r"[^A-Za-z0-9-]", "-", id_dila).upper()
    return f"FRONTIERE-INST-DILA-{nettoye}"


def valeurs_liens(valeur: Any) -> list[dict[str, Any]]:
    resultat = []
    for item in liste(valeur):
        if isinstance(item, dict):
            resultat.append(item)
        elif item not in (None, ""):
            resultat.append({"valeur": str(item)})
    return resultat


def normaliser_responsables(service: dict[str, Any], source_id: str) -> list[dict[str, Any]]:
    resultat = []
    for affectation in liste(service.get("affectation_personne")):
        if not isinstance(affectation, dict):
            continue
        personne = affectation.get("personne")
        if not isinstance(personne, dict):
            personne = {}
        textes = valeurs_liens(personne.get("texte_reference"))
        resultat.append(
            {
                "fonction": nettoyer_texte(affectation.get("fonction")) or "Fonction non précisée",
                "nom": nettoyer_texte(personne.get("nom")),
                "prenom": nettoyer_texte(personne.get("prenom")),
                "civilite": nettoyer_texte(personne.get("civilite")),
                "grade": nettoyer_texte(personne.get("grade")),
                "telephone": nettoyer_texte(affectation.get("telephone")),
                "adresses_courriel": valeurs_liens(personne.get("adresse_courriel")),
                "textes_reference": textes,
                "source_id": source_id,
                "valide_depuis": None,
                "valide_jusqua": None,
            }
        )
    return resultat


def normaliser_coordonnees(service: dict[str, Any]) -> list[dict[str, Any]]:
    resultat: list[dict[str, Any]] = []
    for adresse in liste(service.get("adresse")):
        if isinstance(adresse, dict):
            resultat.append({"type": "ADRESSE", **adresse})

    courriels = liste(service.get("adresse_courriel"))
    for courriel in courriels:
        if isinstance(courriel, dict):
            resultat.append({"type": "COURRIEL", **courriel})
        elif nettoyer_texte(courriel):
            resultat.append({"type": "COURRIEL", "valeur": nettoyer_texte(courriel)})

    for telephone in liste(service.get("telephone")):
        if isinstance(telephone, dict):
            resultat.append({"type": "TELEPHONE", **telephone})
        elif nettoyer_texte(telephone):
            resultat.append({"type": "TELEPHONE", "valeur": nettoyer_texte(telephone)})

    for site in valeurs_liens(service.get("site_internet")):
        resultat.append({"type": "SITE_INTERNET", **site})

    for formulaire in liste(service.get("formulaire_contact")):
        if isinstance(formulaire, dict):
            resultat.append({"type": "FORMULAIRE", **formulaire})
        elif nettoyer_texte(formulaire):
            resultat.append({"type": "FORMULAIRE", "valeur": nettoyer_texte(formulaire)})

    for sve in liste(service.get("sve")):
        if isinstance(sve, dict):
            resultat.append({"type": "SAISINE_ELECTRONIQUE", **sve})
        elif nettoyer_texte(sve):
            resultat.append({"type": "SAISINE_ELECTRONIQUE", "valeur": nettoyer_texte(sve)})

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


def aliases(service: dict[str, Any]) -> list[str]:
    resultat = []
    for valeur in liste(service.get("ancien_nom")):
        texte = nettoyer_texte(valeur)
        if texte and texte not in resultat:
            resultat.append(texte)
    return resultat


def canonicaliser_service(service: dict[str, Any], observe_le: str) -> dict[str, Any]:
    dila_id = nettoyer_texte(service.get("id"))
    nom = nettoyer_texte(service.get("nom"))
    if not dila_id or not nom:
        raise ValueError("Chaque service DILA doit posséder id et nom.")

    mission = nettoyer_texte(service.get("mission"))
    missions = []
    if mission:
        missions.append(
            {
                "texte": mission,
                "source_id": SOURCE_ID,
                "nature": "PUBLIEE",
                "valide_depuis": None,
                "valide_jusqua": None,
            }
        )

    identifiants = {
        "dila_id": dila_id,
        "itm_identifiant": nettoyer_texte(service.get("itm_identifiant")),
        "siren": nettoyer_texte(service.get("siren")),
        "siret": nettoyer_texte(service.get("siret")),
        "partenaire_identifiant": nettoyer_texte(service.get("partenaire_identifiant")),
        "ancien_identifiant": liste(service.get("ancien_identifiant")),
    }

    type_institutionnel = (
        nettoyer_texte(service.get("type_organisme"))
        or nettoyer_texte(service.get("type_repertoire"))
        or "Service institutionnel"
    )

    empreinte_service = compact_sha256(service)

    return {
        "id": id_canonique(dila_id),
        "nom_officiel": nom,
        "sigle": nettoyer_texte(service.get("sigle")),
        "aliases": aliases(service),
        "famille": "organisation_administrative_etat",
        "type_institutionnel": type_institutionnel,
        "nature_juridique": nettoyer_texte(service.get("type_organisme")),
        "personnalite_morale": None,
        "etat": "ACTIF" if service.get("statut_de_diffusion", True) else "INCONNU",
        "identifiants": identifiants,
        "parent_id": None,
        "tutelles": [],
        "territoires": [],
        "missions": missions,
        "responsables": normaliser_responsables(service, SOURCE_ID),
        "coordonnees": normaliser_coordonnees(service),
        "capacites": [],
        "fondements_juridiques": normaliser_textes(service),
        "budget": [],
        "provenance": [
            {
                "source_id": SOURCE_ID,
                "identifiant_source": dila_id,
                "url": nettoyer_texte(service.get("url_service_public")) or PAGE_SOURCE,
                "collecte_le": observe_le,
                "empreinte": empreinte_service,
            }
        ],
        "valide_depuis": None,
        "valide_jusqua": None,
        "observe_le": observe_le,
        "metadata_dila": {
            "categorie": service.get("categorie"),
            "type_repertoire": service.get("type_repertoire"),
            "date_creation": service.get("date_creation"),
            "date_modification": service.get("date_modification"),
            "date_diffusion": service.get("date_diffusion"),
            "version_type": service.get("version_type"),
            "version_source": service.get("version_source"),
            "version_etat_modification": service.get("version_etat_modification"),
            "partenaire": service.get("partenaire"),
            "partenaire_date_modification": service.get("partenaire_date_modification"),
        },
        "source_dila": service,
    }


def candidats_id(objet: Any) -> Iterable[str]:
    if isinstance(objet, str):
        if UUID_RE.match(objet.strip()):
            yield objet.strip()
        return

    if isinstance(objet, dict):
        for cle, valeur in objet.items():
            if cle.lower() in {
                "id",
                "ids",
                "identifiant",
                "id_service",
                "service_id",
                "identifiant_service",
            }:
                if isinstance(valeur, str) and UUID_RE.match(valeur.strip()):
                    yield valeur.strip()
            if isinstance(valeur, (dict, list)):
                yield from candidats_id(valeur)
        return

    if isinstance(objet, list):
        for valeur in objet:
            yield from candidats_id(valeur)


def relations_hierarchie(
    services: list[dict[str, Any]], observe_le: str
) -> tuple[list[dict[str, Any]], int]:
    ids = {
        str(service.get("id")).strip()
        for service in services
        if nettoyer_texte(service.get("id"))
    }
    relations: dict[tuple[str, str, str], dict[str, Any]] = {}
    liens_non_resolus = 0

    for parent in services:
        parent_dila = nettoyer_texte(parent.get("id"))
        if not parent_dila:
            continue

        for lien in liste(parent.get("hierarchie")):
            if not isinstance(lien, dict):
                liens_non_resolus += 1
                continue

            type_source = (
                nettoyer_texte(lien.get("type_hierarchie"))
                or nettoyer_texte(lien.get("type"))
                or "HIERARCHIE_DILA"
            )
            cibles = sorted(
                {
                    candidat
                    for candidat in candidats_id(lien.get("service", lien))
                    if candidat != parent_dila
                }
            )
            cibles_connues = [cible for cible in cibles if cible in ids]

            if not cibles_connues:
                liens_non_resolus += 1
                continue

            for enfant_dila in cibles_connues:
                cle = (enfant_dila, parent_dila, type_source)
                relation = {
                    "id": "FRONTIERE-REL-DILA-"
                    + hashlib.sha256("|".join(cle).encode("utf-8")).hexdigest()[:24].upper(),
                    "source_entite": id_canonique(enfant_dila),
                    "type_relation": "DEPEND_DE",
                    "cible_entite": id_canonique(parent_dila),
                    "qualificatifs": {
                        "type_hierarchie_dila": type_source,
                        "representation_source": lien,
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
                    "valide_depuis": None,
                    "valide_jusqua": None,
                    "observe_le": observe_le,
                    "statut_validation": "VALIDE",
                }
                relations[cle] = relation

    return sorted(relations.values(), key=lambda r: r["id"]), liens_non_resolus


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
        idx = index_partition(str(objet[cle_id]), nombre_partitions)
        partitions[idx].append(objet)

    manifeste = []
    for idx, items in enumerate(partitions):
        items.sort(key=lambda item: str(item[cle_id]))
        chemin = dossier / f"{prefixe}_{idx:02d}.jsonl"
        texte = "".join(
            json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for item in items
        )
        chemin.write_text(texte, encoding="utf-8")
        manifeste.append(
            {
                "fichier": str(chemin.relative_to(RACINE)),
                "nombre": len(items),
                "sha256": hashlib.sha256(texte.encode("utf-8")).hexdigest(),
                "octets": len(texte.encode("utf-8")),
            }
        )
    return manifeste


def statistiques(
    services: list[dict[str, Any]],
    entites: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    liens_non_resolus: int,
    observe_le: str,
) -> dict[str, Any]:
    types = Counter(
        nettoyer_texte(service.get("type_organisme"))
        or nettoyer_texte(service.get("type_repertoire"))
        or "Non précisé"
        for service in services
    )
    categories = Counter(
        nettoyer_texte(service.get("categorie")) or "Non précisée" for service in services
    )

    return {
        "version": "1",
        "source_id": SOURCE_ID,
        "observe_le": observe_le,
        "nombre_services_source": len(services),
        "nombre_entites_canoniques": len(entites),
        "nombre_relations_hierarchiques": len(relations),
        "liens_hierarchiques_non_resolus": liens_non_resolus,
        "couverture": {
            "avec_siren": sum(bool(e["identifiants"].get("siren")) for e in entites),
            "avec_siret": sum(bool(e["identifiants"].get("siret")) for e in entites),
            "avec_mission": sum(bool(e["missions"]) for e in entites),
            "avec_responsable": sum(bool(e["responsables"]) for e in entites),
            "avec_coordonnees": sum(bool(e["coordonnees"]) for e in entites),
            "avec_fondement_juridique": sum(bool(e["fondements_juridiques"]) for e in entites),
        },
        "categories_source": dict(categories.most_common()),
        "types_institutionnels_source": dict(types.most_common()),
    }


def executer(contenu_zip: bytes, entetes: dict[str, str], observe_le: str | None = None) -> dict[str, Any]:
    observe_le = observe_le or maintenant_iso()
    services, nom_json = charger_services_depuis_zip(contenu_zip)

    ids = [nettoyer_texte(service.get("id")) for service in services]
    ids_non_vides = [item for item in ids if item]
    if len(ids_non_vides) != len(services):
        raise ValueError("Le flux contient au moins un service sans identifiant.")
    if len(ids_non_vides) != len(set(ids_non_vides)):
        raise ValueError("Le flux contient des identifiants DILA en doublon.")

    entites = [canonicaliser_service(service, observe_le) for service in services]
    entites.sort(key=lambda item: item["id"])
    relations, non_resolus = relations_hierarchie(services, observe_le)

    partitions_entites = ecrire_jsonl_partitionne(
        entites,
        DOSSIER_ENTITES,
        "roae",
        N_PARTITIONS_ENTITES,
        "id",
    )
    partitions_relations = ecrire_jsonl_partitionne(
        relations,
        DOSSIER_RELATIONS,
        "roae_hierarchie",
        N_PARTITIONS_RELATIONS,
        "id",
    )

    stats = statistiques(services, entites, relations, non_resolus, observe_le)
    STATISTIQUES.parent.mkdir(parents=True, exist_ok=True)
    STATISTIQUES.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    manifeste = {
        "version": "1",
        "source_id": SOURCE_ID,
        "producteur": "Direction de l'information légale et administrative",
        "paternite": "Service-Public.gouv.fr / DILA",
        "licence": "Licence Ouverte 2.0",
        "page_source": PAGE_SOURCE,
        "url_telechargement_longue": URL_SOURCE,
        "nom_fichier_telecharge": NOM_SOURCE,
        "nom_fichier_json": nom_json,
        "observe_le": observe_le,
        "derniere_modification_http": entetes.get("last-modified"),
        "etag_http": entetes.get("etag"),
        "sha256_zip": hashlib.sha256(contenu_zip).hexdigest(),
        "octets_zip": len(contenu_zip),
        "nombre_services": len(services),
        "nombre_relations": len(relations),
        "partitions_entites": partitions_entites,
        "partitions_relations": partitions_relations,
    }
    MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
    MANIFESTE.write_text(
        json.dumps(manifeste, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {"manifest": manifeste, "stats": stats}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Télécharge et canonicalise le Référentiel de l'organisation administrative de l'État."
    )
    parser.add_argument(
        "--source",
        default=URL_SOURCE,
        help="URL du fichier ZIP DILA.",
    )
    args = parser.parse_args()

    contenu, entetes = lire_url(args.source)
    resultat = executer(contenu, entetes)

    print(
        json.dumps(
            {
                "services": resultat["manifest"]["nombre_services"],
                "relations": resultat["manifest"]["nombre_relations"],
                "liens_non_resolus": resultat["stats"]["liens_hierarchiques_non_resolus"],
                "sha256_zip": resultat["manifest"]["sha256_zip"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
