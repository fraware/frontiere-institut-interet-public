from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import tempfile
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

RACINE = Path(__file__).resolve().parents[1]

SOURCE_ID = "insee_cog"
MILLESIME = "2026"
VERSION_TRANSFORMATION = "1.0"

PAGE_SOURCE = "https://www.insee.fr/fr/information/8740222"
URL_SOURCE = (
    "https://www.insee.fr/fr/statistiques/fichier/8740222/"
    "cog_ensemble_2026_csv.zip"
)
NOM_SOURCE = "cog_ensemble_2026_csv.zip"

DOSSIER_TERRITOIRES = RACINE / "institutionnel" / "territoires" / "cog"
DOSSIER_RELATIONS = RACINE / "institutionnel" / "relations_territoriales" / "cog"
DOSSIER_EVENEMENTS = RACINE / "institutionnel" / "evenements" / "cog"
DOSSIER_ARCHIVES = RACINE / "institutionnel" / "archives" / "cog"
MANIFESTE = RACINE / "institutionnel" / "instantanes" / "cog_manifest.json"
STATISTIQUES = RACINE / "institutionnel" / "statistiques_cog.json"
ANOMALIES = RACINE / "institutionnel" / "anomalies_cog.json"

N_PARTITIONS_TERRITOIRES = 32
N_PARTITIONS_RELATIONS = 16
TAILLE_MAX_ARCHIVE = 25 * 1024 * 1024

FICHIERS_REQUIS = {
    "communes": f"v_commune_{MILLESIME}.csv",
    "cantons": f"v_canton_{MILLESIME}.csv",
    "arrondissements": f"v_arrondissement_{MILLESIME}.csv",
    "departements": f"v_departement_{MILLESIME}.csv",
    "regions": f"v_region_{MILLESIME}.csv",
    "ctcd": f"v_ctcd_{MILLESIME}.csv",
    "mouvements_communes": f"v_mvt_commune_{MILLESIME}.csv",
    "historique_communes": "v_commune_depuis_1943.csv",
    "comer": f"v_comer_{MILLESIME}.csv",
    "communes_comer": f"v_commune_comer_{MILLESIME}.csv",
}

TYPECOM_VERS_TYPE = {
    "COM": "COMMUNE",
    "ARM": "ARRONDISSEMENT_MUNICIPAL",
    "COMA": "COMMUNE_ASSOCIEE",
    "COMD": "COMMUNE_DELEGUEE",
}

PREFIXES = {
    "REGION": "REG",
    "DEPARTEMENT": "DEP",
    "CTCD": "CTCD",
    "ARRONDISSEMENT": "ARR",
    "CANTON": "CAN",
    "COMMUNE": "COM",
    "ARRONDISSEMENT_MUNICIPAL": "ARM",
    "COMMUNE_ASSOCIEE": "COMA",
    "COMMUNE_DELEGUEE": "COMD",
    "COLLECTIVITE_OUTRE_MER": "COMER",
    "ZONAGE_OUTRE_MER": "ZONE",
}

CODE_RE = re.compile(r"^[0-9A-Z]+$")


class ErreurCOG(RuntimeError):
    """Erreur explicite de validation ou d'ingestion du COG."""


def maintenant_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def nettoyer(valeur: Any) -> str | None:
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


def sha256_octets(contenu: bytes) -> str:
    return hashlib.sha256(contenu).hexdigest()


def sha256_fichier(chemin: Path) -> str:
    hachage = hashlib.sha256()
    with chemin.open("rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            hachage.update(bloc)
    return hachage.hexdigest()


def id_territoire(type_territoire: str, code: str, nature: str | None = None) -> str:
    code_nettoye = re.sub(r"[^A-Z0-9]", "-", code.upper())
    prefixe = PREFIXES[type_territoire]
    if type_territoire == "ZONAGE_OUTRE_MER" and nature:
        nature_nette = re.sub(r"[^A-Z0-9]", "-", nature.upper())
        return f"FRONTIERE-TERR-COG-{prefixe}-{nature_nette}-{code_nettoye}"
    return f"FRONTIERE-TERR-COG-{prefixe}-{code_nettoye}"


def identifiant_source(type_territoire: str, code: str, nature: str | None = None) -> str:
    if nature:
        return f"{MILLESIME}:{type_territoire}:{nature}:{code}"
    return f"{MILLESIME}:{type_territoire}:{code}"


def relation_id(
    source_id: str,
    cible_id: str,
    type_relation: str,
    qualificatif: str | None = None,
) -> str:
    cle = "|".join((source_id, type_relation, cible_id, qualificatif or ""))
    return "FRONTIERE-REL-TERR-COG-" + hashlib.sha256(
        cle.encode("utf-8")
    ).hexdigest()[:24].upper()


def evenement_id(index: int, ligne: dict[str, str]) -> str:
    cle = {
        "millesime": MILLESIME,
        "index": index,
        "ligne": ligne,
    }
    return "FRONTIERE-EVT-COG-" + compact_sha256(cle)[:24].upper()


def normaliser_ligne(ligne: dict[str, Any]) -> dict[str, str]:
    return {
        str(cle).strip().upper(): str(valeur).strip()
        for cle, valeur in ligne.items()
        if cle is not None and valeur is not None
    }


def valider_code(code: str, champ: str) -> str:
    code = code.strip().upper()
    if not code or not CODE_RE.fullmatch(code):
        raise ErreurCOG(f"Code {champ} invalide: {code!r}")
    return code


def trouver_membre(archive: zipfile.ZipFile, nom_attendu: str) -> zipfile.ZipInfo:
    candidats = [
        info
        for info in archive.infolist()
        if not info.is_dir() and Path(info.filename).name == nom_attendu
    ]
    if len(candidats) != 1:
        raise ErreurCOG(
            f"Le fichier {nom_attendu!r} doit apparaître exactement une fois; "
            f"trouvé: {len(candidats)}."
        )
    info = candidats[0]
    parties = Path(info.filename).parts
    if info.filename.startswith("/") or ".." in parties:
        raise ErreurCOG(f"Chemin ZIP dangereux: {info.filename!r}")
    return info


def lire_csv_zip(
    archive: zipfile.ZipFile,
    nom_attendu: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    info = trouver_membre(archive, nom_attendu)
    brut = archive.read(info)
    if b"\x00" in brut[:4096]:
        raise ErreurCOG(f"Contenu binaire inattendu dans {nom_attendu}.")

    texte = brut.decode("utf-8-sig")
    echantillon = texte[:8192]
    try:
        dialecte = csv.Sniffer().sniff(echantillon, delimiters=",;")
        delimiteur = dialecte.delimiter
    except csv.Error:
        delimiteur = ","

    lecteur = csv.DictReader(io.StringIO(texte, newline=""), delimiter=delimiteur)
    if lecteur.fieldnames is None:
        raise ErreurCOG(f"CSV sans en-tête: {nom_attendu}")

    lignes = [normaliser_ligne(ligne) for ligne in lecteur]
    return lignes, {
        "nom": info.filename,
        "octets": info.file_size,
        "sha256": sha256_octets(brut),
        "colonnes": [str(c).strip().upper() for c in lecteur.fieldnames],
        "nombre_lignes": len(lignes),
        "delimiteur": delimiteur,
    }


def exiger_colonnes(
    lignes: list[dict[str, str]],
    colonnes: Iterable[str],
    nom: str,
) -> None:
    if not lignes:
        raise ErreurCOG(f"Fichier COG vide: {nom}")
    presentes = set(lignes[0])
    manquantes = set(colonnes) - presentes
    if manquantes:
        raise ErreurCOG(
            f"Colonnes manquantes dans {nom}: {sorted(manquantes)}"
        )


def telecharger_archive(url: str, destination: Path) -> dict[str, Any]:
    requete = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FRONTIERE-referentiel-institutionnel/1.0",
            "Accept": "application/zip,application/octet-stream,*/*",
        },
    )
    hachage = hashlib.sha256()
    total = 0

    with urllib.request.urlopen(requete, timeout=120) as reponse:
        longueur = nettoyer(reponse.headers.get("Content-Length"))
        if longueur and longueur.isdigit() and int(longueur) > TAILLE_MAX_ARCHIVE:
            raise ErreurCOG(
                f"Archive COG annoncée à {longueur} octets, au-delà de la limite."
            )

        with destination.open("wb") as sortie:
            while True:
                bloc = reponse.read(1024 * 1024)
                if not bloc:
                    break
                total += len(bloc)
                if total > TAILLE_MAX_ARCHIVE:
                    raise ErreurCOG("Archive COG au-delà de la limite de sécurité.")
                hachage.update(bloc)
                sortie.write(bloc)

        return {
            "url_demandee": url,
            "url_effective": reponse.geturl(),
            "octets": total,
            "sha256": hachage.hexdigest(),
            "last_modified": reponse.headers.get("Last-Modified"),
            "etag": reponse.headers.get("ETag"),
            "content_type": reponse.headers.get("Content-Type"),
        }


def charger_index_jsonl(dossier: Path, cle: str = "id") -> dict[str, dict[str, Any]]:
    resultat: dict[str, dict[str, Any]] = {}
    if not dossier.exists():
        return resultat
    for chemin in sorted(dossier.glob("*.jsonl")):
        with chemin.open("r", encoding="utf-8") as fichier:
            for numero, ligne in enumerate(fichier, start=1):
                if not ligne.strip():
                    continue
                objet = json.loads(ligne)
                valeur = nettoyer(objet.get(cle))
                if not valeur:
                    raise ErreurCOG(f"{chemin}:{numero} sans {cle}.")
                if valeur in resultat:
                    raise ErreurCOG(f"Identifiant dupliqué dans le snapshot: {valeur}")
                resultat[valeur] = objet
    return resultat


def provenance_precedente(precedent: dict[str, Any] | None) -> dict[str, Any] | None:
    if not precedent:
        return None
    provenance = precedent.get("provenance")
    if isinstance(provenance, list) and provenance and isinstance(provenance[0], dict):
        return provenance[0]
    return None


def creer_territoire(
    *,
    type_territoire: str,
    code: str,
    ligne: dict[str, str],
    observe_le: str,
    precedent: dict[str, Any] | None,
    nature: str | None = None,
    parents: list[dict[str, Any]] | None = None,
    chef_lieu: str | None = None,
) -> dict[str, Any]:
    code = valider_code(code, type_territoire)
    identifiant = id_territoire(type_territoire, code, nature)
    empreinte = compact_sha256(ligne)
    precedente = provenance_precedente(precedent)
    inchange = bool(
        precedent
        and precedente
        and precedente.get("empreinte") == empreinte
    )
    observation = precedent.get("observe_le") if inchange else observe_le
    collecte = precedente.get("collecte_le") if inchange and precedente else observe_le

    nom = (
        nettoyer(ligne.get("LIBELLE"))
        or nettoyer(ligne.get("NCCENR"))
        or nettoyer(ligne.get("NCC"))
        or code
    )
    resultat = {
        "id": identifiant,
        "type_territoire": type_territoire,
        "code": code,
        "nom_officiel": nom,
        "etat": "ACTIF",
        "identifiants": {
            "insee_cog": code,
            "millesime": MILLESIME,
        },
        "parents": parents or [],
        "provenance": [
            {
                "source_id": SOURCE_ID,
                "identifiant_source": identifiant_source(
                    type_territoire,
                    code,
                    nature,
                ),
                "url": PAGE_SOURCE,
                "collecte_le": collecte,
                "empreinte": empreinte,
            }
        ],
        "observe_le": observation,
        "source_insee": ligne,
    }

    if nettoyer(ligne.get("NCCENR")):
        resultat["nom_enrichi"] = ligne["NCCENR"]
    if nettoyer(ligne.get("LIBELLE")):
        resultat["libelle"] = ligne["LIBELLE"]
    if chef_lieu:
        resultat["chef_lieu_code_commune"] = chef_lieu
    if nature:
        resultat["identifiants"]["nature_zonage"] = nature
    return resultat


def parent(type_relation: str, type_territoire: str, code: str, nature: str | None = None) -> dict[str, Any]:
    return {
        "type_relation": type_relation,
        "territoire_id": id_territoire(type_territoire, code, nature),
        "source_id": SOURCE_ID,
    }


def construire_territoires(
    donnees: dict[str, list[dict[str, str]]],
    observe_le: str,
    precedents: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    territoires: dict[str, dict[str, Any]] = {}
    anomalies: list[dict[str, Any]] = []
    compteurs = Counter()

    def ajouter(objet: dict[str, Any]) -> None:
        identifiant = objet["id"]
        if identifiant in territoires:
            raise ErreurCOG(f"Territoire canonique dupliqué: {identifiant}")
        territoires[identifiant] = objet
        compteurs[objet["type_territoire"]] += 1

    for ligne in donnees["regions"]:
        code = valider_code(ligne.get("REG", ""), "REG")
        objet = creer_territoire(
            type_territoire="REGION",
            code=code,
            ligne=ligne,
            observe_le=observe_le,
            precedent=precedents.get(id_territoire("REGION", code)),
            chef_lieu=nettoyer(ligne.get("CHEFLIEU")),
        )
        ajouter(objet)

    for ligne in donnees["departements"]:
        code = valider_code(ligne.get("DEP", ""), "DEP")
        parents = []
        if reg := nettoyer(ligne.get("REG")):
            parents.append(parent("APPARTIENT_A", "REGION", reg))
        objet = creer_territoire(
            type_territoire="DEPARTEMENT",
            code=code,
            ligne=ligne,
            observe_le=observe_le,
            precedent=precedents.get(id_territoire("DEPARTEMENT", code)),
            parents=parents,
            chef_lieu=nettoyer(ligne.get("CHEFLIEU")),
        )
        ajouter(objet)

    for ligne in donnees["ctcd"]:
        code = valider_code(ligne.get("CTCD", ""), "CTCD")
        parents = []
        if reg := nettoyer(ligne.get("REG")):
            parents.append(parent("APPARTIENT_A", "REGION", reg))
        objet = creer_territoire(
            type_territoire="CTCD",
            code=code,
            ligne=ligne,
            observe_le=observe_le,
            precedent=precedents.get(id_territoire("CTCD", code)),
            parents=parents,
            chef_lieu=nettoyer(ligne.get("CHEFLIEU")),
        )
        ajouter(objet)

    for ligne in donnees["arrondissements"]:
        code = valider_code(ligne.get("ARR", ""), "ARR")
        parents = []
        if dep := nettoyer(ligne.get("DEP")):
            parents.append(parent("APPARTIENT_A", "DEPARTEMENT", dep))
        if reg := nettoyer(ligne.get("REG")):
            parents.append(parent("APPARTIENT_A", "REGION", reg))
        objet = creer_territoire(
            type_territoire="ARRONDISSEMENT",
            code=code,
            ligne=ligne,
            observe_le=observe_le,
            precedent=precedents.get(id_territoire("ARRONDISSEMENT", code)),
            parents=parents,
            chef_lieu=nettoyer(ligne.get("CHEFLIEU")),
        )
        ajouter(objet)

    for ligne in donnees["cantons"]:
        code = valider_code(ligne.get("CAN", ""), "CAN")
        parents = []
        if dep := nettoyer(ligne.get("DEP")):
            parents.append(parent("APPARTIENT_A", "DEPARTEMENT", dep))
        if reg := nettoyer(ligne.get("REG")):
            parents.append(parent("APPARTIENT_A", "REGION", reg))
        objet = creer_territoire(
            type_territoire="CANTON",
            code=code,
            ligne=ligne,
            observe_le=observe_le,
            precedent=precedents.get(id_territoire("CANTON", code)),
            parents=parents,
            chef_lieu=nettoyer(ligne.get("BURCENTRAL")),
        )
        ajouter(objet)

    index_communes_principales = {
        ligne["COM"]: ligne
        for ligne in donnees["communes"]
        if ligne.get("TYPECOM") == "COM" and ligne.get("COM")
    }

    for ligne in donnees["communes"]:
        typecom = nettoyer(ligne.get("TYPECOM"))
        code = nettoyer(ligne.get("COM"))
        if not typecom or not code:
            raise ErreurCOG("Commune sans TYPECOM ou COM.")
        type_territoire = TYPECOM_VERS_TYPE.get(typecom)
        if not type_territoire:
            anomalies.append(
                {
                    "type": "TYPECOM_INCONNU",
                    "typecom": typecom,
                    "code": code,
                    "ligne": ligne,
                }
            )
            continue

        parents = []
        if dep := nettoyer(ligne.get("DEP")):
            parents.append(parent("APPARTIENT_A", "DEPARTEMENT", dep))
        if reg := nettoyer(ligne.get("REG")):
            parents.append(parent("APPARTIENT_A", "REGION", reg))
        if arr := nettoyer(ligne.get("ARR")):
            parents.append(parent("APPARTIENT_A", "ARRONDISSEMENT", arr))
        if ctcd := nettoyer(ligne.get("CTCD")):
            parents.append(parent("APPARTIENT_A", "CTCD", ctcd))
        if can := nettoyer(ligne.get("CAN")):
            parents.append(parent("APPARTIENT_A", "CANTON", can))

        comparent = nettoyer(ligne.get("COMPARENT"))
        if typecom != "COM" and comparent:
            if comparent in index_communes_principales:
                parents.append(parent("COMMUNE_PARENTE", "COMMUNE", comparent))
            else:
                anomalies.append(
                    {
                        "type": "COMMUNE_PARENTE_ABSENTE",
                        "typecom": typecom,
                        "code": code,
                        "comparent": comparent,
                        "ligne": ligne,
                    }
                )

        identifiant = id_territoire(type_territoire, code)
        objet = creer_territoire(
            type_territoire=type_territoire,
            code=code,
            ligne=ligne,
            observe_le=observe_le,
            precedent=precedents.get(identifiant),
            parents=parents,
        )
        objet["identifiants"]["typecom"] = typecom
        ajouter(objet)

    for ligne in donnees["comer"]:
        code = valider_code(ligne.get("COMER", ""), "COMER")
        identifiant = id_territoire("COLLECTIVITE_OUTRE_MER", code)
        objet = creer_territoire(
            type_territoire="COLLECTIVITE_OUTRE_MER",
            code=code,
            ligne=ligne,
            observe_le=observe_le,
            precedent=precedents.get(identifiant),
        )
        ajouter(objet)

    for ligne in donnees["communes_comer"]:
        code = nettoyer(ligne.get("COM_COMER"))
        comer = nettoyer(ligne.get("COMER"))
        nature = nettoyer(ligne.get("NATURE_ZONAGE")) or "INCONNU"
        if not code or not comer:
            raise ErreurCOG("Zonage outre-mer sans COM_COMER ou COMER.")
        parents = [parent("APPARTIENT_A", "COLLECTIVITE_OUTRE_MER", comer)]
        identifiant = id_territoire("ZONAGE_OUTRE_MER", code, nature)
        objet = creer_territoire(
            type_territoire="ZONAGE_OUTRE_MER",
            code=code,
            nature=nature,
            ligne=ligne,
            observe_le=observe_le,
            precedent=precedents.get(identifiant),
            parents=parents,
        )
        objet["identifiants"]["comer"] = comer
        ajouter(objet)

    ids = set(territoires)
    for objet in territoires.values():
        parents_valides = []
        for lien in objet.get("parents", []):
            cible = lien["territoire_id"]
            if cible in ids:
                parents_valides.append(lien)
            else:
                anomalies.append(
                    {
                        "type": "PARENT_TERRITORIAL_NON_RESOLU",
                        "territoire_id": objet["id"],
                        "territoire_nom": objet["nom_officiel"],
                        "parent_id": cible,
                        "type_relation": lien["type_relation"],
                    }
                )
        objet["parents"] = parents_valides

    return (
        sorted(territoires.values(), key=lambda x: x["id"]),
        anomalies,
        {
            "par_type": dict(sorted(compteurs.items())),
            "nombre_territoires": len(territoires),
        },
    )


def construire_relations_territoriales(
    territoires: list[dict[str, Any]],
    observe_le: str,
    precedentes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    relations = []
    for territoire in territoires:
        for lien in territoire.get("parents", []):
            identifiant = relation_id(
                territoire["id"],
                lien["territoire_id"],
                lien["type_relation"],
            )
            preuve = compact_sha256(
                {
                    "territoire": territoire["id"],
                    "parent": lien,
                    "source": territoire.get("source_insee"),
                }
            )
            precedent = precedentes.get(identifiant)
            ancienne = provenance_precedente(precedent)
            inchange = bool(
                precedent
                and ancienne
                and ancienne.get("empreinte") == preuve
            )
            observation = precedent.get("observe_le") if inchange else observe_le
            collecte = ancienne.get("collecte_le") if inchange and ancienne else observe_le
            relations.append(
                {
                    "id": identifiant,
                    "source_territoire": territoire["id"],
                    "type_relation": lien["type_relation"],
                    "cible_territoire": lien["territoire_id"],
                    "provenance": [
                        {
                            "source_id": SOURCE_ID,
                            "identifiant_source": territoire["provenance"][0][
                                "identifiant_source"
                            ],
                            "url": PAGE_SOURCE,
                            "collecte_le": collecte,
                            "empreinte": preuve,
                        }
                    ],
                    "observe_le": observation,
                    "statut_validation": "VALIDE",
                }
            )
    return sorted(relations, key=lambda x: x["id"])


def construire_evenements(
    mouvements: list[dict[str, str]],
    observe_le: str,
) -> list[dict[str, Any]]:
    resultat = []
    for index, ligne in enumerate(mouvements, start=1):
        resultat.append(
            {
                "id": evenement_id(index, ligne),
                "source_id": SOURCE_ID,
                "type_evenement_source": nettoyer(ligne.get("MOD")),
                "date_effet": nettoyer(ligne.get("DATE_EFF")),
                "avant": {
                    "typecom": nettoyer(ligne.get("TYPECOM_AV")),
                    "code": nettoyer(ligne.get("COM_AV")),
                    "nom": nettoyer(ligne.get("LIBELLE_AV"))
                    or nettoyer(ligne.get("NCCENR_AV")),
                },
                "apres": {
                    "typecom": nettoyer(ligne.get("TYPECOM_AP")),
                    "code": nettoyer(ligne.get("COM_AP")),
                    "nom": nettoyer(ligne.get("LIBELLE_AP"))
                    or nettoyer(ligne.get("NCCENR_AP")),
                },
                "provenance": {
                    "url": PAGE_SOURCE,
                    "empreinte": compact_sha256(ligne),
                },
                "observe_le": observe_le,
                "source_insee": ligne,
            }
        )
    return resultat


def construire_historique_communes(
    lignes: list[dict[str, str]],
) -> list[dict[str, Any]]:
    resultat = []
    for ligne in lignes:
        code = nettoyer(ligne.get("COM"))
        typecom = nettoyer(ligne.get("TYPECOM"))
        if not code or not typecom:
            raise ErreurCOG("Historique commune sans COM ou TYPECOM.")
        resultat.append(
            {
                "typecom": typecom,
                "code": code,
                "nom": nettoyer(ligne.get("LIBELLE"))
                or nettoyer(ligne.get("NCCENR"))
                or nettoyer(ligne.get("NCC")),
                "valide_depuis": nettoyer(ligne.get("DATE_DEBUT")),
                "valide_jusqua": nettoyer(ligne.get("DATE_FIN")),
                "empreinte": compact_sha256(ligne),
                "source_insee": ligne,
            }
        )
    return sorted(
        resultat,
        key=lambda x: (
            x["code"],
            x["typecom"],
            x.get("valide_depuis") or "",
            x.get("valide_jusqua") or "",
        ),
    )


def ecrire_jsonl_partitionne(
    objets: list[dict[str, Any]],
    dossier: Path,
    prefixe: str,
    partitions: int,
) -> list[dict[str, Any]]:
    dossier.mkdir(parents=True, exist_ok=True)
    tmp = dossier.parent / f".{dossier.name}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    groupes: list[list[dict[str, Any]]] = [[] for _ in range(partitions)]
    for objet in objets:
        numero = int(hashlib.sha256(objet["id"].encode("utf-8")).hexdigest()[:8], 16) % partitions
        groupes[numero].append(objet)

    manifeste = []
    for numero, groupe in enumerate(groupes):
        chemin = tmp / f"{prefixe}_{numero:03d}.jsonl"
        with chemin.open("w", encoding="utf-8", newline="\n") as fichier:
            for objet in sorted(groupe, key=lambda x: x["id"]):
                fichier.write(
                    json.dumps(
                        objet,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
        manifeste.append(
            {
                "fichier": str((dossier / chemin.name).relative_to(RACINE)),
                "nombre": len(groupe),
                "octets": chemin.stat().st_size,
                "sha256": sha256_fichier(chemin),
            }
        )

    if dossier.exists():
        shutil.rmtree(dossier)
    tmp.replace(dossier)
    return manifeste


def ecrire_jsonl_simple(
    objets: list[dict[str, Any]],
    chemin: Path,
) -> dict[str, Any]:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(chemin.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fichier:
        for objet in objets:
            fichier.write(
                json.dumps(
                    objet,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
    tmp.replace(chemin)
    return {
        "fichier": str(chemin.relative_to(RACINE)),
        "nombre": len(objets),
        "octets": chemin.stat().st_size,
        "sha256": sha256_fichier(chemin),
    }


def source_deja_traitee(sha_archive: str) -> bool:
    if not MANIFESTE.exists():
        return False
    try:
        precedent = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(
        precedent.get("sha256_archive") == sha_archive
        and precedent.get("version_transformation") == VERSION_TRANSFORMATION
        and precedent.get("millesime") == MILLESIME
    )


def verifier_colonnes(donnees: dict[str, list[dict[str, str]]]) -> None:
    exiger_colonnes(
        donnees["communes"],
        ["TYPECOM", "COM", "REG", "DEP", "NCCENR", "LIBELLE", "COMPARENT"],
        FICHIERS_REQUIS["communes"],
    )
    exiger_colonnes(
        donnees["departements"],
        ["DEP", "REG", "CHEFLIEU", "LIBELLE"],
        FICHIERS_REQUIS["departements"],
    )
    exiger_colonnes(
        donnees["regions"],
        ["REG", "CHEFLIEU", "LIBELLE"],
        FICHIERS_REQUIS["regions"],
    )
    exiger_colonnes(
        donnees["arrondissements"],
        ["ARR", "DEP", "REG", "CHEFLIEU"],
        FICHIERS_REQUIS["arrondissements"],
    )
    exiger_colonnes(
        donnees["cantons"],
        ["CAN", "DEP", "REG", "BURCENTRAL"],
        FICHIERS_REQUIS["cantons"],
    )
    exiger_colonnes(
        donnees["ctcd"],
        ["CTCD", "REG", "CHEFLIEU"],
        FICHIERS_REQUIS["ctcd"],
    )
    exiger_colonnes(
        donnees["mouvements_communes"],
        ["MOD", "DATE_EFF", "TYPECOM_AV", "COM_AV", "TYPECOM_AP", "COM_AP"],
        FICHIERS_REQUIS["mouvements_communes"],
    )
    exiger_colonnes(
        donnees["historique_communes"],
        ["TYPECOM", "COM", "DATE_DEBUT", "DATE_FIN"],
        FICHIERS_REQUIS["historique_communes"],
    )
    exiger_colonnes(
        donnees["comer"],
        ["COMER", "LIBELLE"],
        FICHIERS_REQUIS["comer"],
    )
    exiger_colonnes(
        donnees["communes_comer"],
        ["COM_COMER", "NATURE_ZONAGE", "COMER", "LIBELLE"],
        FICHIERS_REQUIS["communes_comer"],
    )


def analyser_integrite(
    territoires: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    historique: list[dict[str, Any]],
) -> dict[str, Any]:
    ids = [t["id"] for t in territoires]
    if len(ids) != len(set(ids)):
        raise ErreurCOG("Identifiants territoriaux dupliqués.")

    id_set = set(ids)
    for relation in relations:
        if relation["source_territoire"] not in id_set:
            raise ErreurCOG("Source de relation territoriale absente.")
        if relation["cible_territoire"] not in id_set:
            raise ErreurCOG("Cible de relation territoriale absente.")

    communes_actives = {
        t["code"]
        for t in territoires
        if t["type_territoire"] == "COMMUNE"
    }
    historique_codes = {h["code"] for h in historique}
    manquantes_historique = sorted(communes_actives - historique_codes)

    return {
        "ids_uniques": len(set(ids)),
        "extremites_relations_resolues": True,
        "communes_actives_dans_historique": len(manquantes_historique) == 0,
        "communes_actives_absentes_historique": manquantes_historique,
    }


def executer(
    archive_source: Path | None = None,
    *,
    observe_le: str | None = None,
    forcer: bool = False,
) -> dict[str, Any]:
    observe_le = observe_le or maintenant_iso()
    temp_cree = False
    telechargement: dict[str, Any] = {}

    if archive_source is None:
        fd, nom_tmp = tempfile.mkstemp(prefix="frontiere-cog-", suffix=".zip")
        Path(nom_tmp).unlink(missing_ok=True)
        archive_source = Path(nom_tmp)
        temp_cree = True
        telechargement = telecharger_archive(URL_SOURCE, archive_source)
    else:
        archive_source = archive_source.resolve()
        if not archive_source.is_file():
            raise ErreurCOG(f"Archive COG introuvable: {archive_source}")

    try:
        sha_archive = sha256_fichier(archive_source)
        if not forcer and source_deja_traitee(sha_archive):
            return {
                "etat": "inchange",
                "manifest": json.loads(MANIFESTE.read_text(encoding="utf-8")),
            }

        with zipfile.ZipFile(archive_source) as archive:
            donnees = {}
            fichiers_manifest = {}
            for cle, nom in FICHIERS_REQUIS.items():
                lignes, meta = lire_csv_zip(archive, nom)
                donnees[cle] = lignes
                fichiers_manifest[cle] = meta

        verifier_colonnes(donnees)

        precedents_territoires = charger_index_jsonl(DOSSIER_TERRITOIRES)
        precedentes_relations = charger_index_jsonl(DOSSIER_RELATIONS)

        territoires, anomalies, stats_territoires = construire_territoires(
            donnees,
            observe_le,
            precedents_territoires,
        )
        relations = construire_relations_territoriales(
            territoires,
            observe_le,
            precedentes_relations,
        )
        evenements = construire_evenements(
            donnees["mouvements_communes"],
            observe_le,
        )
        historique = construire_historique_communes(
            donnees["historique_communes"]
        )
        integrite = analyser_integrite(territoires, relations, historique)

        partitions_territoires = ecrire_jsonl_partitionne(
            territoires,
            DOSSIER_TERRITOIRES,
            "cog_territoires",
            N_PARTITIONS_TERRITOIRES,
        )
        partitions_relations = ecrire_jsonl_partitionne(
            relations,
            DOSSIER_RELATIONS,
            "cog_relations",
            N_PARTITIONS_RELATIONS,
        )
        evenement_meta = ecrire_jsonl_simple(
            evenements,
            DOSSIER_EVENEMENTS / f"mouvements_communes_{MILLESIME}.jsonl",
        )
        historique_meta = ecrire_jsonl_simple(
            historique,
            DOSSIER_EVENEMENTS / "historique_communes_depuis_1943.jsonl",
        )

        DOSSIER_ARCHIVES.mkdir(parents=True, exist_ok=True)
        archive_finale = DOSSIER_ARCHIVES / NOM_SOURCE
        shutil.copyfile(archive_source, archive_finale)

        statistiques = {
            "version": "1",
            "source_id": SOURCE_ID,
            "millesime": MILLESIME,
            "observe_le": observe_le,
            "nombre_territoires": len(territoires),
            "nombre_relations_territoriales": len(relations),
            "nombre_evenements_communes": len(evenements),
            "nombre_lignes_historique_communes": len(historique),
            "territoires": stats_territoires,
            "integrite": integrite,
            "anomalies": len(anomalies),
            "fichiers_source": {
                cle: meta["nombre_lignes"]
                for cle, meta in sorted(fichiers_manifest.items())
            },
        }

        manifeste = {
            "version": "1",
            "source_id": SOURCE_ID,
            "producteur": "Insee",
            "millesime": MILLESIME,
            "date_reference": f"{MILLESIME}-01-01",
            "page_source": PAGE_SOURCE,
            "url_source": URL_SOURCE,
            "licence": "Licence Ouverte 2.0",
            "observe_le": observe_le,
            "version_transformation": VERSION_TRANSFORMATION,
            "nom_archive": NOM_SOURCE,
            "sha256_archive": sha_archive,
            "octets_archive": archive_finale.stat().st_size,
            "telechargement": telechargement,
            "fichiers_source": fichiers_manifest,
            "partitions_territoires": partitions_territoires,
            "partitions_relations": partitions_relations,
            "evenements_communes": evenement_meta,
            "historique_communes": historique_meta,
        }

        ANOMALIES.write_text(
            json.dumps(
                {
                    "version": "1",
                    "source_id": SOURCE_ID,
                    "millesime": MILLESIME,
                    "observe_le": observe_le,
                    "nombre_anomalies": len(anomalies),
                    "anomalies": anomalies,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        STATISTIQUES.write_text(
            json.dumps(
                statistiques,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        MANIFESTE.write_text(
            json.dumps(
                manifeste,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return {
            "etat": "actualise",
            "territoires": len(territoires),
            "relations": len(relations),
            "evenements": len(evenements),
            "historique": len(historique),
            "anomalies": len(anomalies),
            "sha256_archive": sha_archive,
            "par_type": stats_territoires["par_type"],
        }
    finally:
        if temp_cree and archive_source is not None:
            archive_source.unlink(missing_ok=True)


def parser_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingère le Code officiel géographique 2026 de l'Insee."
    )
    parser.add_argument(
        "--archive",
        type=Path,
        help="Archive CSV COG locale. Sans cet argument, la source officielle est téléchargée.",
    )
    parser.add_argument(
        "--forcer",
        action="store_true",
        help="Recalcule les sorties même si la source et la transformation sont inchangées.",
    )
    return parser.parse_args()


def main() -> int:
    args = parser_arguments()
    try:
        resultat = executer(args.archive, forcer=args.forcer)
    except (OSError, csv.Error, json.JSONDecodeError, zipfile.BadZipFile, ErreurCOG) as exc:
        print(f"ERREUR: {exc}")
        return 2
    print(json.dumps(resultat, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
