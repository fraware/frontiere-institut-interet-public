"""Préparer deux relectures aveugles des preuves et ressources nommées.

Les références historiques ne sont ni ouvertes ni nécessaires.
Les fichiers contenant les méthodes sont réservés au responsable d'étude.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import secrets

from geler_reponses_jeu_reserve import verifier_manifeste
from verifier_reponses_jeu_reserve import verifier_reponses

METHODES = {"analyste", "assistant_generaliste", "frontiere"}


def ecrire(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def empreinte(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preparer(
    questions: Path,
    reponses: list[Path],
    gels: list[Path],
    destination: Path,
    alea: random.Random | None = None,
) -> dict:
    depot = Path(__file__).resolve().parents[1]
    if destination.resolve().is_relative_to(depot):
        raise ValueError("Les dossiers de relecture doivent rester hors du dépôt public.")
    if len(reponses) != 3 or len(gels) != 3:
        raise ValueError("Trois couples réponses/gel sont obligatoires.")
    jeu = json.loads(questions.read_text(encoding="utf-8"))
    cas = jeu.get("cas")
    if not isinstance(cas, list) or not cas:
        raise ValueError("Questions manquantes.")
    codes = [c["code"] for c in cas]
    if len(codes) != len(set(codes)):
        raise ValueError("Codes de cas répétés.")
    noms: dict[str, dict] = {}
    empreintes = {}
    for chemin, gel_path in zip(reponses, gels):
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        gel = json.loads(gel_path.read_text(encoding="utf-8"))
        verifier_reponses(jeu, donnees)
        if not verifier_manifeste(questions, chemin, gel):
            raise ValueError(f"Réponses non conformes au gel : {chemin}")
        nom = donnees["methode"]
        if nom in noms:
            raise ValueError("Méthode répétée.")
        noms[nom] = {ligne["code"]: ligne for ligne in donnees["cas"]}
        empreintes[nom] = {
            "reponses": empreinte(chemin),
            "gel": empreinte(gel_path),
        }
    if set(noms) != METHODES:
        raise ValueError("Les méthodes attendues sont analyste, assistant_generaliste et frontiere.")
    alea = alea or secrets.SystemRandom()
    paquet = {"version_schema": "relecture-aveugle-v1", "cas": []}
    correspondances = []
    relectures = {"version_schema": "jugements-relecture-v1", "empreinte_sha256_paquet": None,
                  "relecteur_code": "a-renseigner", "cas": []}

    for q in cas:
        code = q["code"]
        ordre = list(METHODES)
        alea.shuffle(ordre)
        propositions = []
        anonymisation = []
        jugements = []
        for position, methode in enumerate(ordre):
            identifiant = f"{code}-{chr(65 + position)}"
            reponse = noms[methode][code]
            ressources = [
                {"id": f"R{i:02d}", "nom": nom} for i, nom in enumerate(reponse["ressources"], 1)
            ]
            sources = [
                {"id": f"S{i:02d}", "url": url} for i, url in enumerate(reponse["urls_preuves"], 1)
            ]
            propositions.append({
                "id": identifiant,
                "voies": reponse["voies"],
                "formes_ressource": reponse["formes_ressource"],
                "ressources": ressources,
                "sources": sources,
            })
            anonymisation.append({"id": identifiant, "methode": methode})
            jugements.append({
                "id": identifiant,
                "ressources": [{
                    "id": item["id"], "existence": "A_VERIFIER", "pertinence": "A_VERIFIER",
                    "mobilisabilite": "A_VERIFIER", "motif": "",
                } for item in ressources],
                "sources": [{
                    "id": item["id"], "fiabilite": "A_VERIFIER",
                    "appui": "A_VERIFIER", "motif": "",
                } for item in sources],
                "note": "",
            })
        paquet["cas"].append({
            "code": code,
            "question": q["question"],
            "propositions": propositions,
        })
        correspondances.append({"code": code, "propositions": anonymisation})
        relectures["cas"].append({"code": code, "propositions": jugements})

    destination.mkdir(parents=True, exist_ok=False)
    ecrire(destination / "paquet_aveugle.json", paquet)
    paquet_sha256 = empreinte(destination / "paquet_aveugle.json")
    relectures["empreinte_sha256_paquet"] = paquet_sha256
    for i in (1, 2):
        ecrire(destination / f"jugements_relecteur_{i}_vierges.json", relectures)
    prive = {
        "version_schema": "correspondances-relecture-v1",
        "empreinte_sha256_paquet": paquet_sha256,
        "empreinte_sha256_questions": empreinte(questions),
        "reponses_gels": empreintes,
        "correspondances": correspondances,
        "references_historiques_consultees": False,
        "jugements_recueillis": False,
        "avertissement": "Correspondances confidentielles : ne pas transmettre aux relecteurs.",
    }
    ecrire(destination / "correspondances_privees.json", prive)
    (destination / "CONSIGNES_RELECTEURS.md").write_text(
        "# Relecture indépendante des propositions\n\n"
        "Recevoir uniquement paquet_aveugle.json et son formulaire vierge. "
        "Ne pas consulter correspondances_privees.json, le dépôt ou les références historiques.\n\n"
        "Pour chaque ressource, vérifier son existence, sa pertinence pour la mission "
        "et sa mobilisabilité pour la période ; pour chaque source, vérifier sa fiabilité "
        "et si elle soutient directement les propositions.\n\n"
        "Justifier chaque appréciation en indiquant l'élément contrôlé ; "
        "consigner les incertitudes. Les jugements sont individuels et indépendants.\n\n"
        "Valeurs autorisées :\n"
        "- existence et mobilisabilite : CONFIRMEE, NON_CONFIRMEE, INDETERMINEE ;\n"
        "- pertinence : FORTE, PARTIELLE, INSUFFISANTE, INDETERMINEE ;\n"
        "- fiabilite : PRIMAIRE, SECONDAIRE, INSUFFISANTE, INDETERMINEE ;\n"
        "- appui : DIRECT, PARTIEL, AUCUN, INDETERMINE.\n"
        "A_VERIFIER est uniquement une valeur provisoire, interdite au dépôt final.\n"
        "L'anonymisation des méthodes ne garantit pas que leur style soit méconnaissable.\n",
        encoding="utf-8",
    )
    return prive


def principal() -> None:
    analyseur = argparse.ArgumentParser(description="Préparer deux relectures sans révéler les méthodes.")
    analyseur.add_argument("--questions", type=Path, required=True)
    analyseur.add_argument("--reponses", type=Path, nargs=3, required=True)
    analyseur.add_argument("--gels", type=Path, nargs=3, required=True)
    analyseur.add_argument("--sortie", type=Path, required=True)
    args = analyseur.parse_args()
    try:
        resultat = preparer(args.questions, args.reponses, args.gels, args.sortie)
    except (ValueError, TypeError, KeyError, OSError) as erreur:
        raise SystemExit(f"Préparation impossible : {erreur}") from erreur
    print(f"Relecture préparée. Empreinte du paquet : {resultat['empreinte_sha256_paquet']}")
    print("Transmettre aux relecteurs le paquet et les formulaires, jamais les correspondances.")


if __name__ == "__main__":
    principal()
