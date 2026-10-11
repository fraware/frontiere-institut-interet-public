"""Rapprocher des identifiants BOAMP explicites d'archives BeauAMP vérifiées."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

try:
    from scripts.analyser_historique_boamp import BilanInvalide, produire
except ModuleNotFoundError:
    from analyser_historique_boamp import BilanInvalide, produire

VERSION = "appariement-documentaire-boamp-beauamp-v2"
VERSION_BEAUAMP = "beauamp-quotidiens-v1"
IDENTIFIANT = re.compile(r"[0-9]{2}-[0-9]{2,8}")
SHA = re.compile(r"[0-9a-f]{64}")
JOUR = re.compile(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}")
COLONNES = ("id_boamp_attribution", "id_boamp_contrat",
            "date_avis_attribution", "date_avis_marche", "objet", "id_lot")


def sha256(chemin):
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1_048_576), b""):
            h.update(bloc)
    return h.hexdigest()


def lire_identifiant(valeur):
    texte = str(valeur or "").strip()
    return texte if IDENTIFIANT.fullmatch(texte) else None


def fichiers_beauamp(racine):
    manifeste = json.loads((racine / "manifest.json").read_text(encoding="utf-8"))
    if (manifeste.get("version") != VERSION_BEAUAMP
            or manifeste.get("licence") != "cc-by-sa"
            or not isinstance(manifeste.get("fichiers"), list)
            or len(manifeste["fichiers"]) != manifeste.get("nombre_fichiers")):
        raise BilanInvalide("Manifeste BeauAMP incorrect.")
    uniques, resultat = set(), []
    for fiche in manifeste["fichiers"]:
        jour = fiche.get("jour")
        if not isinstance(jour, str) or not JOUR.fullmatch(jour):
            raise BilanInvalide("Date BeauAMP incorrecte.")
        if date.fromisoformat(jour).isoformat() != jour:
            raise BilanInvalide("Date BeauAMP non canonique.")
        chemin_relatif = f"quotidiens/{jour}.csv"
        if fiche.get("chemin") != chemin_relatif or jour in uniques:
            raise BilanInvalide("Fichier BeauAMP dupliqué ou déplacé.")
        uniques.add(jour)
        chemin = racine / chemin_relatif
        if not chemin.is_file() or chemin.is_symlink():
            raise BilanInvalide("Fichier BeauAMP manquant.")
        if (not 0 < chemin.stat().st_size <= 1_500_000
                or chemin.stat().st_size != fiche.get("octets_archives")
                or not isinstance(fiche.get("sha256"), str)
                or not SHA.fullmatch(fiche["sha256"])
                or sha256(chemin) != fiche["sha256"]):
            raise BilanInvalide("Empreinte BeauAMP ou taille incohérente.")
        resultat.append((jour, chemin, fiche))
    return sorted(resultat), manifeste


def rapprocher(index, preuve, racine_beauamp):
    bilan = produire(index, preuve)
    fichiers, manifeste = fichiers_beauamp(racine_beauamp)
    avis, ambigus = {}, set()
    with closing(sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)) as conn:
        for jour, identifiant, objet, source in conn.execute(
            "SELECT jour, identifiant, objet, archive_source FROM recherche"
        ):
            if identifiant in avis:
                ambigus.add(identifiant)
            avis[identifiant] = (jour, objet, source)
    for identifiant in ambigus:
        del avis[identifiant]
    if len(avis) + len(ambigus) > bilan["nombre_avis"]:
        raise BilanInvalide("Population BOAMP incohérente.")
    rencontres = Counter()
    uniques = {"id_boamp_attribution": set(), "id_boamp_contrat": set()}
    exemples_par_jour_et_type = defaultdict(list)
    ecarts_par_contrat = defaultdict(set)
    total_lignes, vides, malformes, ecarts_negatifs = 0, 0, 0, 0
    lignes_jour_secondaire_hors_fenetre = 0
    ecarts = []
    for jour_fichier, chemin, fiche in fichiers:
        with chemin.open("r", encoding="utf-8-sig", newline="") as handle:
            lecteur = csv.DictReader(handle, delimiter=";")
            if not lecteur.fieldnames or not set(COLONNES) <= set(lecteur.fieldnames):
                raise BilanInvalide("Colonnes BeauAMP obligatoires absentes.")
            for ligne in lecteur:
                total_lignes += 1
                lignes_jour_secondaire_hors_fenetre += not (
                    bilan["couverture"]["premier_jour"] <= jour_fichier
                    <= bilan["couverture"]["dernier_jour"]
                )
                ids = [
                    (champ, lire_identifiant(ligne.get(champ)))
                    for champ in ("id_boamp_attribution", "id_boamp_contrat")
                ]
                if not any(ligne.get(champ) for champ, _ in ids):
                    vides += 1
                malformes += sum(bool(ligne.get(champ)) and valeur is None
                                 for champ, valeur in ids)
                for champ, identifiant in ids:
                    if identifiant is None or identifiant not in avis:
                        continue
                    rencontres[champ] += 1
                    uniques[champ].add(identifiant)
                    jour_boamp, objet_boamp, archive_boamp = avis[identifiant]
                    if len(exemples) < 60:
                        exemples.append({
                            "identifiant_boamp": identifiant,
                            "nature_lien_exact": champ,
                            "jour_parution_boamp": jour_boamp,
                            "archive_boamp": archive_boamp,
                            "objet_boamp": objet_boamp[:350],
                            "jour_fichier_beauamp": jour_fichier,
                            "archive_beauamp": fiche["chemin"],
                            "identifiant_attribution": ligne.get("id_boamp_attribution"),
                            "identifiant_contrat": ligne.get("id_boamp_contrat"),
                            "date_attribution_declaree": ligne.get("date_avis_attribution"),
                            "objet_beauamp": (ligne.get("objet") or "")[:350],
                            "statut": "rapprochement_documentaire_indicatif",
                            "validation_du_marche": False,
                        })
                    if champ == "id_boamp_contrat":
                        texte = (ligne.get("date_avis_attribution") or "").strip()
                        try:
                            jour_attribution = date.fromisoformat(texte)
                        except ValueError:
                            jour_attribution = None
                        if jour_attribution is not None:
                            delta = (jour_attribution - date.fromisoformat(jour_boamp)).days
                            if delta < 0:
                                ecarts_negatifs += 1
                            else:
                                ecarts.append(delta)
                                ecarts_par_contrat[identifiant].add(delta)
    ecarts.sort()
    union = uniques["id_boamp_attribution"] | uniques["id_boamp_contrat"]
    return {
        "version": VERSION,
        "revision_depot_source": bilan["revision_depot"],
        "sha256_index_boamp": bilan["sha256_index"],
        "avis_boamp_dans_index": bilan["nombre_avis"],
        "identifiants_boamp_ambigus_exclus": len(ambigus),
        "source_beauamp": manifeste.get("source"),
        "producteur_beauamp": manifeste.get("producteur"),
        "licence_beauamp": manifeste["licence"],
        "fichiers_beauamp_verifies": len(fichiers),
        "premier_fichier_beauamp": fichiers[0][0] if fichiers else None,
        "dernier_fichier_beauamp": fichiers[-1][0] if fichiers else None,
        "lignes_beauamp_examinees": total_lignes,
        "lignes_sans_identifiant_boamp": vides,
        "identifiants_non_canoniques": malformes,
        "liaisons_sur_lignes_par_type": dict(sorted(rencontres.items())),
        "identifiants_boamp_distincts_par_type": {
            champ: len(ensemble) for champ, ensemble in sorted(uniques.items())
        },
        "identifiants_boamp_distincts_apparies": len(union),
        "ecarts_publication_contrat_attribution_positifs_observes": len(ecarts),
        "ecarts_publication_negatifs_ecartes": ecarts_negatifs,
        "jours_ecart_publication_positifs": {
            "minimum": ecarts[0] if ecarts else None,
            "mediane": (ecarts[(len(ecarts)-1)//2] + ecarts[len(ecarts)//2]) / 2
            if ecarts else None,
            "maximum": ecarts[-1] if ecarts else None,
        },
        "exemples_premiers_dans_les_fichiers": exemples,
        "completude_des_attributions_etablie": False,
        "fichiers_secondaires_limites_a_leur_fenetre": True,
        "attribution_officielle_verifiee": False,
        "delai_de_mobilisation_scientifique_etabli": False,
        "interpretation": (
            "Joins documentaires par identifiants explicites uniquement. "
            "BeauAMP est une source enrichie indicative. Les lignes représentent "
            "potentiellement des lots ou répétitions et non des marchés uniques. "
            "Les écarts de dates concernent les publications mentionnées, non "
            "un délai entre besoin et mobilisation. Une absence de jonction "
            "ne prouve aucune absence d'attribution."
        ),
    }


def ecrire(resultat, cible):
    cible.parent.mkdir(parents=True, exist_ok=True)
    fd, fichier = tempfile.mkstemp(prefix=".appariement-", suffix=".json", dir=cible.parent)
    os.close(fd)
    temp = Path(fichier)
    try:
        temp.write_text(
            json.dumps(resultat, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temp, cible)
    finally:
        temp.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", required=True, type=Path)
    p.add_argument("--preuve-index", required=True, type=Path)
    p.add_argument("--beauamp", default="institutionnel/marches_attribues", type=Path)
    p.add_argument("--sortie", required=True, type=Path)
    a = p.parse_args()
    try:
        resultat = rapprocher(a.index, a.preuve_index, a.beauamp)
        ecrire(resultat, a.sortie)
        print(json.dumps({
            "version": VERSION,
            "fichiers": resultat["fichiers_beauamp_verifies"],
            "lignes": resultat["lignes_beauamp_examinees"],
            "identifiants_apparies": resultat["identifiants_boamp_distincts_apparies"],
            "sortie": str(a.sortie),
        }, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error, csv.Error) as e:
        p.exit(1, f"Appariement interrompu : {e}\n")


if __name__ == "__main__":
    main()
