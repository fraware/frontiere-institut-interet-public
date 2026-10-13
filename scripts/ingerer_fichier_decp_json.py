"""Lire en flux un fichier JSON de données essentielles de marchés publics.

Premier périmètre : un fichier local de taille plafonnée, schémas JSON « marches »
et « marches.marche ». Les notices sont contrôlées sur un sous-ensemble de champs :
ce programme ne prétend pas assurer la conformité réglementaire complète.
Aucune ressource distante n'est téléchargée par ce module.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, TextIO

RACINE = Path(__file__).resolve().parents[1]
MAX_FICHIER_OCTETS = 16_000_000
MAX_OBJET_CARACTERES = 2_000_000
MAX_NOTICES = 50_000
MAX_EXTRAITS = 200
BLOC_CARACTERES = 65536
SIRET = re.compile(r"^[0-9]{14}$")
CPV = re.compile(r"^[0-9]{8}(?:-[0-9])?$")
RESSOURCE = re.compile(r"^[0-9a-fA-F-]{32,40}$")
SOURCE = frozenset({"aife_api_decp", "mef_decp_consolides", "dgfip_pes_marche"})


class DocumentDECPInvalide(ValueError):
    """La structure JSON, l'origine ou une limite explicite est incorrecte."""


class LecteurJSON:
    """Décoder les objets successifs, sans charger un grand tableau complet."""

    def __init__(self, flux: TextIO):
        self.flux = flux
        self.tampon = ""
        self.position = 0
        self.fin = False
        self.decodeur = json.JSONDecoder(parse_constant=self._constante_invalide)

    @staticmethod
    def _constante_invalide(valeur: str) -> None:
        raise DocumentDECPInvalide(f"Valeur JSON numérique interdite : {valeur}")

    def _remplir(self) -> bool:
        if self.fin:
            return False
        if self.position:
            self.tampon = self.tampon[self.position:]
            self.position = 0
        ajout = self.flux.read(BLOC_CARACTERES)
        if not ajout:
            self.fin = True
            return False
        self.tampon += ajout
        return True

    def caractere(self) -> str:
        while True:
            while self.position < len(self.tampon) and self.tampon[self.position].isspace():
                self.position += 1
            if self.position < len(self.tampon):
                return self.tampon[self.position]
            if not self._remplir():
                return ""

    def attendre(self, caractere: str) -> None:
        trouve = self.caractere()
        if trouve != caractere:
            raise DocumentDECPInvalide(
                f"Symbole attendu : {caractere!r}, obtenu : {trouve!r}"
            )
        self.position += 1

    def valeur(self) -> Any:
        self.caractere()
        while True:
            try:
                resultat, fin = self.decodeur.raw_decode(self.tampon, self.position)
                if fin - self.position > MAX_OBJET_CARACTERES:
                    raise DocumentDECPInvalide("Notice supérieure au plafond")
                self.position = fin
                return resultat
            except json.JSONDecodeError as exc:
                if len(self.tampon) - self.position >= MAX_OBJET_CARACTERES:
                    raise DocumentDECPInvalide("Notice trop longue ou mal formée") from exc
                if not self._remplir():
                    raise DocumentDECPInvalide("Document JSON tronqué ou incorrect") from exc


def _iterer_tableau(lecteur: LecteurJSON, categorie: str, total: list[int],
                   plafond_notices: int):
    """Parcourir un tableau nommé, avec plafond global sur les deux catégories."""
    lecteur.attendre("[")
    while lecteur.caractere() != "]":
        if total[0] >= plafond_notices:
            raise DocumentDECPInvalide("Nombre total de notices supérieur au plafond")
        enregistrement = lecteur.valeur()
        total[0] += 1
        yield categorie, enregistrement
        symbole = lecteur.caractere()
        if symbole == ",":
            lecteur.attendre(",")
            if lecteur.caractere() == "]":
                raise DocumentDECPInvalide("Virgule finale dans le tableau")
        elif symbole != "]":
            raise DocumentDECPInvalide("Séparateur du tableau invalide")
    lecteur.attendre("]")


def iterer_documents(flux: TextIO, *, plafond_notices: int = MAX_NOTICES):
    """Parcourir marchés et concessions comme catégories documentaires distinctes.

    L'interface AIFE observée le 13 octobre 2026 utilise :
    {"marches":{"marche":[...],"contrat-concession":[...]}}.
    L'ordre des deux membres ne porte aucune signification. Une structure
    inconnue est refusée, sans omission silencieuse.
    """
    if (type(plafond_notices) is not int
            or not 1 <= plafond_notices <= 200_000):
        raise DocumentDECPInvalide("Plafond de notices non admissible")
    lecteur = LecteurJSON(flux)
    total = [0]
    racine = lecteur.caractere()
    if racine == "[":
        yield from _iterer_tableau(lecteur, "marche", total, plafond_notices)
    elif racine == "{":
        lecteur.attendre("{")
        if lecteur.valeur() != "marches":
            raise DocumentDECPInvalide("Seule la clé principale marches est reconnue")
        lecteur.attendre(":")
        if lecteur.caractere() == "[":
            yield from _iterer_tableau(lecteur, "marche", total, plafond_notices)
        elif lecteur.caractere() == "{":
            lecteur.attendre("{")
            noms = set()
            while lecteur.caractere() != "}":
                nom = lecteur.valeur()
                if nom not in ("marche", "contrat-concession") or nom in noms:
                    raise DocumentDECPInvalide("Collection inconnue ou répétée dans marches")
                noms.add(nom)
                lecteur.attendre(":")
                yield from _iterer_tableau(lecteur, nom, total, plafond_notices)
                symbole = lecteur.caractere()
                if symbole == ",":
                    lecteur.attendre(",")
                    if lecteur.caractere() == "}":
                        raise DocumentDECPInvalide("Virgule finale dans les collections")
                elif symbole != "}":
                    raise DocumentDECPInvalide("Séparateur des collections invalide")
            lecteur.attendre("}")
            if "marche" not in noms:
                raise DocumentDECPInvalide("Collection de marchés absente")
        else:
            raise DocumentDECPInvalide("Valeur de la clé marches non prise en charge")
        lecteur.attendre("}")
    else:
        raise DocumentDECPInvalide("Racine JSON de marchés non reconnue")
    if lecteur.caractere():
        raise DocumentDECPInvalide("Contenu supplémentaire après la racine")


def iterer_marches(flux: TextIO):
    """Interface de compatibilité ne retournant que les notices de marchés."""
    for categorie, notice in iterer_documents(flux):
        if categorie == "marche":
            yield notice


def _chaine(valeur: object, maximum: int) -> str | None:
    if not isinstance(valeur, str) or not 0 < len(valeur.strip()) <= maximum:
        return None
    return valeur.strip()


def _date(valeur: object) -> str | None:
    if valeur is None:
        return None
    if not isinstance(valeur, str):
        raise DocumentDECPInvalide("Date non textuelle")
    try:
        return date.fromisoformat(valeur).isoformat()
    except ValueError as exc:
        raise DocumentDECPInvalide("Date calendaire incorrecte") from exc


def normaliser_marche(brut: object) -> dict:
    """Extraire des champs essentiels sans qualifier la mission ni l'exécution."""
    if not isinstance(brut, dict):
        raise DocumentDECPInvalide("Notice qui n'est pas un objet JSON")
    if brut.get("_type") not in (None, "Marché"):
        raise DocumentDECPInvalide("Objet de concession ou autre type non traité")
    acheteur = brut.get("acheteur")
    numero = _chaine(brut.get("id"), 100)
    siret = acheteur.get("id") if isinstance(acheteur, dict) else None
    objet = _chaine(brut.get("objet"), 1000)
    if not numero or not isinstance(siret, str) or not SIRET.fullmatch(siret):
        raise DocumentDECPInvalide("Identité composite acheteur et marché absente")
    if not objet:
        raise DocumentDECPInvalide("Objet du marché absent")
    cpv = brut.get("codeCPV")
    if cpv is not None and (not isinstance(cpv, str) or not CPV.fullmatch(cpv)):
        raise DocumentDECPInvalide("Code CPV invalide")
    montant = brut.get("montant")
    if montant is not None and (
        type(montant) not in (int, float) or not math.isfinite(montant) or montant < 0
    ):
        raise DocumentDECPInvalide("Montant non admissible")
    offres = brut.get("offresRecues")
    if offres is not None and (type(offres) is not int or offres < 0):
        raise DocumentDECPInvalide("Nombre d'offres non admissible")
    nature = _chaine(brut.get("nature"), 100)
    if nature not in ("Marché", "Marché de partenariat", "Marché de défense ou de sécurité", None):
        raise DocumentDECPInvalide("Nature non reconnue")
    return {
        "id_marche": numero,
        "acheteur_siret": siret,
        "objet": objet,
        "code_cpv": cpv,
        "nature": nature,
        "date_notification": _date(brut.get("dateNotification")),
        "date_publication_declaree": _date(brut.get("datePublicationDonnees")),
        "montant_euros_ht_declare": montant,
        "offres_recues_declarees": offres,
        "marche_innovant_declare": (
            brut["marcheInnovant"] if type(brut.get("marcheInnovant")) is bool else None
        ),
        "preuve_de_premiere_contribution": False,
        "besoin_encore_ouvert_demontre": False,
    }


def traiter_fichier(
    entree: Path, *, source_id: str, ressource_id: str,
    limite_extraits: int = MAX_EXTRAITS,
) -> dict:
    """Produire un bilan exact du fichier, avec un extrait plafonné de notices."""
    if source_id not in SOURCE or not isinstance(ressource_id, str) or not RESSOURCE.fullmatch(ressource_id):
        raise DocumentDECPInvalide("Provenance de ressource non admise")
    if type(limite_extraits) is not int or not 0 <= limite_extraits <= MAX_EXTRAITS:
        raise DocumentDECPInvalide("Plafond des extraits incorrect")
    taille = entree.stat().st_size
    if not 0 < taille <= MAX_FICHIER_OCTETS:
        raise DocumentDECPInvalide("Fichier vide ou hors plafond de taille")
    empreinte = hashlib.sha256()
    with entree.open("rb") as handle:
        for bloc in iter(lambda: handle.read(65536), b""):
            empreinte.update(bloc)
    compteur = Counter()
    categories_rejets = Counter()
    observables = []
    vus = {}
    cpv_categories = Counter()
    with entree.open("r", encoding="utf-8-sig") as handle:
        for categorie, brut in iterer_documents(handle):
            compteur["objets_documentaires_lus"] += 1
            if categorie == "contrat-concession":
                compteur["concessions_non_normalisees"] += 1
                continue
            compteur["notices_lues"] += 1
            try:
                ligne = normaliser_marche(brut)
            except DocumentDECPInvalide as exc:
                compteur["notices_rejetees"] += 1
                categories_rejets[str(exc)] += 1
                continue
            cle = (ligne["acheteur_siret"], ligne["id_marche"])
            signature = hashlib.sha256(json.dumps(
                ligne, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")).hexdigest()
            precedent = vus.get(cle)
            if precedent is not None:
                if precedent == signature:
                    compteur["doublons_exacts_dans_fichier"] += 1
                else:
                    compteur["conflits_de_versions_dans_fichier"] += 1
                continue
            vus[cle] = signature
            compteur["marches_uniques_valides"] += 1
            cpv = ligne["code_cpv"]
            if cpv:
                cpv_categories[cpv[:2]] += 1
            if len(observables) < limite_extraits:
                observables.append(ligne)
    return {
        "version": "decp-fichier-json-v1",
        "source_catalogue": source_id,
        "ressource_id": ressource_id,
        "sha256_fichier_brut": empreinte.hexdigest(),
        "taille_fichier_octets": taille,
        "releves": dict(sorted(compteur.items())),
        "rejets_par_categorie": dict(sorted(categories_rejets.items())),
        "categories_cpv_prefixe_2": dict(sorted(cpv_categories.items())),
        "marches_extraits": observables,
        "extraits_plafonnes": len(observables) < compteur["marches_uniques_valides"],
        "conformite_complete_au_schema_reglementaire_verifiee": False,
        "lien_boamp_demontre": False,
        "premiere_contribution_utile_observee": False,
        "releve_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> None:
    """Traiter un fichier déjà disponible localement sans le télécharger."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entree", type=Path, required=True)
    parser.add_argument("--source", choices=sorted(SOURCE), required=True)
    parser.add_argument("--ressource-id", required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--extraits", type=int, default=MAX_EXTRAITS)
    args = parser.parse_args()
    try:
        bilan = traiter_fichier(
            args.entree, source_id=args.source,
            ressource_id=args.ressource_id, limite_extraits=args.extraits,
        )
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        temporaire = args.sortie.with_name(args.sortie.name + ".tmp")
        temporaire.write_text(
            json.dumps(bilan, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            + "\n", encoding="utf-8",
        )
        temporaire.replace(args.sortie)
        print(json.dumps({k: v for k, v in bilan.items() if k != "marches_extraits"},
                         ensure_ascii=False, sort_keys=True))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.exit(1, f"Ingestion DECP refusée : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
