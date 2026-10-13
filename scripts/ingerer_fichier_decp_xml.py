"""Lire les données essentielles XML des marchés publics, sans charger le document.

Profil d'extraction volontairement réduit : identité acheteur/marché, objet,
CPV, notification et montant. L'analyse ne vaut pas validation complète au
schéma réglementaire, et une attribution n'établit pas un besoin encore ouvert.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

if __package__:
    from scripts.ingerer_fichier_decp_json import normaliser_marche, DocumentDECPInvalide
else:
    from ingerer_fichier_decp_json import normaliser_marche, DocumentDECPInvalide

PLAFOND_FICHIER = 2_000_000
PLAFOND_NOTICES = 20_000
PLAFOND_EXTRAITS = 1000
PLAFOND_PROFONDEUR = 48
SOURCES = {"dgfip_pes_marche", "aife_api_decp", "mef_decp_consolides"}
RESSOURCE = re.compile(r"^[0-9a-fA-F-]{36}$")


class XMLDECPInvalide(ValueError):
    """Relevé XML mal formé, incomplet ou dépassant ses limites."""


def _nom(tag: str) -> str:
    """Retirer uniquement le nom d'espace XML, sans modifier le contenu."""
    return tag.rsplit("}", 1)[-1]


def _enfant(element: ET.Element, nom: str) -> ET.Element | None:
    """Trouver un enfant immédiat, éventuellement avec espace de noms."""
    return next((e for e in element if _nom(e.tag) == nom), None)


def _contenu(element: ET.Element, nom: str) -> str | None:
    """Extraire un champ scalaire enfant, sans agréger les champs descendants."""
    valeur = _enfant(element, nom)
    if valeur is None:
        return None
    return valeur.text.strip() if valeur.text and valeur.text.strip() else None


def _entier(valeur: str | None, champ: str) -> int | None:
    if valeur is None:
        return None
    if not re.fullmatch(r"[0-9]{1,12}", valeur):
        raise XMLDECPInvalide(f"Nombre entier incorrect : {champ}")
    return int(valeur)


def _nombre(valeur: str | None) -> float | None:
    if valeur is None:
        return None
    if not re.fullmatch(r"[0-9]{1,15}(?:\.[0-9]{1,8})?", valeur):
        raise XMLDECPInvalide("Montant XML incorrect")
    montant = float(valeur)
    if not math.isfinite(montant):
        raise XMLDECPInvalide("Montant non fini")
    return montant


def _booleen(valeur: str | None) -> bool | None:
    if valeur is None:
        return None
    valeurs = {"oui": True, "non": False, "true": True, "false": False}
    if valeur.lower() not in valeurs:
        raise XMLDECPInvalide("Booléen XML inconnu")
    return valeurs[valeur.lower()]


def normaliser_xml(
    element: ET.Element, anomalies_facultatives: list[str] | None = None
) -> dict:
    """Valider les champs essentiels sans perdre un marché pour un champ accessoire."""
    anomalies = anomalies_facultatives if anomalies_facultatives is not None else []
    if _nom(element.tag) != "marche":
        raise XMLDECPInvalide("Objet XML qui n'est pas un marché")
    acheteur = _enfant(element, "acheteur")
    try:
        offres = _entier(_contenu(element, "offresRecues"), "offresRecues")
    except XMLDECPInvalide:
        offres = None
        anomalies.append("offresRecues_non_interpretable")
    try:
        innovant = _booleen(_contenu(element, "marcheInnovant"))
    except XMLDECPInvalide:
        innovant = None
        anomalies.append("marcheInnovant_non_interpretable")
    champs = {
        "id": _contenu(element, "id"),
        "acheteur": {"id": _contenu(acheteur, "id") if acheteur is not None else None},
        "objet": _contenu(element, "objet"),
        "codeCPV": _contenu(element, "codeCPV"),
        "nature": _contenu(element, "nature"),
        "dateNotification": _contenu(element, "dateNotification"),
        "datePublicationDonnees": _contenu(element, "datePublicationDonnees"),
        "montant": _nombre(_contenu(element, "montant")),
        "offresRecues": offres,
        "marcheInnovant": innovant,
        "_type": "Marché",
    }
    try:
        return normaliser_marche(champs)
    except DocumentDECPInvalide as exc:
        raise XMLDECPInvalide(str(exc)) from exc


def _interdire_definitions_xml(fichier: Path) -> None:
    """Refuser les définitions DTD et entités avant l'analyse XML.

    Le fichier traité est de taille plafonnée et uniquement en octets UTF-8.
    Aucun parseur externe ni chargement d'entité externe n'est utilisé.
    """
    debut = b""
    with fichier.open("rb") as stream:
        while bloc := stream.read(65536):
            partie = (debut + bloc).upper()
            if b"<!DOCTYPE" in partie or b"<!ENTITY" in partie:
                raise XMLDECPInvalide("Déclaration DTD ou entité XML interdite")
            debut = partie[-16:]


def _preparer_source_xml(fichier: Path) -> tuple[Path | io.BytesIO, dict]:
    """Rectifier uniquement l'attribut de namespace mal formé observé DGFiP.

    Les ressources réelles du 13 octobre 2026 ont toutes une séquence
    xmlns:="http... dans l'élément racine. Le ':' isolé rend la déclaration
    syntaxiquement invalide. La correction est confinée à la racine et
    chaque octet original reste attesté par l'empreinte du fichier brut.
    """
    original = fichier.read_bytes()
    anomalie = b'xmlns:="'
    occurrences = original.count(anomalie)
    if occurrences == 0:
        return fichier, {
            "type": "aucune",
            "occurrences": 0,
            "sha256_contenu_analyse": hashlib.sha256(original).hexdigest(),
        }
    if occurrences != 1:
        raise XMLDECPInvalide(
            "Plusieurs déclarations de namespace invalides : correction refusée"
        )
    racine = original.find(b"<marches")
    position = original.find(anomalie)
    fin = original.find(b">", racine) if racine >= 0 else -1
    if (
        not (0 <= racine < position < fin < 4096)
        or position == 0
        or original[position - 1:position] not in (b" ", b"\t", b"\r", b"\n")
    ):
        raise XMLDECPInvalide(
            "Anomalie de namespace hors de l'élément racine : correction refusée"
        )
    # Supprimer exactement le ':' du nom de l'attribut.
    corrige = original[:position] + original[position:].replace(
        anomalie, b'xmlns="', 1
    )
    return io.BytesIO(corrige), {
        "type": "rectification_lexicale_declaration_xmlns_vide",
        "occurrences": 1,
        "sha256_contenu_analyse": hashlib.sha256(corrige).hexdigest(),
        "copie_temporaire_uniquement": True,
        "conformite_reglementaire_du_document_etablie": False,
    }


def analyser_fichier(
    fichier: Path, *, source_id: str, ressource_id: str,
    limite_extraits: int = PLAFOND_EXTRAITS,
) -> dict:
    """Parcourir un fichier XML borné en préservant des comptes exacts."""
    if source_id not in SOURCES or not RESSOURCE.fullmatch(ressource_id):
        raise XMLDECPInvalide("Identifiants de source ou ressource incorrects")
    if type(limite_extraits) is not int or not 0 <= limite_extraits <= PLAFOND_EXTRAITS:
        raise XMLDECPInvalide("Plafond des extraits hors limites")
    taille = fichier.stat().st_size
    if not 0 < taille <= PLAFOND_FICHIER:
        raise XMLDECPInvalide("Taille du document non admissible")
    with fichier.open("rb") as stream:
        prefixe = stream.read(4)
    if prefixe.startswith((b"\xff\xfe", b"\xfe\xff", b"\x00")):
        raise XMLDECPInvalide("Encodage XML non UTF-8")
    _interdire_definitions_xml(fichier)
    h = hashlib.sha256()
    with fichier.open("rb") as stream:
        while bloc := stream.read(65536):
            h.update(bloc)

    comptes = Counter()
    rejets = Counter()
    anomalies_optionnelles = Counter()
    cpvs = Counter()
    vus: dict[tuple[str, str], str] = {}
    extraits = []
    profondeur = 0
    racine = None
    source_analyse, transformation = _preparer_source_xml(fichier)
    try:
        for evenement, element in ET.iterparse(source_analyse, events=("start", "end")):
            tag = _nom(element.tag)
            if evenement == "start":
                profondeur += 1
                if profondeur > PLAFOND_PROFONDEUR:
                    raise XMLDECPInvalide("Profondeur XML supérieure au plafond")
                if racine is None:
                    racine = element
                    if tag != "marches":
                        raise XMLDECPInvalide("Racine XML inattendue")
                continue
            if profondeur == 2 and tag in ("marche", "contrat-concession"):
                comptes["objets_documentaires_lus"] += 1
                if comptes["objets_documentaires_lus"] > PLAFOND_NOTICES:
                    raise XMLDECPInvalide("Nombre de notices trop important")
                if tag == "contrat-concession":
                    comptes["concessions_non_normalisees"] += 1
                else:
                    comptes["notices_lues"] += 1
                    anomalies_notice = []
                    try:
                        notice = normaliser_xml(element, anomalies_notice)
                    except XMLDECPInvalide as exc:
                        comptes["notices_rejetees"] += 1
                        rejets[str(exc)] += 1
                    else:
                        cle = (notice["acheteur_siret"], notice["id_marche"])
                        empreinte = hashlib.sha256(json.dumps(
                            notice, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":"), allow_nan=False,
                        ).encode("utf-8")).hexdigest()
                        precedent = vus.get(cle)
                        if precedent is not None:
                            comptes[
                                "doublons_exacts_dans_fichier"
                                if precedent == empreinte
                                else "conflits_de_versions_dans_fichier"
                            ] += 1
                        else:
                            vus[cle] = empreinte
                            comptes["marches_uniques_valides"] += 1
                            if notice["code_cpv"]:
                                cpvs[notice["code_cpv"][:2]] += 1
                            if len(extraits) < limite_extraits:
                                extraits.append(notice)
                    anomalies_optionnelles.update(anomalies_notice)
                element.clear()
                if racine is not None:
                    racine.clear()
            profondeur -= 1
        if racine is None or profondeur != 0:
            raise XMLDECPInvalide("Document XML sans racine complète")
    except ET.ParseError as exc:
        # Ne conserver qu'une fenêtre de codes numériques autour de l'erreur.
        # Aucun texte de marché ni fragment XML n'est journalisé.
        ligne, colonne = exc.position
        with fichier.open("rb") as raw:
            lignes = raw.read(min(taille, 4096)).splitlines()
        fenetre = []
        if 0 < ligne <= len(lignes):
            fragment = lignes[ligne - 1]
            debut = max(0, colonne - 4)
            fin = min(len(fragment), colonne + 5)
            fenetre = list(fragment[debut:fin])
        raise XMLDECPInvalide(
            f"Erreur de syntaxe XML (code {exc.code}, ligne {ligne}, "
            f"colonne {colonne}, octets_proches={fenetre})"
        ) from exc
    return {
        "version": "decp-fichier-xml-v1", "source_catalogue": source_id,
        "ressource_id": ressource_id, "sha256_fichier_brut": h.hexdigest(),
        "transformation_xml": transformation,
        "taille_fichier_octets": taille,
        "releves": dict(sorted(comptes.items())),
        "rejets_par_categorie": dict(sorted(rejets.items())),
        "anomalies_champs_facultatifs": dict(sorted(anomalies_optionnelles.items())),
        "categories_cpv_prefixe_2": dict(sorted(cpvs.items())),
        "marches_extraits": extraits,
        "extraits_plafonnes": len(extraits) < comptes["marches_uniques_valides"],
        "conformite_complete_au_schema_reglementaire_verifiee": False,
        "besoins_encore_ouverts_etablis": 0,
        "correspondances_boamp_verifiees": 0,
        "releve_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> None:
    """Analyser hors réseau un fichier XML public déjà obtenu."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--entree", type=Path, required=True)
    p.add_argument("--source", choices=sorted(SOURCES), required=True)
    p.add_argument("--ressource-id", required=True)
    p.add_argument("--sortie", type=Path, required=True)
    p.add_argument("--extraits", type=int, default=PLAFOND_EXTRAITS)
    args = p.parse_args()
    try:
        resultat = analyser_fichier(args.entree, source_id=args.source,
                                   ressource_id=args.ressource_id,
                                   limite_extraits=args.extraits)
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        temporaire = args.sortie.with_name(args.sortie.name + ".tmp")
        temporaire.write_text(
            json.dumps(resultat, ensure_ascii=False, indent=2, sort_keys=True,
                       allow_nan=False) + "\n", encoding="utf-8"
        )
        temporaire.replace(args.sortie)
        print(json.dumps({k: v for k, v in resultat.items() if k != "marches_extraits"},
                         ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, UnicodeError) as exc:
        p.exit(1, f"XML DECP refusé : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
