"""Mesurer la diversité documentaire des rapprochements BOAMP et institutions.

Les fréquences sont descriptives pour une sélection non représentative.
Un même texte reproduit dans plusieurs notices n'est pas plusieurs preuves
indépendantes de compétence opérationnelle.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

VERSION = "audit-concentration-preuves-v1"
VERSION_CROISEMENT = "croisement-avis-capacites-v2"
SHA_RE = re.compile(r"[a-f0-9]{64}")
NIVEAUX = ("capacite_publiee", "mission_publiee",
           "domaine_scientifique_publie", "nom_seul")
PUBLIES = NIVEAUX[:3]


class AuditIncoherent(ValueError):
    """Le rapport présente une source, un effectif ou une preuve incohérente."""


def calculer(rapport: dict, bilan_institutions: dict, empreinte_rapport: str) -> dict:
    if (not isinstance(rapport, dict)
            or rapport.get("version") != VERSION_CROISEMENT
            or not isinstance(rapport.get("dossiers"), list)
            or not isinstance(rapport.get("pistes_par_theme"), dict)
            or not isinstance(empreinte_rapport, str)
            or not SHA_RE.fullmatch(empreinte_rapport)
            or not isinstance(bilan_institutions, dict)
            or bilan_institutions.get("empreinte_sha256_sources")
            != rapport.get("empreinte_sha256_referentiel")
            or bilan_institutions.get("nombre_entites")
            != rapport.get("nombre_organismes_dans_index")):
        raise AuditIncoherent("Provenance ou structure des rapprochements incohérente.")
    groupes_theme = defaultdict(list)
    for fiche in rapport["dossiers"]:
        if not isinstance(fiche, dict) or fiche.get("theme") not in rapport["pistes_par_theme"]:
            raise AuditIncoherent("Dossier rattaché à un thème inconnu.")
        if (fiche.get("besoin_scientifique_valide") is not False
                or fiche.get("disponibilite_etablie") is not False
                or fiche.get("qualification_humaine_effectuee") is not False):
            raise AuditIncoherent("Un rapprochement est présenté comme validé.")
        groupes_theme[fiche["theme"]].append(fiche)
    total_annonces = sum(rapport["pistes_par_theme"].values())
    if total_annonces != len(rapport["dossiers"]) or total_annonces != rapport.get("nombre_pistes"):
        raise AuditIncoherent("Nombre de pistes différent de la source.")
    analyses = {}
    for theme in sorted(rapport["pistes_par_theme"]):
        fiches = groupes_theme[theme]
        if len(fiches) != rapport["pistes_par_theme"][theme]:
            raise AuditIncoherent("Nombre de pistes par thème incohérent.")
        institutions = set()
        occurrences = Counter()
        sources_courtes = {}
        passages_par_avis = defaultdict(set)
        nombres_liaisons = Counter()
        apparitions_organismes = Counter()
        pistes_tronquees = 0
        avec_document = 0
        avec_nom = 0
        pour_acheteur = set()
        for fiche in fiches:
            groupes = fiche.get("groupes")
            if not isinstance(groupes, dict) or set(groupes) != set(NIVEAUX):
                raise AuditIncoherent("Classes documentaires manquantes.")
            cle_avis = (fiche.get("date_parution"), fiche.get("identifiant_avis"))
            pour_acheteur.add(fiche.get("acheteur_declare"))
            a_publie = False
            a_nom = False
            pistes_tronquees += bool(fiche.get("recherche_tronquee")) or any(
                bool(v) for v in fiche.get("groupes_tronques", {}).values()
            )
            for niveau in NIVEAUX:
                candidats = groupes[niveau]
                if not isinstance(candidats, list):
                    raise AuditIncoherent("Candidats de correspondance incorrects.")
                for candidat in candidats:
                    numero = candidat.get("identifiant")
                    if not isinstance(numero, str) or not numero:
                        raise AuditIncoherent("Identité de candidat manquante.")
                    if (candidat.get("mobilisabilite") != "NON_ETABLIE"
                            or candidat.get("disponibilite") != "INCONNUE"
                            or candidat.get("niveau_documentaire") != niveau):
                        raise AuditIncoherent("État ou classe de candidat incohérent.")
                    institutions.add(numero)
                    apparitions_organismes[numero] += 1
                    nombres_liaisons[niveau] += 1
                    if niveau == "nom_seul":
                        a_nom = True
                    else:
                        a_publie = True
                    passages = candidat.get("passages_justificatifs")
                    if not isinstance(passages, list) or not passages:
                        raise AuditIncoherent("Correspondance sans justificatif.")
                    for passage in passages:
                        niveau_passage = passage.get("niveau")
                        if niveau_passage not in NIVEAUX:
                            raise AuditIncoherent("Niveau du passage inconnu.")
                        if niveau_passage in PUBLIES:
                            code = passage.get("sha256_passage_complet")
                            if (not isinstance(code, str) or not SHA_RE.fullmatch(code)
                                    or not passage.get("source_id")):
                                raise AuditIncoherent("Empreinte du passage publié manquante.")
                            occurrences[code] += 1
                            passages_par_avis[cle_avis].add(code)
                            sources_courtes.setdefault(code, {
                                "sha256_passage_complet": code,
                                "source_id": passage["source_id"],
                                "extrait": passage["texte_publie"][:200],
                            })
        nombre_passages = sum(occurrences.values())
        concentrations = occurrences.most_common()
        analyses[theme] = {
            "pistes": len(fiches),
            "acheteurs_declares_distincts_non_resolus": len(pour_acheteur),
            "pistes_avec_passage_publie": sum(
                bool(passages_par_avis[(x["date_parution"], x["identifiant_avis"])])
                for x in fiches
            ),
            "pistes_avec_nom_uniquement_ou_en_complement": sum(
                bool(x["groupes"]["nom_seul"]) for x in fiches
            ),
            "pistes_recherche_ou_restitution_tronquee": pistes_tronquees,
            "liaisons_affichees_par_niveau": dict(sorted(nombres_liaisons.items())),
            "organismes_distincts_par_identifiant": len(institutions),
            "total_occurrences_passages_publies": nombre_passages,
            "passages_publies_distincts_par_empreinte": len(occurrences),
            "part_passage_le_plus_repris": (
                round(concentrations[0][1] / nombre_passages, 4)
                if nombre_passages else None
            ),
            "passage_le_plus_repris": (
                {**sources_courtes[concentrations[0][0]],
                 "nombre_occurrences": concentrations[0][1]}
                if concentrations else None
            ),
            "identifiants_organismes_les_plus_repris": [
                {"identifiant": code, "nombre_apparitions": n}
                for code, n in apparitions_organismes.most_common(3)
            ],
        }
    return {
        "version": VERSION,
        "empreinte_sha256_croisement": empreinte_rapport,
        "revision_depot_source": rapport["revision_depot_source"],
        "empreinte_sha256_referentiel": rapport["empreinte_sha256_referentiel"],
        "nombre_organismes_indexes": bilan_institutions["nombre_entites"],
        "nombre_capacites_explicitement_publiees_dans_index":
            bilan_institutions["nombre_capacites_explicitement_publiees"],
        "nombre_domaines_scientifiques_publies_dans_index":
            bilan_institutions["nombre_domaines_scientifiques_publies"],
        "nombre_pistes_selectionnees": len(rapport["dossiers"]),
        "par_theme": analyses,
        "interpretation": (
            "Comptage descriptif des preuves et des identifiants affichés, sans "
            "évaluation de leur pertinence, de leur indépendance institutionnelle "
            "ou de leur disponibilité. Une empreinte de passage est calculée sur "
            "le texte intégral et sa source, même si seul un extrait est publié. "
            "Les plafonds de sélection limitent l'interprétation. "
            "Aucune fréquence de manque de compétences n'est estimée."
        ),
        "resultat_experimental_independant": False,
    }


def presenter(rapport: dict) -> str:
    lignes = [
        "# Diversité des preuves documentaires — FRONTIÈRE",
        "",
        f"Révision source : \x60{rapport['revision_depot_source']}\x60",
        f"Pistes étudiées : **{rapport['nombre_pistes_selectionnees']}**.",
        "",
        "| Thème | Pistes | Avec passage publié | Passages distincts | "
        "Répétitions du premier passage | Recherches tronquées |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for theme, item in rapport["par_theme"].items():
        champion = item["passage_le_plus_repris"]
        lignes.append(
            f"| {theme.replace('_', ' ')} | {item['pistes']} | "
            f"{item['pistes_avec_passage_publie']} | "
            f"{item['passages_publies_distincts_par_empreinte']} | "
            f"{champion['nombre_occurrences'] if champion else '—'} / "
            f"{item['total_occurrences_passages_publies']} | "
            f"{item['pistes_recherche_ou_restitution_tronquee']} |"
        )
    lignes += [
        "",
        "**Lecture :** plusieurs liens vers des organismes peuvent reposer sur "
        "un même texte publié. Ils ne constituent pas des preuves indépendantes "
        "d'une compétence opérationnelle. Les résultats tronqués ne permettent "
        "pas de conclure à l'absence de ressources supplémentaires.",
        "",
        "Les avis, les correspondances et ce tableau ne représentent ni la "
        "population des besoins publics ni une évaluation indépendante de FRONTIÈRE.",
        "",
    ]
    return "\n".join(lignes)


def ecrire(chemin: Path, texte: str) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fd, nom = tempfile.mkstemp(prefix=".audit-preuves-", dir=chemin.parent)
    os.close(fd)
    temporaire = Path(nom)
    try:
        temporaire.write_text(texte, encoding="utf-8")
        os.replace(temporaire, chemin)
    finally:
        temporaire.unlink(missing_ok=True)


def principal() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--croisements", type=Path, required=True)
    parser.add_argument("--bilan-capacites", type=Path, required=True)
    parser.add_argument("--sortie-json", type=Path, required=True)
    parser.add_argument("--sortie-md", type=Path, required=True)
    a = parser.parse_args()
    try:
        source = a.croisements.read_bytes()
        croisement = json.loads(source)
        bilan = json.loads(a.bilan_capacites.read_text(encoding="utf-8"))
        rapport = calculer(croisement, bilan, hashlib.sha256(source).hexdigest())
        ecrire(a.sortie_json, json.dumps(
            rapport, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        ecrire(a.sortie_md, presenter(rapport))
        print(json.dumps({
            "version": VERSION,
            "pistes": rapport["nombre_pistes_selectionnees"],
            "par_theme": {
                k: {
                    "avec_passage": v["pistes_avec_passage_publie"],
                    "passages_distincts": v["passages_publies_distincts_par_empreinte"],
                    "total_occurrences": v["total_occurrences_passages_publies"],
                } for k, v in rapport["par_theme"].items()
            },
        }, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as erreur:
        parser.exit(1, f"Audit de concentration interrompu : {erreur}\n")


if __name__ == "__main__":
    principal()
