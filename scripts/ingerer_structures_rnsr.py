"""Importer les structures de recherche publiques actives du RNSR (MESR).

Les domaines scientifiques sont des classifications publiées, distinctes des
capacités opérationnelles. Aucune fusion par ressemblance de nom avec la DILA.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

RACINE = Path(__file__).resolve().parents[1]
DESTINATION = RACINE / "institutionnel"
SOURCE_ID = "mesr_rnsr_structures_actives"
VERSION_TRANSFORMATION = "1.0"
API = (
    "https://mesr.opendatasoft.com/api/explore/v2.1/catalog/"
    "datasets/fr-esr-structures-recherche-publiques-actives/records"
)
SOURCE_OFFICIELLE = (
    "https://data.enseignementsup-recherche.gouv.fr/explore/dataset/"
    "fr-esr-structures-recherche-publiques-actives/"
)
PARTITIONS = 8
TAILLE_PAGE = 100
PLAFOND_SOURCE = 20000


def empreinte(objet: Any) -> str:
    brut = json.dumps(
        objet, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def maintenant() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def chaine(valeur: Any) -> str | None:
    return valeur.strip() if isinstance(valeur, str) and valeur.strip() else None


def elements(valeur: Any) -> list[str]:
    """Lire uniquement les étiquettes textuelles explicites de la source."""
    if isinstance(valeur, list):
        morceaux = [part for x in valeur for part in elements(x)]
    elif isinstance(valeur, str):
        morceaux = [x.strip() for x in valeur.split(";") if x.strip()]
    else:
        morceaux = []
    return list(dict.fromkeys(morceaux))


def identifier(enregistrement: dict) -> str:
    texte = chaine(enregistrement.get("numero_national_de_structure"))
    if not texte or not re.fullmatch(r"[A-Za-z0-9]{8,14}", texte):
        raise ValueError("Identifiant national RNSR manquant ou invalide.")
    return texte.upper()


def normaliser(
    enregistrement: dict,
    date_collecte: str,
    precedent: dict | None = None,
) -> dict:
    code = identifier(enregistrement)
    nom = chaine(enregistrement.get("libelle"))
    if not nom:
        raise ValueError(f"{code} : dénomination officielle manquante.")
    signature = empreinte(enregistrement)
    provenance_prec = (precedent or {}).get("provenance") or []
    ancienne = provenance_prec[0] if provenance_prec and isinstance(provenance_prec[0], dict) else {}
    identique = ancienne.get("empreinte") == signature
    observe = precedent.get("observe_le") if precedent and identique else date_collecte
    collecte = ancienne.get("collecte_le", date_collecte) if identique else date_collecte

    domaines = elements(enregistrement.get("domaine_scientifique"))
    panels = elements(enregistrement.get("panel_erc"))
    codes_domaines = elements(enregistrement.get("code_domaine_scientifique"))
    codes_panels = elements(enregistrement.get("code_panel_erc"))
    classifications = [
        {"texte": texte, "source_id": SOURCE_ID, "nature": "PUBLIEE",
         "classification": famille}
        for famille, valeurs in (
            ("domaine_scientifique", domaines),
            ("panel_erc", panels),
        )
        for texte in valeurs
    ]
    fiche = chaine(enregistrement.get("fiche_rnsr"))
    site = chaine(enregistrement.get("site_web"))
    alias = chaine(enregistrement.get("sigle"))
    return {
        "id": f"FRONTIERE-INST-RNSR-{code}",
        "nom_officiel": nom,
        "sigle": alias,
        "aliases": [alias] if alias and alias.casefold() != nom.casefold() else [],
        "famille": "recherche_publique",
        "type_institutionnel": chaine(enregistrement.get("type_de_structure")),
        "etat": "ACTIF",
        "identifiants": {"rnsr": code},
        "missions": [],
        "capacites": [],
        "domaines_recherche": classifications,
        "codes_domaines_recherche": {
            "domaine_scientifique": codes_domaines,
            "panel_erc": codes_panels,
        },
        "site_web": site,
        "fiche_rnsr": fiche,
        "commune_declaree": chaine(enregistrement.get("commune")),
        "code_postal": chaine(enregistrement.get("code_postal")),
        "provenance": [{
            "source_id": SOURCE_ID,
            "identifiant_source": code,
            "url": SOURCE_OFFICIELLE,
            "collecte_le": collecte,
            "empreinte": signature,
        }],
        "observe_le": observe,
        "mise_en_garde": (
            "Discipline ou domaine déclaré dans un répertoire de structures : "
            "aucune capacité opérationnelle ni disponibilité n'est attestée."
        ),
    }


def lire_page_api(offset: int, limite: int = TAILLE_PAGE) -> dict:
    adresse = API + "?" + urllib.parse.urlencode({
        "limit": limite,
        "offset": offset,
        "order_by": "numero_national_de_structure",
    })
    req = urllib.request.Request(
        adresse,
        headers={
            "Accept": "application/json",
            "User-Agent": "FRONTIERE-referentiel-scientifique/1.0",
        },
    )
    for tentative in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as reponse:
                valeur = json.loads(reponse.read().decode("utf-8"))
            if not isinstance(valeur, dict):
                raise ValueError("Réponse RNSR non structurée.")
            return valeur
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            reessayable = not isinstance(exc, urllib.error.HTTPError) or exc.code in {429, 500, 502, 503, 504}
            if not reessayable or tentative == 2:
                raise
            time.sleep(2 ** tentative)
    raise RuntimeError("Récupération des données interrompue.")


def telecharger(
    lire_page: Callable[[int, int], dict] = lire_page_api,
) -> list[dict]:
    tous: list[dict] = []
    attendus = None
    offset = 0
    while attendus is None or offset < attendus:
        page = lire_page(offset, TAILLE_PAGE)
        total = page.get("total_count")
        lignes = page.get("results")
        if type(total) is not int or total < 1 or total > PLAFOND_SOURCE:
            raise ValueError("Nombre de notices RNSR absent ou excessif.")
        if attendus is None:
            attendus = total
        if total != attendus:
            raise ValueError("Le nombre de notices a changé durant la collecte.")
        if not isinstance(lignes, list) or not lignes or len(lignes) > TAILLE_PAGE:
            raise ValueError("Page RNSR absente ou de taille incohérente.")
        for ligne in lignes:
            if not isinstance(ligne, dict):
                raise ValueError("Notice RNSR non structurée.")
            contenu = ligne.get("fields") if isinstance(ligne.get("fields"), dict) else ligne
            tous.append(contenu)
        offset += len(lignes)
        if offset > attendus:
            raise ValueError("Pagination RNSR dépassant le nombre déclaré.")
    identifiants = [identifier(x) for x in tous]
    if len(identifiants) != len(set(identifiants)):
        doublons = [code for code, n in Counter(identifiants).items() if n > 1]
        raise ValueError(
            "Doublon d'identifiant RNSR dans la collecte triée : "
            f"{len(doublons)} identifiant(s), "
            f"premier code source : {sorted(doublons)[0]}."
        )
    return tous


def anciens_index(dossier: Path) -> dict[str, dict]:
    repertoires = dossier / "entites" / "rnsr"
    index = {}
    for fichier in sorted(repertoires.glob("*.jsonl")):
        with fichier.open(encoding="utf-8") as f:
            for ligne in f:
                if ligne.strip():
                    item = json.loads(ligne)
                    identifiant = item.get("identifiants", {}).get("rnsr")
                    if identifiant:
                        if identifiant in index:
                            raise ValueError("Doublon d'identifiant dans la version RNSR précédente.")
                        index[identifiant] = item
    return index


def produire(
    enregistrements: list[dict],
    destination: Path = DESTINATION,
    *,
    minimum: int = 3000,
    date_collecte: str | None = None,
) -> dict:
    if len(enregistrements) < minimum or len(enregistrements) > PLAFOND_SOURCE:
        raise ValueError("Nombre de structures RNSR en dehors du périmètre autorisé.")
    ids = [identifier(item) for item in enregistrements]
    if len(ids) != len(set(ids)):
        raise ValueError("La source contient plusieurs occurrences d'un même identifiant RNSR.")
    destination = Path(destination)
    manifeste_path = destination / "instantanes" / "rnsr_manifest.json"
    stats_path = destination / "statistiques_rnsr.json"
    anciens = anciens_index(destination)
    if anciens and len(ids) < 0.85 * len(anciens):
        raise ValueError("Baisse supérieure à 15 % du nombre de structures : examen nécessaire.")
    sha_source = empreinte(sorted(empreinte(item) for item in enregistrements))
    if manifeste_path.exists() and stats_path.exists():
        manifeste_avant = json.loads(manifeste_path.read_text(encoding="utf-8"))
        if (manifeste_avant.get("sha256_semantique_source") == sha_source
                and manifeste_avant.get("version_transformation") == VERSION_TRANSFORMATION):
            repartition = manifeste_avant.get("empreintes_partitions") or {}
            integre = len(repartition) == PARTITIONS and all(
                (destination / "entites" / "rnsr" / nom).is_file()
                and hashlib.sha256(
                    (destination / "entites" / "rnsr" / nom).read_bytes()
                ).hexdigest() == signature
                for nom, signature in repartition.items()
            )
            if integre:
                return {"statut": "inchangé", **json.loads(stats_path.read_text(encoding="utf-8"))}

    horodatage = date_collecte or maintenant()
    entites = [
        normaliser(item, horodatage, anciens.get(identifier(item)))
        for item in enregistrements
    ]
    entites.sort(key=lambda x: x["id"])
    partitions: list[list[dict]] = [[] for _ in range(PARTITIONS)]
    for item in entites:
        code = item["identifiants"]["rnsr"]
        partition = int(hashlib.sha256(code.encode("ascii")).hexdigest()[:8], 16) % PARTITIONS
        partitions[partition].append(item)
    dossier = destination / "entites" / "rnsr"
    dossier.mkdir(parents=True, exist_ok=True)
    destination.joinpath("instantanes").mkdir(parents=True, exist_ok=True)
    empreintes_partitions = {}
    for rang, bloc in enumerate(partitions):
        fichier = dossier / f"rnsr_{rang:02d}.jsonl"
        temporaire = fichier.with_suffix(".jsonl.tmp")
        with temporaire.open("w", encoding="utf-8") as f:
            for item in bloc:
                f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
        temporaire.replace(fichier)
        empreintes_partitions[fichier.name] = hashlib.sha256(fichier.read_bytes()).hexdigest()

    couverture = Counter()
    for item in entites:
        if item["domaines_recherche"]:
            couverture["avec_domaines_nommes"] += 1
        if any(item["codes_domaines_recherche"].values()):
            couverture["avec_codes_de_classification"] += 1
        if item["site_web"]:
            couverture["avec_site_web"] += 1
        if item["fiche_rnsr"]:
            couverture["avec_fiche_rnsr"] += 1
    stats = {
        "version_schema": "statistiques-structures-recherche-rnsr-v1",
        "nombre_structures": len(entites),
        "partitions": PARTITIONS,
        "couverture": dict(couverture),
        "nombre_capacites_operationnelles_etablies": 0,
        "limite": "Les disciplines publiées ne démontrent aucune compétence mobilisable.",
    }
    manifeste = {
        "version_schema": "instantane-structures-recherche-rnsr-v1",
        "source_id": SOURCE_ID,
        "source_url": SOURCE_OFFICIELLE,
        "api_url": API,
        "version_transformation": VERSION_TRANSFORMATION,
        "collecte_le": horodatage,
        "nombre_structures": len(entites),
        "sha256_semantique_source": sha_source,
        "nombre_partitions": PARTITIONS,
        "empreintes_partitions": empreintes_partitions,
    }
    for chemin, contenu in ((stats_path, stats), (manifeste_path, manifeste)):
        temporaire = chemin.with_suffix(".json.tmp")
        temporaire.write_text(
            json.dumps(contenu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporaire.replace(chemin)
    return {"statut": "actualisé", **stats}


def main() -> None:
    parser = argparse.ArgumentParser(description="Importer les structures de recherche actives du RNSR.")
    parser.add_argument("--source-json", type=Path, help="Réponse JSON locale pour vérification hors réseau.")
    parser.add_argument("--destination", type=Path, default=DESTINATION)
    args = parser.parse_args()
    try:
        if args.source_json:
            brut = json.loads(args.source_json.read_text(encoding="utf-8"))
            if isinstance(brut, list):
                donnees = brut
            elif isinstance(brut, dict) and isinstance(brut.get("results"), list):
                donnees = [
                    x.get("fields", x) if isinstance(x, dict) else x
                    for x in brut["results"]
                ]
                if type(brut.get("total_count")) is int and len(donnees) != brut["total_count"]:
                    raise ValueError("Le fichier d'essai ne contient pas la totalité des notices.")
            else:
                raise ValueError("Format de fichier d'entrée non reconnu.")
        else:
            donnees = telecharger()
        resultat = produire(donnees, args.destination)
    except (ValueError, OSError, TypeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        parser.exit(1, f"Ingestion RNSR refusée : {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
