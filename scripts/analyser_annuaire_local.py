from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import resource
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Iterable, Iterator

RACINE = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == "scripts" else Path.cwd()
METADATA_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "service-public-gouv-fr-annuaire-de-ladministration-base-de-donnees-locales/"
)
RESOURCE_ID = "73302880-e4df-4d4c-8676-1a61bb997f3d"
SOURCE_ID = "dila_annuaire_local"
VERSION_RAPPORT = "1.0"
USER_AGENT = "FRONTIERE-referentiel-institutionnel/1.0"

DOSSIER_ROAE = RACINE / "institutionnel" / "entites" / "roae"
ANOMALIES_ROAE = RACINE / "institutionnel" / "anomalies_roae.json"
DOSSIER_ANALYSES = RACINE / "institutionnel" / "analyses"

TAILLE_BLOC = 1024 * 1024
LIMITE_TELECHARGEMENT = 1_000_000_000
LIMITE_TAMPON_JSON = 64 * 1024 * 1024
LIMITE_ZIP_COMMUNES = 1_000_000_000
LIMITE_FICHIER_COMMUNE = 4 * 1024 * 1024

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

CHAMPS_TECHNIQUES_CANDIDATS = {
    "date_diffusion",
    "version_type",
    "version_etat_modification",
    "version_source",
}


class ErreurAnalyse(RuntimeError):
    """Erreur explicite lors de la caractérisation d'une archive DILA."""


def maintenant_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def liste(valeur: Any) -> list[Any]:
    if valeur is None or valeur == "":
        return []
    return valeur if isinstance(valeur, list) else [valeur]


def texte(valeur: Any) -> str | None:
    if valeur is None:
        return None
    resultat = str(valeur).strip()
    return resultat or None


def compact_sha256(objet: Any) -> str:
    brut = json.dumps(
        objet,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def empreinte_semantique_candidate(service: dict[str, Any]) -> str:
    copie = {
        cle: valeur
        for cle, valeur in service.items()
        if cle not in CHAMPS_TECHNIQUES_CANDIDATS
    }
    return compact_sha256(copie)


def candidats_id(objet: Any) -> Iterable[str]:
    """Extrait uniquement des UUID explicites, sans rapprochement de nom."""
    if isinstance(objet, str):
        candidat = objet.strip()
        if UUID_RE.match(candidat):
            yield candidat
        return

    if isinstance(objet, dict):
        for cle, valeur in objet.items():
            if (
                cle.lower()
                in {
                    "id",
                    "ids",
                    "identifiant",
                    "id_service",
                    "service_id",
                    "identifiant_service",
                }
                and isinstance(valeur, str)
                and UUID_RE.match(valeur.strip())
            ):
                yield valeur.strip()
            if isinstance(valeur, (dict, list)):
                yield from candidats_id(valeur)
        return

    if isinstance(objet, list):
        for valeur in objet:
            yield from candidats_id(valeur)


def _lire_plus(
    fichier: io.TextIOBase,
    tampon: str,
    position: int,
    fin: bool,
    taille_bloc: int,
) -> tuple[str, int, bool]:
    if fin:
        return tampon, position, fin

    if position:
        tampon = tampon[position:]
        position = 0

    morceau = fichier.read(taille_bloc)
    if morceau == "":
        return tampon, position, True
    return tampon + morceau, position, False


def iter_tableau_json(
    flux_binaire: BinaryIO,
    *,
    taille_bloc: int = TAILLE_BLOC,
    limite_tampon: int = LIMITE_TAMPON_JSON,
) -> Iterator[dict[str, Any]]:
    """Parcourt un tableau JSON de premier niveau sans charger le fichier entier.

    La spécification DILA décrit un fichier JSON contenant l'ensemble des guichets.
    L'analyse refuse explicitement une structure de premier niveau différente afin
    qu'une évolution de format soit détectée au lieu d'être interprétée silencieusement.
    """

    decodeur = json.JSONDecoder()
    texte_flux = io.TextIOWrapper(flux_binaire, encoding="utf-8-sig", newline="")
    tampon = ""
    position = 0
    fin = False
    demarre = False
    termine = False

    while True:
        while True:
            while position < len(tampon) and tampon[position].isspace():
                position += 1

            if position < len(tampon):
                break
            if fin:
                break
            tampon, position, fin = _lire_plus(
                texte_flux, tampon, position, fin, taille_bloc
            )

        if not demarre:
            if position >= len(tampon):
                raise ErreurAnalyse("Fichier JSON vide.")
            if tampon[position] != "[":
                raise ErreurAnalyse(
                    "La ressource DILA n'est pas un tableau JSON de premier niveau. "
                    "Le format doit être réexaminé avant ingestion."
                )
            demarre = True
            position += 1
            continue

        while True:
            while position < len(tampon) and tampon[position].isspace():
                position += 1
            if position < len(tampon):
                break
            if fin:
                raise ErreurAnalyse("Tableau JSON tronqué avant son crochet fermant.")
            tampon, position, fin = _lire_plus(
                texte_flux, tampon, position, fin, taille_bloc
            )

        if tampon[position] == "]":
            termine = True
            position += 1
            break

        try:
            objet, fin_objet = decodeur.raw_decode(tampon, position)
        except json.JSONDecodeError as exc:
            if fin:
                raise ErreurAnalyse(
                    f"JSON invalide ou tronqué près de la position {exc.pos}."
                ) from exc
            if len(tampon) - position > limite_tampon:
                raise ErreurAnalyse(
                    "Un enregistrement JSON dépasse la limite de tampon autorisée."
                ) from exc
            tampon, position, fin = _lire_plus(
                texte_flux, tampon, position, fin, taille_bloc
            )
            continue

        if not isinstance(objet, dict):
            raise ErreurAnalyse("Chaque élément du tableau DILA doit être un objet JSON.")
        yield objet
        position = fin_objet

        while True:
            while position < len(tampon) and tampon[position].isspace():
                position += 1
            if position < len(tampon):
                break
            if fin:
                raise ErreurAnalyse("Tableau JSON tronqué après un enregistrement.")
            tampon, position, fin = _lire_plus(
                texte_flux, tampon, position, fin, taille_bloc
            )

        if tampon[position] == ",":
            position += 1
            continue
        if tampon[position] == "]":
            termine = True
            position += 1
            break
        raise ErreurAnalyse("Séparateur JSON inattendu entre deux guichets.")

    if not termine:
        raise ErreurAnalyse("Tableau JSON non terminé.")

    reste = tampon[position:] + texte_flux.read()
    if reste.strip():
        raise ErreurAnalyse("Contenu inattendu après le tableau JSON principal.")


def nom_archive_sur(nom: str) -> bool:
    chemin = PurePosixPath(nom)
    if chemin.is_absolute() or ".." in chemin.parts:
        return False
    return bool(chemin.parts) and all(part not in {"", "."} for part in chemin.parts)


def verifier_membre_tar(membre: tarfile.TarInfo) -> None:
    if not nom_archive_sur(membre.name):
        raise ErreurAnalyse(f"Chemin TAR dangereux ou invalide: {membre.name!r}")
    if membre.issym() or membre.islnk():
        raise ErreurAnalyse(f"Lien symbolique/interne interdit dans le TAR: {membre.name!r}")


def verifier_nom_zip(nom: str) -> None:
    if not nom_archive_sur(nom):
        raise ErreurAnalyse(f"Chemin ZIP dangereux ou invalide: {nom!r}")


def decouvrir_ressource() -> dict[str, Any]:
    requete = urllib.request.Request(
        METADATA_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(requete, timeout=60) as reponse:
        donnees = json.load(reponse)

    ressources = donnees.get("resources") if isinstance(donnees, dict) else None
    if not isinstance(ressources, list):
        raise ErreurAnalyse("Métadonnées data.gouv.fr sans liste de ressources.")

    correspondances = [r for r in ressources if r.get("id") == RESOURCE_ID]
    if len(correspondances) != 1:
        raise ErreurAnalyse(
            f"Ressource DILA {RESOURCE_ID} absente ou dupliquée dans les métadonnées."
        )

    ressource = correspondances[0]
    adresse = texte(ressource.get("url"))
    if not adresse or not adresse.lower().endswith("all_latest.tar.bz2"):
        raise ErreurAnalyse(
            "L'adresse longue de la ressource DILA ne correspond plus à all_latest.tar.bz2."
        )

    return {
        "dataset_id": donnees.get("id"),
        "dataset_titre": donnees.get("title"),
        "dataset_derniere_mise_a_jour": donnees.get("last_update"),
        "ressource_id": RESOURCE_ID,
        "ressource_titre": ressource.get("title"),
        "url_longue": adresse,
        "url_stable_data_gouv": ressource.get("latest"),
        "derniere_modification_metadata": ressource.get("last_modified"),
        "format": ressource.get("format"),
        "licence": donnees.get("license"),
        "producteur": "Service-Public.gouv.fr / DILA",
    }


def telecharger_archive(
    adresse: str,
    destination: Path,
    *,
    limite_octets: int = LIMITE_TELECHARGEMENT,
) -> dict[str, Any]:
    requete = urllib.request.Request(
        adresse,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream,*/*",
        },
    )
    empreinte = hashlib.sha256()
    octets = 0

    with urllib.request.urlopen(requete, timeout=180) as reponse:
        longueur = reponse.headers.get("Content-Length")
        if longueur and longueur.isdigit() and int(longueur) > limite_octets:
            raise ErreurAnalyse(
                f"Archive annoncée à {longueur} octets, au-delà de la limite de sécurité."
            )

        with destination.open("wb") as sortie:
            while True:
                bloc = reponse.read(TAILLE_BLOC)
                if not bloc:
                    break
                octets += len(bloc)
                if octets > limite_octets:
                    raise ErreurAnalyse("Archive téléchargée au-delà de la limite de sécurité.")
                empreinte.update(bloc)
                sortie.write(bloc)

        return {
            "url_effective": reponse.geturl(),
            "content_length": longueur,
            "last_modified_http": reponse.headers.get("Last-Modified"),
            "etag": reponse.headers.get("ETag"),
            "octets": octets,
            "sha256": empreinte.hexdigest(),
        }


def charger_index_roae(dossier: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    if not dossier.exists():
        return index

    for chemin in sorted(dossier.glob("*.jsonl")):
        with chemin.open("r", encoding="utf-8") as fichier:
            for numero, ligne in enumerate(fichier, start=1):
                if not ligne.strip():
                    continue
                objet = json.loads(ligne)
                identifiants = objet.get("identifiants")
                dila_id = (
                    texte(identifiants.get("dila_id"))
                    if isinstance(identifiants, dict)
                    else None
                )
                if not dila_id:
                    raise ErreurAnalyse(
                        f"Entité ROAE sans dila_id dans {chemin}:{numero}."
                    )
                if dila_id in index:
                    raise ErreurAnalyse(f"dila_id ROAE dupliqué: {dila_id}")
                provenance = objet.get("provenance")
                empreinte_source = None
                if isinstance(provenance, list) and provenance and isinstance(provenance[0], dict):
                    empreinte_source = provenance[0].get("empreinte")
                index[dila_id] = {
                    "id_canonique": objet.get("id"),
                    "nom": objet.get("nom_officiel"),
                    "categorie": (objet.get("metadata_dila") or {}).get("categorie")
                    if isinstance(objet.get("metadata_dila"), dict)
                    else None,
                    "siren": identifiants.get("siren") if isinstance(identifiants, dict) else None,
                    "siret": identifiants.get("siret") if isinstance(identifiants, dict) else None,
                    "empreinte_source": empreinte_source,
                }
    return index


def charger_anomalies(chemin: Path) -> list[dict[str, Any]]:
    if not chemin.exists():
        return []
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    anomalies = donnees.get("liens_hierarchiques_non_resolus")
    if not isinstance(anomalies, list):
        raise ErreurAnalyse("Format inattendu du registre des anomalies ROAE.")
    return [a for a in anomalies if isinstance(a, dict)]


def distribution(counter: Counter[str], *, limite: int | None = None) -> dict[str, int]:
    elements = counter.most_common(limite)
    return {cle: valeur for cle, valeur in elements}


def _presence(valeur: Any) -> bool:
    if valeur is None:
        return False
    if isinstance(valeur, str):
        return bool(valeur.strip())
    if isinstance(valeur, (list, dict, tuple, set)):
        return bool(valeur)
    return True


def _coordonnees_geographiques(service: dict[str, Any]) -> bool:
    for adresse in liste(service.get("adresse")):
        if not isinstance(adresse, dict):
            continue
        longitude = adresse.get("longitude", adresse.get("Longitude"))
        latitude = adresse.get("latitude", adresse.get("Latitude"))
        if _presence(longitude) and _presence(latitude):
            return True
    return False


def _date_source(valeur: Any) -> str | None:
    chaine = texte(valeur)
    if not chaine:
        return None
    correspondance = re.match(r"^(\d{2})/(\d{2})/(\d{4})", chaine)
    if correspondance:
        jour, mois, annee = correspondance.groups()
        return f"{annee}-{mois}-{jour}"
    correspondance = re.match(r"^(\d{4})-(\d{2})-(\d{2})", chaine)
    if correspondance:
        return "-".join(correspondance.groups())
    return None


def _empreinte_agregee(index: dict[str, dict[str, Any]], cle: str) -> str:
    h = hashlib.sha256()
    for identifiant in sorted(index):
        h.update(identifiant.encode("utf-8"))
        h.update(b"\0")
        h.update(str(index[identifiant][cle]).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def analyser_guichets(
    flux: BinaryIO,
    roae: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[tuple[str, str, str]]]:
    index: dict[str, dict[str, Any]] = {}
    doublons: list[dict[str, Any]] = []
    liens: list[tuple[str, str, str]] = []

    categories: Counter[str] = Counter()
    repertoires: Counter[str] = Counter()
    organismes: Counter[str] = Counter()
    types_locaux: Counter[str] = Counter()
    dates_diffusion: Counter[str] = Counter()
    dates_modification: Counter[str] = Counter()

    couverture = Counter()
    nombre = 0
    liens_declares = 0

    for service in iter_tableau_json(flux):
        nombre += 1
        identifiant = texte(service.get("id"))
        nom = texte(service.get("nom"))
        if not identifiant or not nom:
            raise ErreurAnalyse(f"Guichet #{nombre} sans id ou nom.")

        brut = compact_sha256(service)
        semantique = empreinte_semantique_candidate(service)

        types_service = sorted(
            {
                valeur
                for pivot in liste(service.get("pivot"))
                if isinstance(pivot, dict)
                for valeur in [texte(pivot.get("type_service_local"))]
                if valeur
            }
        )

        courant = {
            "id": identifiant,
            "nom": nom,
            "categorie": texte(service.get("categorie")),
            "type_repertoire": texte(service.get("type_repertoire")),
            "type_organisme": texte(service.get("type_organisme")),
            "types_service_local": types_service,
            "siren": texte(service.get("siren")),
            "siret": texte(service.get("siret")),
            "empreinte_brute": brut,
            "empreinte_semantique_candidate": semantique,
        }

        precedent = index.get(identifiant)
        if precedent is not None:
            doublons.append(
                {
                    "id": identifiant,
                    "nom_premiere_occurrence": precedent.get("nom"),
                    "nom_occurrence_suivante": nom,
                    "empreinte_identique": precedent.get("empreinte_brute") == brut,
                }
            )
        else:
            index[identifiant] = courant

        for cle, compteur in (
            ("categorie", categories),
            ("type_repertoire", repertoires),
            ("type_organisme", organismes),
        ):
            valeur = texte(service.get(cle))
            if valeur:
                compteur[valeur] += 1
        for valeur in types_service:
            types_locaux[valeur] += 1

        for cle in ("siren", "siret", "mission", "texte_reference", "affectation_personne"):
            if _presence(service.get(cle)):
                couverture[f"avec_{cle}"] += 1
        if _presence(service.get("adresse")):
            couverture["avec_adresse"] += 1
        if _coordonnees_geographiques(service):
            couverture["avec_coordonnees_geographiques"] += 1

        date_diffusion = _date_source(service.get("date_diffusion"))
        if date_diffusion:
            dates_diffusion[date_diffusion] += 1
        date_modification = _date_source(service.get("date_modification"))
        if date_modification:
            dates_modification[date_modification] += 1

        for lien in liste(service.get("hierarchie")):
            if not isinstance(lien, dict):
                continue
            type_hierarchie = texte(lien.get("type_hierarchie")) or texte(lien.get("type")) or "HIERARCHIE_DILA"
            cibles = sorted(set(candidats_id(lien.get("service", lien))))
            for cible in cibles:
                if cible != identifiant:
                    liens_declares += 1
                    liens.append((cible, identifiant, type_hierarchie))

    recouvrements = []
    for identifiant in sorted(set(index) & set(roae)):
        local = index[identifiant]
        central = roae[identifiant]
        recouvrements.append(
            {
                "dila_id": identifiant,
                "local": {
                    "nom": local.get("nom"),
                    "categorie": local.get("categorie"),
                    "siren": local.get("siren"),
                    "siret": local.get("siret"),
                    "empreinte_source": local.get("empreinte_brute"),
                },
                "roae": {
                    "id_canonique": central.get("id_canonique"),
                    "nom": central.get("nom"),
                    "categorie": central.get("categorie"),
                    "siren": central.get("siren"),
                    "siret": central.get("siret"),
                    "empreinte_source": central.get("empreinte_source"),
                },
                "nom_identique": local.get("nom") == central.get("nom"),
                "siren_compatible": (
                    not local.get("siren")
                    or not central.get("siren")
                    or local.get("siren") == central.get("siren")
                ),
                "siret_compatible": (
                    not local.get("siret")
                    or not central.get("siret")
                    or local.get("siret") == central.get("siret")
                ),
            }
        )

    ids_locaux = set(index)
    ids_roae = set(roae)
    local_local = 0
    local_roae_hors_local = 0
    cible_locale_et_roae = 0
    non_resolus = 0
    for cible, _parent, _type in liens:
        dans_local = cible in ids_locaux
        dans_roae = cible in ids_roae
        if dans_local:
            local_local += 1
            if dans_roae:
                cible_locale_et_roae += 1
        elif dans_roae:
            local_roae_hors_local += 1
        else:
            non_resolus += 1

    stats = {
        "nombre_guichets_source": nombre,
        "nombre_ids_uniques": len(index),
        "nombre_occurrences_dupliquees": len(doublons),
        "doublons": doublons,
        "distributions": {
            "categorie": distribution(categories),
            "type_repertoire": distribution(repertoires),
            "type_organisme": distribution(organismes),
            "type_service_local": distribution(types_locaux),
        },
        "couverture": dict(sorted(couverture.items())),
        "hierarchie": {
            "liens_declares_avec_id_explicite": liens_declares,
            "liens_local_local": local_local,
            "liens_local_roae_hors_local": local_roae_hors_local,
            "liens_cible_locale_et_roae": cible_locale_et_roae,
            "liens_non_resolus": non_resolus,
        },
        "temporalite": {
            "dates_diffusion": distribution(dates_diffusion, limite=30),
            "dates_modification": distribution(dates_modification, limite=30),
            "champs_exclus_empreinte_semantique_candidate": sorted(
                CHAMPS_TECHNIQUES_CANDIDATS
            ),
            "empreinte_agregee_brute": _empreinte_agregee(index, "empreinte_brute"),
            "empreinte_agregee_semantique_candidate": _empreinte_agregee(
                index, "empreinte_semantique_candidate"
            ),
            "interpretation": (
                "Les deux empreintes permettent une comparaison entre observations. "
                "Une seule observation ne permet pas d'établir qu'un champ change quotidiennement."
            ),
        },
        "croisement_roae": {
            "nombre_ids_roae": len(roae),
            "nombre_recouvrements_ids_exacts": len(recouvrements),
            "recouvrements": recouvrements,
        },
    }
    return stats, index, liens


def _copier_flux_borne(flux: BinaryIO, destination: Path, limite: int) -> int:
    total = 0
    with destination.open("wb") as sortie:
        while True:
            bloc = flux.read(TAILLE_BLOC)
            if not bloc:
                break
            total += len(bloc)
            if total > limite:
                raise ErreurAnalyse("Membre d'archive au-delà de la limite de sécurité.")
            sortie.write(bloc)
    return total


def analyser_competences_communes(chemin_zip: Path) -> dict[str, Any]:
    nombre_fichiers = 0
    codes_insee: set[str] = set()
    associations = 0
    types: Counter[str] = Counter()
    organismes_distincts: set[str] = set()
    fichiers_sans_code = 0

    with zipfile.ZipFile(chemin_zip) as archive:
        infos = archive.infolist()
        for info in infos:
            verifier_nom_zip(info.filename)
            if info.is_dir():
                continue
            if not info.filename.lower().endswith(".json"):
                continue
            if info.file_size > LIMITE_FICHIER_COMMUNE:
                raise ErreurAnalyse(
                    f"Fichier communal anormalement volumineux: {info.filename}"
                )

            brut = archive.read(info)
            donnees = json.loads(brut.decode("utf-8-sig"))
            if not isinstance(donnees, dict):
                raise ErreurAnalyse(f"Fichier communal non objet: {info.filename}")

            nombre_fichiers += 1
            code = texte(donnees.get("code_insee_commune"))
            if code:
                codes_insee.add(code)
            else:
                fichiers_sans_code += 1

            groupes = donnees.get("type_service_local")
            if groupes is None:
                groupes = donnees.get("Type_service_local")
            for groupe in liste(groupes):
                if not isinstance(groupe, dict):
                    continue
                code_type = texte(groupe.get("code_type_service_local")) or "INCONNU"
                orgs = liste(groupe.get("organisme"))
                for organisme in orgs:
                    identifiant = None
                    if isinstance(organisme, str):
                        identifiant = texte(organisme)
                    elif isinstance(organisme, dict):
                        identifiant = next(iter(candidats_id(organisme)), None)
                        identifiant = identifiant or texte(organisme.get("id")) or texte(organisme.get("identifiant"))
                    if identifiant:
                        associations += 1
                        types[code_type] += 1
                        organismes_distincts.add(identifiant)

    return {
        "nombre_fichiers_communes": nombre_fichiers,
        "nombre_codes_insee_distincts": len(codes_insee),
        "nombre_fichiers_sans_code_insee": fichiers_sans_code,
        "nombre_associations_competence": associations,
        "nombre_organismes_distincts_references": len(organismes_distincts),
        "types_service_local": distribution(types),
    }


def resoudre_anomalies_roae(
    anomalies: list[dict[str, Any]],
    index_local: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    resolus = []
    a_examiner = []
    absents = []

    ids_locaux = set(index_local)
    for numero, anomalie in enumerate(anomalies, start=1):
        candidats = [
            str(c).strip()
            for c in liste(anomalie.get("candidats_id"))
            if texte(c)
        ]
        trouves = sorted(set(candidats) & ids_locaux)
        entree = {
            "index_anomalie": numero,
            "parent_id_dila": anomalie.get("parent_id_dila"),
            "parent_nom": anomalie.get("parent_nom"),
            "type_hierarchie_dila": anomalie.get("type_hierarchie_dila"),
            "candidats_id": candidats,
            "candidats_locaux_trouves": [
                {
                    "dila_id": identifiant,
                    "nom": index_local[identifiant].get("nom"),
                    "categorie": index_local[identifiant].get("categorie"),
                    "types_service_local": index_local[identifiant].get("types_service_local", []),
                }
                for identifiant in trouves
            ],
        }
        if len(trouves) == 1:
            resolus.append(entree)
        elif len(trouves) > 1:
            a_examiner.append(entree)
        else:
            absents.append(entree)

    return {
        "nombre_anomalies_source": len(anomalies),
        "nombre_resolues_exactement_par_un_id_local": len(resolus),
        "nombre_a_examiner": len(a_examiner),
        "nombre_toujours_absentes": len(absents),
        "resolues": resolus,
        "a_examiner": a_examiner,
        "absentes": absents,
    }


def analyser_archive(
    chemin_archive: Path,
    *,
    roae: dict[str, dict[str, Any]],
    anomalies: list[dict[str, Any]],
    source: dict[str, Any] | None = None,
    telechargement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    debut = time.monotonic()
    observe_le = maintenant_iso()

    json_membre: tarfile.TarInfo | None = None
    zip_membre: tarfile.TarInfo | None = None
    membres_resume = []

    with tarfile.open(chemin_archive, mode="r:bz2") as archive:
        for membre in archive.getmembers():
            verifier_membre_tar(membre)
            if membre.isdir():
                continue
            if not membre.isfile():
                raise ErreurAnalyse(f"Type de membre TAR non supporté: {membre.name}")
            membres_resume.append({"nom": membre.name, "octets": membre.size})
            nom = membre.name.lower()
            if nom.endswith("data.gouv_local.json"):
                if json_membre is not None:
                    raise ErreurAnalyse("Plusieurs fichiers JSON principaux détectés.")
                json_membre = membre
            elif nom.endswith("data.gouv.commune.zip"):
                if zip_membre is not None:
                    raise ErreurAnalyse("Plusieurs ZIP communaux détectés.")
                zip_membre = membre

        if json_membre is None or zip_membre is None:
            raise ErreurAnalyse(
                "Archive inattendue: fichier JSON principal ou ZIP communal absent."
            )

        flux_json = archive.extractfile(json_membre)
        if flux_json is None:
            raise ErreurAnalyse("Impossible d'ouvrir le JSON principal du TAR.")
        stats_guichets, index_local, _liens = analyser_guichets(flux_json, roae)

        flux_zip = archive.extractfile(zip_membre)
        if flux_zip is None:
            raise ErreurAnalyse("Impossible d'ouvrir le ZIP communal du TAR.")

        with tempfile.TemporaryDirectory(prefix="frontiere-annuaire-local-") as dossier_tmp:
            chemin_zip = Path(dossier_tmp) / "communes.zip"
            taille_zip = _copier_flux_borne(flux_zip, chemin_zip, LIMITE_ZIP_COMMUNES)
            stats_communes = analyser_competences_communes(chemin_zip)

    resolution_anomalies = resoudre_anomalies_roae(anomalies, index_local)

    duree = time.monotonic() - debut
    pic = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    pic_octets = int(pic if sys.platform == "darwin" else pic * 1024)

    sha_archive = None
    octets_archive = chemin_archive.stat().st_size
    if telechargement:
        sha_archive = telechargement.get("sha256")
    if not sha_archive:
        h = hashlib.sha256()
        with chemin_archive.open("rb") as fichier:
            for bloc in iter(lambda: fichier.read(TAILLE_BLOC), b""):
                h.update(bloc)
        sha_archive = h.hexdigest()

    return {
        "version_rapport": VERSION_RAPPORT,
        "source_id": SOURCE_ID,
        "observe_le": observe_le,
        "source": source or {},
        "archive": {
            "chemin_analyse": chemin_archive.name,
            "octets_compresse": octets_archive,
            "sha256": sha_archive,
            "telechargement": telechargement or {},
        },
        "structure_archive": {
            "membres": membres_resume,
            "json_principal": json_membre.name,
            "json_principal_octets_decompresses": json_membre.size,
            "zip_communes": zip_membre.name,
            "zip_communes_octets": taille_zip,
        },
        "guichets": stats_guichets,
        "resolution_anomalies_roae": resolution_anomalies,
        "competence_geographique": stats_communes,
        "performance": {
            "duree_secondes": round(duree, 3),
            "memoire_maximale_octets": pic_octets,
        },
        "doctrine": {
            "aucune_fusion_par_nom": True,
            "aucune_ecriture_canonique": True,
            "rapport_descriptif_seulement": True,
            "note": (
                "Cette caractérisation mesure le contenu et les croisements exacts. "
                "Elle ne modifie ni les entités ROAE ni leur registre d'anomalies."
            ),
        },
    }


def choisir_sortie(rapport: dict[str, Any], argument: Path | None) -> Path:
    if argument is not None:
        return argument
    nom_json = rapport.get("structure_archive", {}).get("json_principal", "")
    correspondance = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(nom_json))
    date = "".join(correspondance.groups()) if correspondance else datetime.now(timezone.utc).strftime("%Y%m%d")
    return DOSSIER_ANALYSES / f"annuaire_local_{date}.json"


def parser_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Caractérise la base locale DILA sans écrire d'entités canoniques."
    )
    parser.add_argument(
        "--archive",
        type=Path,
        help="Archive all_latest.tar.bz2 locale. Sans cet argument, la ressource officielle est découverte et téléchargée.",
    )
    parser.add_argument("--sortie", type=Path, help="Chemin du rapport JSON produit.")
    parser.add_argument("--roae-dir", type=Path, default=DOSSIER_ROAE)
    parser.add_argument("--anomalies-roae", type=Path, default=ANOMALIES_ROAE)
    return parser.parse_args()


def main() -> int:
    args = parser_arguments()
    roae = charger_index_roae(args.roae_dir)
    anomalies = charger_anomalies(args.anomalies_roae)

    source: dict[str, Any] = {}
    telechargement: dict[str, Any] = {}
    archive_temporaire: Path | None = None

    try:
        if args.archive:
            chemin_archive = args.archive.resolve()
            if not chemin_archive.is_file():
                raise ErreurAnalyse(f"Archive introuvable: {chemin_archive}")
        else:
            source = decouvrir_ressource()
            fd, nom_tmp = tempfile.mkstemp(prefix="frontiere-annuaire-local-", suffix=".tar.bz2")
            os.close(fd)
            archive_temporaire = Path(nom_tmp)
            telechargement = telecharger_archive(source["url_longue"], archive_temporaire)
            chemin_archive = archive_temporaire

        rapport = analyser_archive(
            chemin_archive,
            roae=roae,
            anomalies=anomalies,
            source=source,
            telechargement=telechargement,
        )
        sortie = choisir_sortie(rapport, args.sortie)
        sortie.parent.mkdir(parents=True, exist_ok=True)
        sortie.write_text(
            json.dumps(rapport, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        resume = {
            "sortie": str(sortie),
            "guichets": rapport["guichets"]["nombre_guichets_source"],
            "ids_uniques": rapport["guichets"]["nombre_ids_uniques"],
            "recouvrements_roae": rapport["guichets"]["croisement_roae"]["nombre_recouvrements_ids_exacts"],
            "orphelins_roae_resolus": rapport["resolution_anomalies_roae"]["nombre_resolues_exactement_par_un_id_local"],
            "liens_local_local": rapport["guichets"]["hierarchie"]["liens_local_local"],
            "liens_local_roae": rapport["guichets"]["hierarchie"]["liens_local_roae_hors_local"],
            "liens_non_resolus": rapport["guichets"]["hierarchie"]["liens_non_resolus"],
            "fichiers_communes": rapport["competence_geographique"]["nombre_fichiers_communes"],
            "codes_insee": rapport["competence_geographique"]["nombre_codes_insee_distincts"],
            "associations_competence": rapport["competence_geographique"]["nombre_associations_competence"],
            "json_decompresse_octets": rapport["structure_archive"]["json_principal_octets_decompresses"],
            "memoire_maximale_octets": rapport["performance"]["memoire_maximale_octets"],
            "duree_secondes": rapport["performance"]["duree_secondes"],
        }
        print(json.dumps(resume, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, tarfile.TarError, zipfile.BadZipFile, ErreurAnalyse) as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        return 2
    finally:
        if archive_temporaire is not None:
            archive_temporaire.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
