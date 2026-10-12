"""Qualifier une attribution BOAMP FNSimple ou MAPA sans inventer de lot.

Ces formats ne contiennent pas les nœuds eForms de résultat par lot.
Les observations hors lot ne participent pas au calcul des lots attribués.
"""
from __future__ import annotations
from datetime import date
import json


class AutreFormatInvalide(ValueError):
    """Structure de source ou contenu contradictoire."""


def chemin(racine, *cles):
    for cle in cles:
        if not isinstance(racine, dict):
            return None
        racine = racine.get(cle)
    return racine


def qualification_hors_eforms(notice):
    brut = notice.get("donnees")
    if not isinstance(brut, str):
        raise AutreFormatInvalide("Formulaire absent.")
    try:
        structure = json.loads(brut)
    except json.JSONDecodeError as exc:
        raise AutreFormatInvalide("Formulaire illisible.") from exc
    if not isinstance(structure, dict) or len(structure) != 1:
        raise AutreFormatInvalide("Structure à racines multiples ou vide.")

    if "FNSimple" in structure:
        texte = chemin(structure, "FNSimple", "attribution", "attributionMarche")
        if not isinstance(texte, str) or not texte.strip():
            raise AutreFormatInvalide("Description textuelle de l'attribution absente.")
        return {
            "statut_releve": "attribution_textuelle_non_lotifiee",
            "nature": "ATTRIBUTION",
            "format_source": "fnsimple",
            "resultats_lots": [],
            "observations_hors_lots": [{
                "nature": "declaration_textuelle_non_codee",
                "texte_officiel": texte,
                "origine_champ": "/FNSimple/attribution/attributionMarche",
                "identifiant_lot_verifie": None,
                "qualification_regle_automatique": None,
                "confirmation_independante": False,
            }],
            "erreur_extracteur": None,
        }

    if "MAPA" in structure:
        attribution = chemin(structure, "MAPA", "attribution")
        resultat = chemin(attribution, "attribution", "resultat")
        if not isinstance(resultat, dict) or set(resultat) != {"attribue"}:
            raise AutreFormatInvalide("Résultat MAPA sans attribution structurée unique.")
        attribue = resultat["attribue"]
        titulaire = chemin(attribue, "titulaire", "PersonneMorale")
        if not isinstance(titulaire, str) or not titulaire.strip():
            raise AutreFormatInvalide("Titulaire MAPA non documenté.")
        info = attribution.get("autresInformations")
        offres = chemin(info, "nbOffresRecues")
        if offres is not None:
            if type(offres) is int and offres >= 0:
                n = offres
            elif isinstance(offres, str) and offres.isascii() and offres.isdecimal():
                n = int(offres)
            else:
                raise AutreFormatInvalide("Nombre d'offres MAPA invalide.")
            if n == 0:
                raise AutreFormatInvalide("Attribution MAPA avec zéro offre déclarée.")
        else:
            n = None
        date_attr = chemin(info, "dateAttribution")
        if date_attr is not None:
            if not isinstance(date_attr, str):
                raise AutreFormatInvalide("Date d'attribution MAPA invalide.")
            try:
                if date.fromisoformat(date_attr).isoformat() != date_attr:
                    raise ValueError("Date non canonique")
            except ValueError as exc:
                raise AutreFormatInvalide("Date d'attribution MAPA invalide.") from exc
        return {
            "statut_releve": "attribution_structuree_sans_numero_lot",
            "nature": "ATTRIBUTION",
            "format_source": "mapa",
            "resultats_lots": [],
            "observations_hors_lots": [{
                "nature": "attribution_structurée_non_lotifiée",
                "titulaire_declare": titulaire,
                "origine_titulaire": "/MAPA/attribution/attribution/resultat/attribue/titulaire/PersonneMorale",
                "nombre_offres_declare": n,
                "origine_nombre_offres": "/MAPA/attribution/autresInformations/nbOffresRecues",
                "date_attribution_declaree": date_attr,
                "origine_date_attribution": "/MAPA/attribution/autresInformations/dateAttribution",
                "identifiant_lot_verifie": None,
                "confirmation_independante": False,
            }],
            "erreur_extracteur": None,
        }

    raise AutreFormatInvalide("Format d'attribution non pris en charge.")
