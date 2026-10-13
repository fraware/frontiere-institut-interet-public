"""Actualiser le bilan DECP seulement si les relevés documentaires ont changé.

La base SQLite complète est générée temporairement puis supprimée. Le dépôt
ne reçoit que le rapport reproductible et ses empreintes de provenances.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

if __package__:
    from scripts.consolider_attributions_decp import AIFE, DGFIP, construire_index
else:
    from consolider_attributions_decp import AIFE, DGFIP, construire_index

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "institutionnel/decp/bilan_index_unifie.json"


def actualiser(aife: Path, dgfip: Path, sortie: Path) -> dict:
    """Construire réellement la base SQLite avant de comparer les deux relevés."""
    entree_aife = json.loads(aife.read_text(encoding="utf-8"))
    entree_dgfip = json.loads(dgfip.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="frontiere-index-decp-") as dossier:
        bilan = construire_index(
            Path(dossier) / "index.sqlite3",
            aife=entree_aife, dgfip=entree_dgfip,
        )
    if sortie.is_file():
        precedent = json.loads(sortie.read_text(encoding="utf-8"))
        # Recontrôler les relevés en reconstruisant l'index, même en cas
        # de contenu inchangé. Seule l'heure de génération diffère.
        comparable = lambda x: {
            k: v for k, v in x.items() if k != "construit_le"
        }
        if comparable(precedent) == comparable(bilan):
            return {"statut": "identique", "bilan": precedent}
    sortie.parent.mkdir(parents=True, exist_ok=True)
    temporaire = sortie.with_name(sortie.name + ".tmp")
    temporaire.write_text(json.dumps(bilan, ensure_ascii=False, indent=2,
                                    sort_keys=True, allow_nan=False) + "\n",
                          encoding="utf-8")
    temporaire.replace(sortie)
    return {"statut": "mis_a_jour", "bilan": bilan}


def main() -> None:
    """Calculer et publier uniquement les résultats d'une base réellement créée."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aife", type=Path, default=AIFE)
    parser.add_argument("--dgfip", type=Path, default=DGFIP)
    parser.add_argument("--sortie", type=Path, default=SORTIE)
    options = parser.parse_args()
    try:
        retour = actualiser(options.aife, options.dgfip, options.sortie)
        print(json.dumps({
            "statut": retour["statut"],
            "enregistrements": retour["bilan"]["enregistrements_normalises_par_fichier"],
            "identites": retour["bilan"]["identites_distinctes_par_siret_et_id_marche"],
            "variantes": retour["bilan"]["variantes_documentaires_distinctes"],
        }, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(1, f"Bilan DECP refusé : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
