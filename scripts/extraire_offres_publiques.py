"""Extraire des annonces d'emploi publiques depuis le CSV DGAFP sans contacts privés.

Le fichier source est téléchargé dans un dossier temporaire, vérifié, puis
réduit à des champs déclarés. La copie brute n'est jamais ajoutée à Git.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

if __package__:
    from scripts.sonder_structure_offres_publiques import choisir
else:
    from sonder_structure_offres_publiques import choisir

RACINE = Path(__file__).resolve().parents[1]
DIR = RACINE / "institutionnel" / "besoins_publics"
REPERTOIRE = DIR / "offres_postes"
MANIFESTE = DIR / "manifest_offres_postes.json"
LIMITE_BRUTE = 190_000_000
MAX_LIGNES = 300_000
CLES = {
    "Référence": ("reference", 180),
    "Organisme de rattachement": ("organisme", 240),
    "Versant": ("versant", 80),
    "Métier": ("metier", 220),
    "Statut du poste": ("statut_poste", 120),
    "Nature de l'emploi": ("nature_emploi", 120),
    "Durée du contrat": ("duree_contrat", 100),
    "Intitulé du poste": ("intitule", 400),
    "Localisation du poste": ("localisation", 250),
    "Lieu d'affectation": ("lieu_affectation", 250),
    "Niveau d'études": ("niveau_etudes", 130),
    "Niveau d'expérience min. requis": ("experience_minimale", 100),
    "Date de vacance de l'emploi": ("date_vacance", 45),
    "Date de début de publication par défaut": ("publication_debut", 45),
    "Date de fin de publication par défaut": ("publication_fin", 45),
    "Date de première publication": ("premiere_publication", 45),
    "Spécialisation": ("specialisation", 350),
    "Télétravail": ("teletravail", 80),
    "Employeur": ("employeur", 250),
    "Catégorie": ("categorie", 60),
    "Compétences attendues": ("competences_attendues", 6000),
    "Nature de contrat": ("nature_contrat", 100),
}


class EchecExtraction(ValueError):
    """Échantillon ou schéma impropre à une extraction fiable."""


def texte(v: object, plafond: int) -> str:
    return v.strip()[:plafond] if isinstance(v, str) else ""


def ligne_offre(ligne: dict) -> dict | None:
    reference = texte(ligne.get("Référence"), 180)
    if len(reference) < 3 or any(ord(c) < 32 for c in reference):
        return None
    contenu = {"reference": reference}
    bornes = []
    for source, (cle, limite) in CLES.items():
        if source == "Référence":
            continue
        valeur_brute = ligne.get(source)
        if valeur_brute is not None and not isinstance(valeur_brute, str):
            raise EchecExtraction("Cellule CSV mal formée.")
        valeur = texte(valeur_brute, limite)
        if isinstance(valeur_brute, str) and len(valeur_brute.strip()) > limite:
            bornes.append(cle)
        contenu[cle] = valeur or None
    contenu["champs_tronques"] = sorted(bornes)
    return contenu


def traiter_csv(chemin: Path, colonnes: list[str]) -> tuple[dict[str, dict], dict]:
    if not isinstance(colonnes, list) or len(colonnes) < len(CLES) or len(colonnes) > 300:
        raise EchecExtraction("Schéma de colonnes non vérifié.")
    offres: dict[str, dict] = {}
    variations: dict[str, set[str]] = {}
    lignes, oubliees, identiques, cellules_tronquees = 0, 0, 0, 0
    csv.field_size_limit(4_000_000)
    with chemin.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        if reader.fieldnames != colonnes:
            raise EchecExtraction("Schéma du CSV différent de celui vérifié officiellement.")
        if not set(CLES).issubset(reader.fieldnames):
            raise EchecExtraction("Champs scientifiques essentiels absents du CSV.")
        for ligne in reader:
            lignes += 1
            if lignes > MAX_LIGNES:
                raise EchecExtraction("Plafond des offres dépassé ; répartir la collecte.")
            if None in ligne:
                raise EchecExtraction("La ligne comporte davantage de cellules que le schéma.")
            valeur = ligne_offre(ligne)
            if valeur is None:
                oubliees += 1
                continue
            cellules_tronquees += len(valeur["champs_tronques"])
            reference = valeur["reference"]
            projection = json.dumps(valeur, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")
            cle = hashlib.sha256(projection).hexdigest()
            variations.setdefault(reference, set()).add(cle)
            valeur["cle_enregistrement"] = cle
            if cle in offres:
                if offres[cle] != valeur:
                    raise EchecExtraction("Collision d'empreintes des annonces.")
                identiques += 1
                continue
            offres[cle] = valeur
    if not offres:
        raise EchecExtraction("Le CSV ne comporte aucune annonce identifiable.")
    return offres, {
        "lignes_lues": lignes,
        "lignes_sans_reference": oubliees,
        "doublons_identiques": identiques,
        "references_distinctes": len(variations),
        "references_avec_plusieurs_variantes": sum(len(x) > 1 for x in variations.values()),
        "variantes_supplementaires_de_reference": sum(len(x)-1 for x in variations.values()),
        "offres_distinctes": len(offres),
        "cellules_tronquees": cellules_tronquees,
        "couverture_integrale_du_csv": oubliees == 0 and cellules_tronquees == 0,
    }


def telecharger_csv(url: str, taille_attendue: int | None, cible: Path) -> dict:
    if not url.startswith("https://static.data.gouv.fr/resources/"):
        raise EchecExtraction("Adresse de téléchargement différente de la plateforme officielle.")
    request = Request(url, headers={
        "User-Agent": "FRONTIERE-offres-emplois-publics/1.0",
        "Accept-Encoding": "identity",
    })
    taille, empreinte = 0, hashlib.sha256()
    with urlopen(request, timeout=90) as reponse:
        if reponse.status != 200:
            raise EchecExtraction("Réponse HTTP du fichier d'emploi incorrecte.")
        final = urlparse(reponse.geturl())
        if final.scheme != "https" or final.hostname != "static.data.gouv.fr":
            raise EchecExtraction("Fichier redirigé hors du site officiel.")
        with cible.open("wb") as sortie:
            while bloc := reponse.read(1024 * 1024):
                taille += len(bloc)
                if taille > LIMITE_BRUTE:
                    raise EchecExtraction("Le fichier dépasse la limite de téléchargement.")
                empreinte.update(bloc)
                sortie.write(bloc)
    if taille_attendue is not None and taille != taille_attendue:
        raise EchecExtraction("Le nombre d'octets diffère du catalogue officiel.")
    return {"octets_telecharges": taille, "sha256_csv": empreinte.hexdigest()}


def partitions(offres: dict[str, dict]) -> dict[str, list[str]]:
    resultat = {f"{x:02x}": [] for x in range(16)}
    for reference in sorted(offres):
        part = f"{int(hashlib.sha256(reference.encode('utf-8')).hexdigest()[0], 16):02x}"
        resultat[part].append(json.dumps(offres[reference], ensure_ascii=False, sort_keys=True,
                                          separators=(",", ":")) + "\n")
    return resultat


def empreinte_partition(chemin: Path) -> str:
    """Calculer l'empreinte d'une partition sans charger son contenu en mémoire."""
    empreinte = hashlib.sha256()
    with chemin.open("rb") as flux:
        for bloc in iter(lambda: flux.read(1024 * 1024), b""):
            empreinte.update(bloc)
    return empreinte.hexdigest()


def partitions_verifiees(dossier: Path, manifeste: dict) -> bool:
    """Vérifier les seize fichiers avant de réutiliser un extrait précédent.

    Un ancien manifeste dépourvu d'empreintes est considéré comme non vérifié :
    l'extraction suivante le remplacera à partir de la source officielle.
    """
    attendu = {f"lot_{x:02x}.jsonl" for x in range(16)}
    empreintes = manifeste.get("empreintes_partitions")
    if not isinstance(empreintes, dict) or set(empreintes) != attendu:
        return False
    if not isinstance(manifeste.get("offres_distinctes"), int) or manifeste["offres_distinctes"] <= 0:
        return False
    for nom in sorted(attendu):
        empreinte = empreintes[nom]
        if not isinstance(empreinte, str) or len(empreinte) != 64:
            return False
        chemin = dossier / "offres_postes" / nom
        if not chemin.is_file() or empreinte_partition(chemin) != empreinte:
            return False
    return True


def publier(offres: dict[str, dict], dossier: Path, manifeste: dict) -> None:
    cible = dossier / "offres_postes"
    cible.mkdir(parents=True, exist_ok=True)
    lignes = partitions(offres)
    empreintes = {}
    for cle in sorted(lignes):
        nom = f"lot_{cle}.jsonl"
        dest = cible / nom
        contenu = "".join(lignes[cle])
        octets = contenu.encode("utf-8")
        empreintes[nom] = hashlib.sha256(octets).hexdigest()
        if dest.is_file() and empreinte_partition(dest) == empreintes[nom]:
            continue
        temporaire = dest.with_suffix(".jsonl.tmp")
        temporaire.write_bytes(octets)
        temporaire.replace(dest)
    # Le manifeste est publié en dernier, après la remise en état des seize lots.
    manifeste["empreintes_partitions"] = empreintes
    fichier = dossier / "manifest_offres_postes.json"
    temp = fichier.with_suffix(".json.tmp")
    temp.write_text(json.dumps(manifeste, ensure_ascii=False, sort_keys=True, indent=2) +
                    "\n", encoding="utf-8")
    temp.replace(fichier)


def executer(dossier: Path = DIR) -> dict:
    inventaire = json.loads((dossier / "ressources_emplois_publics.json").read_text(encoding="utf-8"))
    schema = json.loads((dossier / "schema_emplois_publics.json").read_text(encoding="utf-8"))
    if inventaire.get("licence_declaree") not in ("lov2", "lov1"):
        raise EchecExtraction("Licence non confirmée.")
    fichier = choisir(inventaire["ressources"])
    if schema.get("source_id") != fichier["id"] or schema.get("separateur") != "point-virgule":
        raise EchecExtraction("Le fichier et son schéma officiel ne concordent plus.")
    cible = dossier / "manifest_offres_postes.json"
    ancien = json.loads(cible.read_text(encoding="utf-8")) if cible.is_file() else {}
    if (ancien.get("source_id") == fichier["id"]
            and ancien.get("source_modifie_le") == fichier.get("modifie_le")
            and partitions_verifiees(dossier, ancien)):
        return {"etat": "inchangé", "source_id": fichier["id"],
                "offres_distinctes": ancien.get("offres_distinctes")}
    with tempfile.TemporaryDirectory(prefix="frontiere-csp-") as tmp:
        brut = Path(tmp) / "offres-source.csv"
        empreintes = telecharger_csv(fichier["url"], fichier.get("taille_octets_declaree"), brut)
        offres, bilan = traiter_csv(brut, schema["colonnes"])
    maintenant = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifeste = {
        "version": "emplois-publics-extraits-v1",
        "source_id": fichier["id"],
        "source_modifie_le": fichier.get("modifie_le"),
        "source_url": fichier["url"],
        "extraire_le": maintenant,
        "colonnes_source_verifiees": len(schema["colonnes"]),
        "champs_offres_extraits": [cle for cle, _ in CLES.values() if cle != "reference"],
        "fichier_brut_conserve_dans_git": False,
        "lignes_de_contacts_nominatifs_reproduites": False,
        **empreintes,
        **bilan,
    }
    publier(offres, dossier, manifeste)
    return manifeste


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dossier", type=Path, default=DIR)
    args = parser.parse_args()
    try:
        resultat = executer(args.dossier)
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, csv.Error) as err:
        parser.exit(1, f"Extraction des offres interrompue : {type(err).__name__}: {err}\n")


if __name__ == "__main__":
    main()
