from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

RACINE = Path(__file__).resolve().parents[1]
SOURCE_ID = "insee_cog"
VERSION_TRANSFORMATION = "1.1"
MILLESIME = "2026"
REFERENCE_LE = "2026-01-01"
PAGE_SOURCE = "https://www.insee.fr/fr/information/8740222"
URL_SOURCE = "https://www.insee.fr/fr/statistiques/fichier/8740222/cog_ensemble_2026_csv.zip"
NOM_SOURCE = "cog_ensemble_2026_csv.zip"

DOSSIER_TERRITOIRES = RACINE / "institutionnel" / "territoires" / "cog"
DOSSIER_RELATIONS = RACINE / "institutionnel" / "relations" / "territoriales" / "cog"
MANIFESTE = RACINE / "institutionnel" / "instantanes" / "cog_manifest.json"
MANIFESTE_ANNUAIRE = RACINE / "institutionnel" / "instantanes" / "annuaire_local_manifest.json"
STATISTIQUES = RACINE / "institutionnel" / "statistiques_cog.json"
ANOMALIES = RACINE / "institutionnel" / "anomalies_cog.json"
RESOLUTION_ANNUAIRE = RACINE / "institutionnel" / "resolution_annuaire_cog.json"
DOSSIER_ANNUAIRE = RACINE / "institutionnel" / "entites" / "locales"

N_PARTITIONS_TERRITOIRES = 64
N_PARTITIONS_RELATIONS = 128
TAILLE_BLOC = 1024 * 1024
LIMITE_ARCHIVE = 50 * 1024 * 1024
LIMITE_MEMBRE = 20 * 1024 * 1024

TYPES_COMMUNE = {"COM", "ARM", "COMA", "COMD"}


class ErreurCOG(RuntimeError):
    """Erreur explicite d'ingestion du Code officiel géographique."""


def maintenant_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def texte(valeur: Any) -> str | None:
    if valeur is None:
        return None
    resultat = str(valeur).strip()
    return resultat or None


def compact_sha256(objet: Any) -> str:
    brut = json.dumps(objet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def sha256_fichier(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as fichier:
        for bloc in iter(lambda: fichier.read(4 * TAILLE_BLOC), b""):
            h.update(bloc)
    return h.hexdigest()


def nom_archive_sur(nom: str) -> bool:
    chemin = PurePosixPath(nom)
    return bool(chemin.parts) and not chemin.is_absolute() and ".." not in chemin.parts and all(p not in {"", "."} for p in chemin.parts)


def membre_zip_est_lien(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return bool(mode and stat.S_ISLNK(mode))


def verifier_membre_zip(info: zipfile.ZipInfo) -> None:
    if not nom_archive_sur(info.filename):
        raise ErreurCOG(f"Chemin ZIP dangereux ou invalide: {info.filename!r}")
    if membre_zip_est_lien(info):
        raise ErreurCOG(f"Lien symbolique interdit dans le ZIP: {info.filename!r}")
    if info.file_size > LIMITE_MEMBRE:
        raise ErreurCOG(f"Membre ZIP anormalement volumineux: {info.filename}")


def telecharger(url: str, destination: Path, limite_octets: int = LIMITE_ARCHIVE) -> dict[str, Any]:
    requete = urllib.request.Request(url, headers={"User-Agent": "FRONTIERE-referentiel-territorial/1.0", "Accept": "application/zip,application/octet-stream,*/*"})
    h = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(requete, timeout=120) as reponse:
        longueur = reponse.headers.get("Content-Length")
        if longueur and longueur.isdigit() and int(longueur) > limite_octets:
            raise ErreurCOG(f"Archive annoncée à {longueur} octets, au-delà de la limite de sécurité.")
        with destination.open("wb") as sortie:
            while True:
                bloc = reponse.read(TAILLE_BLOC)
                if not bloc:
                    break
                total += len(bloc)
                if total > limite_octets:
                    raise ErreurCOG("Archive téléchargée au-delà de la limite de sécurité.")
                h.update(bloc)
                sortie.write(bloc)
        return {
            "url_effective": reponse.geturl(),
            "last_modified_http": reponse.headers.get("Last-Modified"),
            "etag_http": reponse.headers.get("ETag"),
            "content_length_http": longueur,
            "octets": total,
            "sha256": h.hexdigest(),
        }


def normaliser_entete(nom: str) -> str:
    return nom.strip().lstrip("\ufeff").upper()


def delimiter_csv(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    with archive.open(info) as brut:
        premiere = brut.readline(64 * 1024).decode("utf-8-sig")
    if not premiere.strip():
        raise ErreurCOG(f"CSV vide: {info.filename}")
    candidats = [",", ";", "\t", "|"]
    scores = {c: premiere.count(c) for c in candidats}
    delimiteur, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        raise ErreurCOG(f"Délimiteur CSV non reconnu: {info.filename}")
    return delimiteur


def entete_csv(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> set[str]:
    delimiteur = delimiter_csv(archive, info)
    with archive.open(info) as brut:
        texte_flux = io.TextIOWrapper(brut, encoding="utf-8-sig", newline="")
        lecteur = csv.reader(texte_flux, delimiter=delimiteur)
        try:
            ligne = next(lecteur)
        except StopIteration as exc:
            raise ErreurCOG(f"CSV vide: {info.filename}") from exc
    return {normaliser_entete(c) for c in ligne}


def classifier_csv(entete: set[str]) -> str | None:
    if {"TYPECOM", "COM", "REG", "DEP", "CTCD", "ARR", "CAN", "COMPARENT"} <= entete:
        return "communes"
    if {"CAN", "DEP", "REG", "BURCENTRAL", "COMPCT", "TYPECT"} <= entete:
        return "cantons"
    if {"ARR", "DEP", "REG", "CHEFLIEU"} <= entete and "COM" not in entete:
        return "arrondissements"
    if {"CTCD", "REG", "CHEFLIEU"} <= entete:
        return "ctcd"
    if {"DEP", "REG", "CHEFLIEU"} <= entete and not ({"ARR", "CAN", "CTCD"} & entete):
        return "departements"
    if {"REG", "CHEFLIEU", "TNCC", "NCC", "NCCENR", "LIBELLE"} <= entete and not ({"DEP", "ARR", "CAN", "CTCD"} & entete):
        return "regions"
    if {"COM_COMER", "NATURE_ZONAGE", "COMER"} <= entete:
        return "communes_comer"
    if {"COMER", "TNCC", "NCC", "NCCENR", "LIBELLE"} <= entete and not ({"COM_COMER", "DATE_DEBUT", "DATE_FIN"} & entete):
        return "comer"
    if {"TYPECOM", "COM", "DATE_DEBUT", "DATE_FIN", "NCCENR"} <= entete:
        return "communes_historiques"
    if {"MOD", "DATE_EFF", "TYPECOM_AV", "COM_AV", "TYPECOM_AP", "COM_AP"} <= entete:
        return "evenements_communes"
    return None


FAMILLES_REQUISES = {
    "communes",
    "cantons",
    "arrondissements",
    "departements",
    "regions",
    "ctcd",
    "communes_comer",
    "comer",
    "communes_historiques",
    "evenements_communes",
}


def decouvrir_fichiers(archive: zipfile.ZipFile) -> tuple[dict[str, zipfile.ZipInfo], list[dict[str, Any]]]:
    classes: dict[str, zipfile.ZipInfo] = {}
    inventaire: list[dict[str, Any]] = []
    for info in archive.infolist():
        verifier_membre_zip(info)
        if info.is_dir():
            continue
        h = hashlib.sha256()
        with archive.open(info) as flux:
            for bloc in iter(lambda: flux.read(TAILLE_BLOC), b""):
                h.update(bloc)
        entree = {"nom": info.filename, "octets": info.file_size, "sha256": h.hexdigest()}
        if info.filename.lower().endswith(".csv"):
            entete = entete_csv(archive, info)
            classe = classifier_csv(entete)
            entree["classe_detectee"] = classe
            entree["colonnes"] = sorted(entete)
            if classe:
                if classe in classes:
                    raise ErreurCOG(f"Plusieurs CSV correspondent à la classe {classe}: {classes[classe].filename}, {info.filename}")
                classes[classe] = info
        inventaire.append(entree)
    manquantes = sorted(FAMILLES_REQUISES - set(classes))
    if manquantes:
        raise ErreurCOG(f"Archive COG incomplète ou format modifié; classes absentes: {', '.join(manquantes)}")
    return classes, inventaire


def lire_csv(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> list[dict[str, str]]:
    delimiteur = delimiter_csv(archive, info)
    with archive.open(info) as brut:
        texte_flux = io.TextIOWrapper(brut, encoding="utf-8-sig", newline="")
        lecteur = csv.DictReader(texte_flux, delimiter=delimiteur)
        resultat = []
        for brut_ligne in lecteur:
            ligne = {normaliser_entete(k): (v.strip() if isinstance(v, str) else v) for k, v in brut_ligne.items() if k is not None}
            resultat.append(ligne)
        return resultat


def id_territoire(type_territoire: str, code: str, *, parent: str | None = None) -> str:
    morceaux = ["FRONTIERE", "TERR", "COG", re.sub(r"[^A-Z0-9]+", "-", type_territoire.upper()).strip("-")]
    if parent:
        morceaux.append(re.sub(r"[^A-Z0-9]+", "-", parent.upper()).strip("-"))
    morceaux.append(re.sub(r"[^A-Z0-9]+", "-", code.upper()).strip("-"))
    return "-".join(morceaux)


def nom_ligne(ligne: dict[str, str]) -> str:
    return texte(ligne.get("LIBELLE")) or texte(ligne.get("NCCENR")) or texte(ligne.get("NCC")) or "Nom non publié"


def provenance_precedente(precedent: dict[str, Any] | None) -> dict[str, Any] | None:
    if not precedent:
        return None
    p = precedent.get("provenance")
    if isinstance(p, list) and p and isinstance(p[0], dict):
        return p[0]
    return None


def charger_index_jsonl(dossier: Path, cle: str = "id") -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    if not dossier.exists():
        return index
    for chemin in sorted(dossier.glob("*.jsonl")):
        with chemin.open("r", encoding="utf-8") as fichier:
            for numero, ligne in enumerate(fichier, start=1):
                if not ligne.strip():
                    continue
                objet = json.loads(ligne)
                identifiant = texte(objet.get(cle))
                if not identifiant:
                    raise ErreurCOG(f"Objet sans {cle} dans {chemin}:{numero}")
                if identifiant in index:
                    raise ErreurCOG(f"Identifiant canonique dupliqué: {identifiant}")
                index[identifiant] = objet
    return index


def creer_territoire(type_territoire: str, code: str, ligne: dict[str, str], observe_le: str, precedent: dict[str, Any] | None = None, *, parent_code: str | None = None) -> dict[str, Any]:
    if not code:
        raise ErreurCOG(f"Code absent pour un territoire {type_territoire}")
    identifiant = id_territoire(type_territoire, code, parent=parent_code)
    empreinte = compact_sha256(ligne)
    ancienne = provenance_precedente(precedent)
    inchange = bool(precedent and ancienne and ancienne.get("empreinte") == empreinte)
    collecte = ancienne.get("collecte_le") if inchange and ancienne else observe_le
    observation = precedent.get("observe_le") if inchange else observe_le
    identifiants = {"insee_cog": code}
    if type_territoire in TYPES_COMMUNE:
        identifiants["typecom"] = type_territoire
    if type_territoire == "COMER-COM":
        identifiants["comer"] = parent_code
        identifiants["nature_zonage"] = ligne.get("NATURE_ZONAGE")
    return {
        "id": identifiant,
        "nom_officiel": nom_ligne(ligne),
        "type_territoire": type_territoire,
        "code": code,
        "identifiants": {k: v for k, v in identifiants.items() if v},
        "reference_le": REFERENCE_LE,
        "millesime": MILLESIME,
        "provenance": [{
            "source_id": SOURCE_ID,
            "identifiant_source": f"{type_territoire}:{parent_code + ':' if parent_code else ''}{code}",
            "url": PAGE_SOURCE,
            "collecte_le": collecte,
            "empreinte": empreinte,
        }],
        "observe_le": observation,
        "source_insee": ligne,
    }


def construire_territoires(tables: dict[str, list[dict[str, str]]], observe_le: str, precedents: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    resultat: list[dict[str, Any]] = []
    # Le fichier CTCD décrit des collectivités territoriales exerçant les
    # compétences départementales. Ce sont des autorités/institutions publiques,
    # pas des unités géographiques homogènes avec REG/DEP/COM. Nous conservons
    # le fichier dans le manifeste source et les codes CTCD dans `source_insee`,
    # sans créer de nœuds territoriaux CTCD. Leur résolution institutionnelle
    # fera l’objet d’un croisement dédié ultérieur.
    specifications: list[tuple[str, str, str]] = [
        ("regions", "REG", "REG"),
        ("departements", "DEP", "DEP"),
        ("arrondissements", "ARR", "ARR"),
        ("cantons", "CAN", "CAN"),
    ]
    for table, colonne, type_territoire in specifications:
        for ligne in tables[table]:
            code = texte(ligne.get(colonne))
            if not code:
                raise ErreurCOG(f"Code {colonne} absent dans {table}")
            identifiant = id_territoire(type_territoire, code)
            resultat.append(creer_territoire(type_territoire, code, ligne, observe_le, precedents.get(identifiant)))
    for ligne in tables["communes"]:
        typecom = texte(ligne.get("TYPECOM"))
        code = texte(ligne.get("COM"))
        if typecom not in TYPES_COMMUNE or not code:
            raise ErreurCOG(f"Commune avec TYPECOM/COM invalide: {typecom!r}/{code!r}")
        identifiant = id_territoire(typecom, code)
        resultat.append(creer_territoire(typecom, code, ligne, observe_le, precedents.get(identifiant)))
    for ligne in tables["comer"]:
        code = texte(ligne.get("COMER"))
        if not code:
            raise ErreurCOG("Collectivité d'outre-mer sans code COMER")
        identifiant = id_territoire("COMER", code)
        resultat.append(creer_territoire("COMER", code, ligne, observe_le, precedents.get(identifiant)))
    for ligne in tables["communes_comer"]:
        code = texte(ligne.get("COM_COMER"))
        parent = texte(ligne.get("COMER"))
        if not code or not parent:
            raise ErreurCOG("Zonage d'outre-mer sans COM_COMER/COMER")
        identifiant = id_territoire("COMER-COM", code, parent=parent)
        resultat.append(creer_territoire("COMER-COM", code, ligne, observe_le, precedents.get(identifiant), parent_code=parent))
    ids = [x["id"] for x in resultat]
    if len(ids) != len(set(ids)):
        doublons = [i for i, n in Counter(ids).items() if n > 1]
        raise ErreurCOG(f"Identifiants territoriaux dupliqués: {doublons[:10]}")
    resultat.sort(key=lambda x: x["id"])
    return resultat


def index_territoires(territoires: Iterable[dict[str, Any]]) -> dict[tuple[str, str], str]:
    resultat: dict[tuple[str, str], str] = {}
    for t in territoires:
        typ = t["type_territoire"]
        code = t["code"]
        if typ == "COMER-COM":
            parent = (t.get("identifiants") or {}).get("comer")
            if not parent:
                raise ErreurCOG(f"Territoire COMER-COM sans parent: {t['id']}")
            cle = (typ, f"{parent}:{code}")
        else:
            cle = (typ, code)
        if cle in resultat:
            raise ErreurCOG(f"Clé territoriale dupliquée: {cle}")
        resultat[cle] = t["id"]
    return resultat


def relation_id(source: str, type_relation: str, cible: str, champ: str) -> str:
    cle = "|".join((source, type_relation, cible, champ))
    return "FRONTIERE-REL-COG-" + hashlib.sha256(cle.encode("utf-8")).hexdigest()[:24].upper()


def creer_relation(source: str, type_relation: str, cible: str, champ: str, ligne: dict[str, str], observe_le: str, precedent: dict[str, Any] | None = None) -> dict[str, Any]:
    identifiant = relation_id(source, type_relation, cible, champ)
    empreinte = compact_sha256({"champ": champ, "ligne": ligne, "source": source, "cible": cible, "type": type_relation})
    ancienne = provenance_precedente(precedent)
    inchange = bool(precedent and ancienne and ancienne.get("empreinte") == empreinte)
    collecte = ancienne.get("collecte_le") if inchange and ancienne else observe_le
    observation = precedent.get("observe_le") if inchange else observe_le
    return {
        "id": identifiant,
        "source_territoire": source,
        "type_relation": type_relation,
        "cible_territoire": cible,
        "qualificatifs": {"champ_source": champ},
        "reference_le": REFERENCE_LE,
        "provenance": [{"source_id": SOURCE_ID, "url": PAGE_SOURCE, "collecte_le": collecte, "empreinte": empreinte}],
        "observe_le": observation,
        "statut_validation": "VALIDE",
    }


def construire_relations(tables: dict[str, list[dict[str, str]]], territoires: list[dict[str, Any]], observe_le: str, precedentes: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    idx = index_territoires(territoires)
    relations: dict[str, dict[str, Any]] = {}
    anomalies: list[dict[str, Any]] = []

    def ajouter(source: str | None, cible_type: str, cible_code: str | None, type_relation: str, champ: str, ligne: dict[str, str]) -> None:
        if not source or not cible_code:
            return
        cible = idx.get((cible_type, cible_code))
        if not cible:
            anomalies.append({"type": "CIBLE_TERRITORIALE_NON_RESOLUE", "source_territoire": source, "type_relation": type_relation, "champ_source": champ, "type_cible": cible_type, "code_cible": cible_code, "source_insee": ligne})
            return
        identifiant = relation_id(source, type_relation, cible, champ)
        relations[identifiant] = creer_relation(source, type_relation, cible, champ, ligne, observe_le, precedentes.get(identifiant))

    for ligne in tables["departements"]:
        source = idx.get(("DEP", ligne.get("DEP", "")))
        ajouter(source, "REG", texte(ligne.get("REG")), "APPARTIENT_A", "REG", ligne)
        ajouter(source, "COM", texte(ligne.get("CHEFLIEU")), "A_POUR_CHEF_LIEU", "CHEFLIEU", ligne)
    for ligne in tables["arrondissements"]:
        source = idx.get(("ARR", ligne.get("ARR", "")))
        ajouter(source, "DEP", texte(ligne.get("DEP")), "APPARTIENT_A", "DEP", ligne)
        ajouter(source, "REG", texte(ligne.get("REG")), "APPARTIENT_A", "REG", ligne)
        ajouter(source, "COM", texte(ligne.get("CHEFLIEU")), "A_POUR_CHEF_LIEU", "CHEFLIEU", ligne)
    for ligne in tables["cantons"]:
        source = idx.get(("CAN", ligne.get("CAN", "")))
        ajouter(source, "DEP", texte(ligne.get("DEP")), "APPARTIENT_A", "DEP", ligne)
        ajouter(source, "REG", texte(ligne.get("REG")), "APPARTIENT_A", "REG", ligne)
        ajouter(source, "COM", texte(ligne.get("BURCENTRAL")), "A_POUR_CHEF_LIEU", "BURCENTRAL", ligne)
    for ligne in tables["regions"]:
        source = idx.get(("REG", ligne.get("REG", "")))
        ajouter(source, "COM", texte(ligne.get("CHEFLIEU")), "A_POUR_CHEF_LIEU", "CHEFLIEU", ligne)
    for ligne in tables["communes"]:
        typecom = texte(ligne.get("TYPECOM")) or ""
        code = texte(ligne.get("COM")) or ""
        source = idx.get((typecom, code))
        if typecom != "COM" and texte(ligne.get("COMPARENT")):
            ajouter(source, "COM", texte(ligne.get("COMPARENT")), "PARTIE_DE", "COMPARENT", ligne)
        ajouter(source, "DEP", texte(ligne.get("DEP")), "APPARTIENT_A", "DEP", ligne)
        ajouter(source, "REG", texte(ligne.get("REG")), "APPARTIENT_A", "REG", ligne)
        ajouter(source, "ARR", texte(ligne.get("ARR")), "APPARTIENT_A", "ARR", ligne)
        ajouter(source, "CAN", texte(ligne.get("CAN")), "APPARTIENT_A", "CAN", ligne)
    for ligne in tables["communes_comer"]:
        code = texte(ligne.get("COM_COMER")) or ""
        parent = texte(ligne.get("COMER")) or ""
        source = idx.get(("COMER-COM", f"{parent}:{code}"))
        ajouter(source, "COMER", parent, "APPARTIENT_A", "COMER", ligne)

    resultat = sorted(relations.values(), key=lambda x: x["id"])
    return resultat, anomalies


def ecrire_jsonl_partitionne(objets: list[dict[str, Any]], dossier: Path, prefixe: str, nombre: int, cle: str) -> list[dict[str, Any]]:
    if dossier.exists():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    partitions: list[list[dict[str, Any]]] = [[] for _ in range(nombre)]
    for objet in objets:
        identifiant = texte(objet.get(cle))
        if not identifiant:
            raise ErreurCOG(f"Clé absente pour partitionnement: {cle}")
        idx = int(hashlib.sha256(identifiant.encode("utf-8")).hexdigest()[:8], 16) % nombre
        partitions[idx].append(objet)
    manifeste = []
    for i, items in enumerate(partitions):
        items.sort(key=lambda x: str(x[cle]))
        chemin = dossier / f"{prefixe}_{i:03d}.jsonl"
        contenu = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for x in items)
        chemin.write_text(contenu, encoding="utf-8")
        brut = contenu.encode("utf-8")
        manifeste.append({"fichier": str(chemin.relative_to(RACINE)), "nombre": len(items), "octets": len(brut), "sha256": hashlib.sha256(brut).hexdigest()})
    return manifeste


def charger_codes_annuaire() -> Iterable[tuple[str, list[str]]]:
    if not DOSSIER_ANNUAIRE.exists():
        return []
    def generateur():
        for chemin in sorted(DOSSIER_ANNUAIRE.glob("*.jsonl")):
            with chemin.open("r", encoding="utf-8") as fichier:
                for ligne in fichier:
                    if not ligne.strip():
                        continue
                    entite = json.loads(ligne)
                    codes = [str(c).strip() for c in entite.get("territoires") or [] if texte(c)]
                    if codes:
                        yield entite.get("id", ""), codes
    return generateur()


def _index_historique_communes(
    historique: Iterable[dict[str, str]],
    evenements: Iterable[dict[str, str]],
) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    par_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    evenements_sortants: dict[str, list[dict[str, str]]] = defaultdict(list)

    for ligne in historique:
        code = texte(ligne.get("COM"))
        if code:
            par_code[code].append(ligne)

    for lignes in par_code.values():
        lignes.sort(key=lambda x: (texte(x.get("DATE_DEBUT")) or "", texte(x.get("DATE_FIN")) or ""))

    for ligne in evenements:
        code = texte(ligne.get("COM_AV"))
        if code:
            evenements_sortants[code].append(ligne)

    for lignes in evenements_sortants.values():
        lignes.sort(key=lambda x: texte(x.get("DATE_EFF")) or "")

    return dict(par_code), dict(evenements_sortants)


def _resume_historique_code(
    code: str,
    historique: dict[str, list[dict[str, str]]],
    evenements: dict[str, list[dict[str, str]]],
) -> dict[str, Any] | None:
    periodes = historique.get(code, [])
    transitions = evenements.get(code, [])
    if not periodes and not transitions:
        return None

    dernieres_periodes: list[dict[str, Any]] = []
    if periodes:
        date_debut_max = max(texte(x.get("DATE_DEBUT")) or "" for x in periodes)
        dernieres_periodes = [
            {
                "typecom": texte(x.get("TYPECOM")),
                "nom": texte(x.get("NCCENR")) or texte(x.get("LIBELLE")) or texte(x.get("NCC")),
                "date_debut": texte(x.get("DATE_DEBUT")),
                "date_fin": texte(x.get("DATE_FIN")),
            }
            for x in periodes
            if (texte(x.get("DATE_DEBUT")) or "") == date_debut_max
        ]

    derniers_evenements: list[dict[str, Any]] = []
    if transitions:
        date_eff_max = max(texte(x.get("DATE_EFF")) or "" for x in transitions)
        derniers_evenements = [
            {
                "mod": texte(x.get("MOD")),
                "date_eff": texte(x.get("DATE_EFF")),
                "typecom_av": texte(x.get("TYPECOM_AV")),
                "code_av": texte(x.get("COM_AV")),
                "nom_av": texte(x.get("NCCENR_AV")) or texte(x.get("LIBELLE_AV")) or texte(x.get("NCC_AV")),
                "typecom_ap": texte(x.get("TYPECOM_AP")),
                "code_ap": texte(x.get("COM_AP")),
                "nom_ap": texte(x.get("NCCENR_AP")) or texte(x.get("LIBELLE_AP")) or texte(x.get("NCC_AP")),
            }
            for x in transitions
            if (texte(x.get("DATE_EFF")) or "") == date_eff_max
        ]

    return {
        "code": code,
        "derniere_periode_connue": dernieres_periodes,
        "dernier_evenement_sortant": derniers_evenements,
    }


def resoudre_annuaire_cog(
    territoires: list[dict[str, Any]],
    observe_le: str,
    *,
    historique_communes: Iterable[dict[str, str]] = (),
    evenements_communes: Iterable[dict[str, str]] = (),
) -> dict[str, Any]:
    par_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in territoires:
        if t["type_territoire"] in TYPES_COMMUNE or t["type_territoire"] == "COMER-COM":
            par_code[t["code"]].append(t)

    historique, evenements = _index_historique_communes(
        historique_communes, evenements_communes
    )

    total_entites = 0
    total_codes = 0
    resolus = 0
    ambigus = 0
    absents = 0
    absents_historiques = 0
    absents_inconnus = 0
    exemples_ambigus: list[dict[str, Any]] = []
    exemples_absents: list[dict[str, Any]] = []
    exemples_historiques: list[dict[str, Any]] = []
    exemples_inconnus: list[dict[str, Any]] = []

    for entite_id, codes in charger_codes_annuaire():
        total_entites += 1
        for code in codes:
            total_codes += 1
            candidats = par_code.get(code, [])
            communes = [t for t in candidats if t["type_territoire"] == "COM"]
            if len(communes) == 1:
                resolus += 1
                continue
            comer = [t for t in candidats if t["type_territoire"] == "COMER-COM"]
            if not communes and len(comer) == 1:
                resolus += 1
                continue
            if len(candidats) == 1:
                resolus += 1
            elif len(candidats) > 1:
                ambigus += 1
                if len(exemples_ambigus) < 100:
                    exemples_ambigus.append(
                        {
                            "entite_id": entite_id,
                            "code": code,
                            "candidats": [t["id"] for t in candidats],
                        }
                    )
            else:
                absents += 1
                resume_historique = _resume_historique_code(code, historique, evenements)
                entree_absente: dict[str, Any] = {"entite_id": entite_id, "code": code}
                if resume_historique is not None:
                    absents_historiques += 1
                    entree_absente["classification"] = "CODE_HISTORIQUE_ABSENT_DU_COG_COURANT"
                    entree_absente["historique_cog"] = resume_historique
                    if len(exemples_historiques) < 100:
                        exemples_historiques.append(entree_absente)
                else:
                    absents_inconnus += 1
                    entree_absente["classification"] = "CODE_ABSENT_SANS_TRACE_HISTORIQUE_COG"
                    if len(exemples_inconnus) < 100:
                        exemples_inconnus.append(entree_absente)
                if len(exemples_absents) < 100:
                    exemples_absents.append(entree_absente)

    explications = resolus + absents_historiques
    return {
        "version": "2",
        "observe_le": observe_le,
        "entites_annuaire_avec_territoire": total_entites,
        "references_codes_insee": total_codes,
        "resolues": resolus,
        "ambigues": ambigus,
        "absentes": absents,
        "absentes_courantes_expliquees_historiquement": absents_historiques,
        "absentes_sans_trace_historique": absents_inconnus,
        "taux_resolution": round(resolus / total_codes, 6) if total_codes else None,
        "taux_references_expliquees": round(explications / total_codes, 6) if total_codes else None,
        "exemples_ambigus": exemples_ambigus,
        "exemples_absents": exemples_absents,
        "exemples_absents_historiques": exemples_historiques,
        "exemples_absents_inconnus": exemples_inconnus,
        "doctrine": (
            "Priorité à TYPECOM=COM; à défaut un zonage COMER-COM unique; "
            "aucune résolution par nom. Un code absent du COG courant est "
            "classé séparément s'il est attesté dans les tables historiques "
            "officielles; cette classification ne le remappe pas vers un territoire courant."
        ),
    }


def empreinte_semantique(territoires: list[dict[str, Any]], relations: list[dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for objet in sorted(territoires, key=lambda x: x["id"]):
        h.update(objet["id"].encode())
        h.update((objet["provenance"][0]["empreinte"] or "").encode())
        h.update(b"\n")
    for relation in sorted(relations, key=lambda x: x["id"]):
        h.update(relation["id"].encode())
        h.update((relation["provenance"][0]["empreinte"] or "").encode())
        h.update(b"\n")
    return h.hexdigest()



def empreinte_dependance_annuaire() -> str:
    """Empreinte de l'état Annuaire dont dépend le rapport de résolution COG."""
    try:
        manifeste = json.loads(MANIFESTE_ANNUAIRE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ErreurCOG("Le manifeste Annuaire local est indispensable au croisement COG.") from exc
    dependance = {
        "sha256_semantique_export": manifeste.get("sha256_semantique_export"),
        "version_transformation": manifeste.get("version_transformation"),
        "nombre_services_locaux": manifeste.get("nombre_services_locaux"),
    }
    if not dependance["sha256_semantique_export"] or not dependance["version_transformation"]:
        raise ErreurCOG("Le manifeste Annuaire local ne contient pas son identité sémantique.")
    return compact_sha256(dependance)

def source_deja_traitee(sha_zip: str, empreinte_annuaire: str) -> bool:
    if not MANIFESTE.exists():
        return False
    try:
        m = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(
        m.get("sha256_zip") == sha_zip
        and m.get("version_transformation") == VERSION_TRANSFORMATION
        and m.get("empreinte_dependance_annuaire") == empreinte_annuaire
    )


def executer(archive_path: Path, telechargement: dict[str, Any] | None = None, observe_le: str | None = None) -> dict[str, Any]:
    observe_le = observe_le or maintenant_iso()
    sha_zip = (telechargement or {}).get("sha256") or sha256_fichier(archive_path)
    empreinte_annuaire = empreinte_dependance_annuaire()
    if source_deja_traitee(sha_zip, empreinte_annuaire):
        return {"etat": "inchange", "manifest": json.loads(MANIFESTE.read_text(encoding="utf-8")), "stats": json.loads(STATISTIQUES.read_text(encoding="utf-8"))}
    precedents = charger_index_jsonl(DOSSIER_TERRITOIRES)
    relations_precedentes = charger_index_jsonl(DOSSIER_RELATIONS)
    with zipfile.ZipFile(archive_path) as archive:
        classes, inventaire = decouvrir_fichiers(archive)
        tables = {classe: lire_csv(archive, info) for classe, info in classes.items()}
    territoires = construire_territoires(tables, observe_le, precedents)
    relations, anomalies = construire_relations(tables, territoires, observe_le, relations_precedentes)
    resolution = resoudre_annuaire_cog(
        territoires,
        observe_le,
        historique_communes=tables["communes_historiques"],
        evenements_communes=tables["evenements_communes"],
    )
    partitions_t = ecrire_jsonl_partitionne(territoires, DOSSIER_TERRITOIRES, "cog_territoire", N_PARTITIONS_TERRITOIRES, "id")
    partitions_r = ecrire_jsonl_partitionne(relations, DOSSIER_RELATIONS, "cog_relation", N_PARTITIONS_RELATIONS, "id")
    compteur_types = Counter(t["type_territoire"] for t in territoires)
    stats = {
        "version": "1",
        "source_id": SOURCE_ID,
        "millesime": MILLESIME,
        "reference_le": REFERENCE_LE,
        "observe_le": observe_le,
        "nombre_territoires": len(territoires),
        "nombre_relations": len(relations),
        "types_territoires": dict(compteur_types.most_common()),
        "anomalies_relations": len(anomalies),
        "collectivites_competence_departementale_source": len(tables["ctcd"]),
        "doctrine_ctcd": (
            "Les codes CTCD sont conservés comme attributs source et ne sont pas "
            "matérialisés comme territoires : le fichier CTCD décrit des collectivités "
            "territoriales exerçant les compétences départementales."
        ),
        "resolution_annuaire": {
            k: resolution[k]
            for k in (
                "entites_annuaire_avec_territoire",
                "references_codes_insee",
                "resolues",
                "ambigues",
                "absentes",
                "absentes_courantes_expliquees_historiquement",
                "absentes_sans_trace_historique",
                "taux_resolution",
                "taux_references_expliquees",
            )
        },
        "stockage": {
            "octets_territoires": sum((RACINE / p["fichier"]).stat().st_size for p in partitions_t),
            "octets_relations": sum((RACINE / p["fichier"]).stat().st_size for p in partitions_r),
        },
    }
    STATISTIQUES.write_text(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ANOMALIES.write_text(json.dumps({"version": "1", "observe_le": observe_le, "nombre": len(anomalies), "anomalies": anomalies}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    RESOLUTION_ANNUAIRE.write_text(json.dumps(resolution, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifeste = {
        "version": "1",
        "version_transformation": VERSION_TRANSFORMATION,
        "source_id": SOURCE_ID,
        "producteur": "Insee",
        "page_source": PAGE_SOURCE,
        "url_source": URL_SOURCE,
        "nom_fichier": NOM_SOURCE,
        "millesime": MILLESIME,
        "reference_le": REFERENCE_LE,
        "observe_le": observe_le,
        "sha256_zip": sha_zip,
        "empreinte_dependance_annuaire": empreinte_annuaire,
        "telechargement": telechargement or {},
        "fichiers_source": inventaire,
        "sha256_semantique": empreinte_semantique(territoires, relations),
        "nombre_territoires": len(territoires),
        "nombre_relations": len(relations),
        "partitions_territoires": partitions_t,
        "partitions_relations": partitions_r,
    }
    MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
    MANIFESTE.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"etat": "actualise", "manifest": manifeste, "stats": stats}


def parser_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingère le Code officiel géographique 2026 dans le référentiel territorial FRONTIÈRE.")
    parser.add_argument("--archive", type=Path, help="Archive COG CSV locale; sinon téléchargement officiel Insee.")
    return parser.parse_args()


def main() -> int:
    args = parser_arguments()
    temporaire: Path | None = None
    try:
        if args.archive:
            archive = args.archive.resolve()
            if not archive.is_file():
                raise ErreurCOG(f"Archive introuvable: {archive}")
            telechargement: dict[str, Any] = {}
        else:
            fd, nom = tempfile.mkstemp(prefix="frontiere-cog-", suffix=".zip")
            import os
            os.close(fd)
            temporaire = Path(nom)
            telechargement = telecharger(URL_SOURCE, temporaire)
            archive = temporaire
        resultat = executer(archive, telechargement=telechargement)
        resume = {
            "etat": resultat["etat"],
            "territoires": resultat["stats"]["nombre_territoires"],
            "relations": resultat["stats"]["nombre_relations"],
            "types": resultat["stats"]["types_territoires"],
            "anomalies": resultat["stats"]["anomalies_relations"],
            "resolution_annuaire": resultat["stats"]["resolution_annuaire"],
            "sha256_zip": resultat["manifest"]["sha256_zip"],
        }
        print(json.dumps(resume, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, csv.Error, json.JSONDecodeError, zipfile.BadZipFile, ErreurCOG, ValueError) as exc:
        print(f"ERREUR: {exc}", file=__import__("sys").stderr)
        return 2
    finally:
        if temporaire:
            temporaire.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())