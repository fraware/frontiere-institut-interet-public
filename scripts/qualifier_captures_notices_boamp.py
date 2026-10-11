"""Qualifier la nature documentaire des avis BOAMP capturés sans inférence causale."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

try:
    from scripts.collecter_notices_pilotes_boamp import verifier_capture
    from scripts.preparer_dossiers_pilotes_boamp import lire_cas
except ModuleNotFoundError:
    from collecter_notices_pilotes_boamp import verifier_capture
    from preparer_dossiers_pilotes_boamp import lire_cas


VERSION = "qualification-nature-notices-pilotes-v1"
ID_AVIS = re.compile(r"[0-9]{2}-[0-9]{2,8}")


class QualificationInvalide(ValueError):
    """La capture ne permet pas une qualification documentaire reproductible."""


def liste_textes(valeur, nom: str) -> list[str]:
    """Conserver seulement des chaînes déclarées, sans inventer de valeur."""
    if valeur is None:
        return []
    if not isinstance(valeur, list) or any(
        not isinstance(item, str) or not item.strip() for item in valeur
    ):
        raise QualificationInvalide(f"Champ source {nom} incompatible.")
    return valeur


def liens_avis(valeur) -> list[str]:
    liens = liste_textes(valeur, "annonce_lie")
    if len(set(liens)) != len(liens) or any(
        not ID_AVIS.fullmatch(code) for code in liens
    ):
        raise QualificationInvalide("Lien à un avis antérieur incorrect ou dupliqué.")
    return liens


def produire(captures: Path, registre: Path) -> dict:
    rapport = verifier_capture(captures)
    if not registre.is_file() or hashlib.sha256(registre.read_bytes()).hexdigest() != (
        rapport["sha256_registre"]
    ):
        raise QualificationInvalide("Le registre préenregistré diffère de la capture.")
    references = lire_cas(registre)
    attendus = {x["identifiant"]: x for x in references}
    identifies = {x["identifiant"]: x for x in rapport["cas"]}
    if len(references) != len(rapport["cas"]) or set(attendus) != set(identifies):
        raise QualificationInvalide("Inventaire des pilotes incohérent.")
    lignes = []
    categories = Counter()
    for reference in references:
        code = reference["identifiant"]
        fiche = identifies[code]
        categorie = "avis_absent_de_la_consultation"
        nature = etat = nom_acheteur = titulaire = None
        categories_marche = []
        liens = []
        date_limite = None
        if fiche["etat_observation"] == "notice_retrouvee_et_identifiee":
            raw = json.loads((captures / fiche["fichier_reponse"]).read_bytes())
            source = raw["results"][0]
            nature = source.get("nature")
            etat = source.get("etat")
            if not isinstance(nature, str) or not isinstance(etat, str):
                raise QualificationInvalide("Nature ou état officiel absent.")
            if etat != fiche["etat_documentaire_reobserve"]:
                raise QualificationInvalide("État documentaire contradictoire.")
            if source.get("dateparution") != fiche["date_parution_reobservee"]:
                raise QualificationInvalide("Date de parution incohérente.")
            categories_marche = liste_textes(source.get("type_marche"), "type_marche")
            titulaires = liste_textes(source.get("titulaire"), "titulaire")
            titulaire = titulaires or None
            liens = liens_avis(source.get("annonce_lie"))
            nom_acheteur = source.get("nomacheteur")
            if nom_acheteur is not None and not isinstance(nom_acheteur, str):
                raise QualificationInvalide("Acheteur déclaré incorrect.")
            date_limite = source.get("datelimitereponse")
            if date_limite is not None and not isinstance(date_limite, str):
                raise QualificationInvalide("Date limite de réponse incorrecte.")
            if etat == "RECTIFICATIF":
                categorie = "rectificatif"
            elif nature == "ATTRIBUTION":
                categorie = "avis_attribution"
            elif nature == "APPEL_OFFRE" and etat == "INITIAL":
                categorie = "appel_offres_initial"
            else:
                categorie = "autre_nature_ou_etat"
        categories[categorie] += 1
        lignes.append({
            "identifiant": code,
            "theme_pre_enregistre": reference["theme"],
            "date_reference": reference["date_attendue"],
            "statut_capture": fiche["etat_observation"],
            "nature_officielle": nature,
            "etat_officiel": etat,
            "categorie_documentaire_analytique": categorie,
            "acheteur_declare": nom_acheteur,
            "categories_marche_declarees": categories_marche,
            "titulaires_declares_dans_avis": titulaire,
            "date_parution_officielle": fiche["date_parution_reobservee"],
            "date_limite_reponse_declaree": date_limite,
            "avis_anterieurs_explicitement_lies": liens,
            "contenu_des_avis_anterieurs_examine": False,
            "fichier_reponse": fiche["fichier_reponse"],
            "sha256_reponse_http": fiche["sha256_reponse_http"],
            "notice_officielle": fiche["source_officielle_interrogee"],
            "classification_deficit_competences": "indeterminee",
            "mobilisation_effective_etablie": False,
            "premiere_contribution_utile_etablie": False,
        })
    return {
        "version": VERSION,
        "version_capture": rapport["version"],
        "date_observation_capture": rapport["observe_le"],
        "sha256_registre": rapport["sha256_registre"],
        "nombre_cas": len(lignes),
        "repartition_documentaire": dict(sorted(categories.items())),
        "cas": lignes,
        "pieces_contractuelles_integrales_examinees": False,
        "conclusions_causales_autorisees": False,
        "interpretation": (
            "Les catégories décrivent la nature et l'état publiés des avis. "
            "Un avis d'attribution n'atteste pas le début de l'exécution "
            "ni sa première contribution utile. Un rectificatif n'établit "
            "pas le contenu de son avis antérieur. Les ressources, l'origine "
            "du besoin et le délai de mobilisation demeurent indéterminés."
        ),
    }


def ecrire(rapport: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".qualification-boamp-", suffix=".json",
                                dir=destination.parent)
    os.close(fd)
    try:
        Path(temp).write_text(
            json.dumps(rapport, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temp, destination)
    finally:
        Path(temp).unlink(missing_ok=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--captures", type=Path, required=True)
    p.add_argument("--registre", type=Path,
                   default=Path("evaluation/cas_pilotes_boamp_v1.json"))
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        bilan = produire(a.captures, a.registre)
        ecrire(bilan, a.sortie)
        print(json.dumps({
            "cas": bilan["nombre_cas"],
            "repartition": bilan["repartition_documentaire"],
        }, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as erreur:
        p.exit(1, f"Qualification documentaire impossible : {erreur}\n")


if __name__ == "__main__":
    main()
