from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def charger(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def principal() -> None:
    chemin = Path("donnees/signaux_publics_v1.json")
    contenu = charger(chemin)
    signaux = contenu["signaux"]

    par_niveau = Counter(s["niveau_documentaire"] for s in signaux)
    par_nature = Counter(s["nature"] for s in signaux)
    par_domaine = Counter(s["domaine"] for s in signaux)
    contre_exemples = [s for s in signaux if s["contre_exemple"]]
    solutions_connues = [s for s in signaux if s["solution_connue"]]
    chronologies = [s for s in signaux if s["chronologie_exploitable"]]
    priorite_haute = [s for s in signaux if s["priorite_examen"] == "haute"]

    print(f"Nombre total de signaux : {len(signaux)}")
    print(f"Cas solides : {par_niveau['cas_solide']}")
    print(f"Cas partiels : {par_niveau['cas_partiel']}")
    print(f"Signaux contextuels : {par_niveau['signal_contextuel']}")
    print(f"Solutions connues : {len(solutions_connues)}")
    print(f"Chronologies exploitables : {len(chronologies)}")
    print(f"Contre-exemples : {len(contre_exemples)}")
    print(f"Priorité haute : {len(priorite_haute)}")

    print("\nPrincipales natures de signal :")
    for nature, nombre in par_nature.most_common():
        print(f"- {nature} : {nombre}")

    print("\nPrincipaux domaines :")
    for domaine, nombre in par_domaine.most_common():
        print(f"- {domaine} : {nombre}")

    print("\nCas prioritaires avec chronologie exploitable :")
    for signal in signaux:
        if signal["priorite_examen"] == "haute" and signal["chronologie_exploitable"]:
            print(f"- {signal['id_signal']} — {signal['titre']}")


if __name__ == "__main__":
    principal()
