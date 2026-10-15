"""Journal persistant des exécutions de collecteurs FRONTIÈRE.

Les horodatages concernent les exécutions locales et sont distincts des
dates de publication et des captures documentaires. Les consultations sont
strictement en lecture seule et n'initialisent pas une base absente.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4

SCHEMA = """
CREATE TABLE IF NOT EXISTS passages_collectes (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    demarre_le TEXT NOT NULL,
    termine_le TEXT,
    etat TEXT NOT NULL CHECK (
        etat IN ('en_cours', 'reussite', 'echec', 'interrompu')
    ),
    code_retour INTEGER,
    erreur_type TEXT
);
CREATE INDEX IF NOT EXISTS ix_passages_source_date
ON passages_collectes(source, demarre_le DESC);
"""
SOURCES = (
    "amorcage_boamp", "amorcage_emplois", "amorcage_decp",
    "boamp", "emplois", "decp", "decp_consolides",
)


def instant() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class JournalCollectes:
    def __init__(self, fichier: Path):
        self.fichier = Path(fichier)
        self.fichier.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.fichier, timeout=30) as conn:
            conn.execute("PRAGMA busy_timeout=30000")
            conn.executescript(SCHEMA)

    def commencer(self, source: str) -> str:
        if source not in SOURCES:
            raise ValueError("Source de collecte inconnue.")
        identifiant = str(uuid4())
        with sqlite3.connect(self.fichier, timeout=30) as conn:
            conn.execute(
                "INSERT INTO passages_collectes "
                "(id,source,demarre_le,etat) VALUES (?,?,?,'en_cours')",
                (identifiant, source, instant()),
            )
        return identifiant

    def conclure(
        self, identifiant: str, code_retour: int | None, *,
        erreur_type: str | None = None,
    ) -> None:
        statut = (
            "echec" if erreur_type is not None or
            (code_retour is not None and code_retour != 0) else
            "interrompu" if code_retour is None else "reussite"
        )
        with sqlite3.connect(self.fichier, timeout=30) as conn:
            r = conn.execute(
                "UPDATE passages_collectes SET etat=?,termine_le=?,"
                "code_retour=?,erreur_type=? WHERE id=? AND etat='en_cours'",
                (statut, instant(), code_retour, erreur_type, identifiant),
            )
            if r.rowcount != 1:
                raise ValueError("Exécution inconnue ou déjà terminée.")


def derniere_activite(fichier: Path | None, *, limite: int = 10) -> dict:
    """Lire l'historique récent sans créer la base ou modifier son contenu."""
    if type(limite) is not int or not 1 <= limite <= 50:
        raise ValueError("Limite de consultation invalide.")
    if fichier is None or not fichier.is_file():
        return {"etat": "non_configure", "sources": {}, "derniers_passages": []}
    try:
        with sqlite3.connect(
            fichier.resolve().as_uri() + "?mode=ro", uri=True, timeout=10
        ) as conn:
            conn.row_factory = sqlite3.Row
            noms = {
                x[0] for x in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "passages_collectes" not in noms:
                return {
                    "etat": "schema_incompatible",
                    "sources": {}, "derniers_passages": [],
                }
            resume: dict[str, dict] = {}
            for source in SOURCES:
                dernier = conn.execute(
                    "SELECT demarre_le,termine_le,etat,code_retour,erreur_type "
                    "FROM passages_collectes WHERE source=? "
                    "ORDER BY demarre_le DESC,rowid DESC LIMIT 1",
                    (source,),
                ).fetchone()
                succes = conn.execute(
                    "SELECT MAX(termine_le) FROM passages_collectes "
                    "WHERE source=? AND etat='reussite'",
                    (source,),
                ).fetchone()[0]
                echecs = conn.execute(
                    "SELECT COUNT(*) FROM passages_collectes "
                    "WHERE source=? AND etat='echec'",
                    (source,),
                ).fetchone()[0]
                resume[source] = {
                    "dernier_passage": dict(dernier) if dernier else None,
                    "derniere_reussite_le": succes,
                    "nombre_echecs_observes": echecs,
                }
            lignes = conn.execute(
                "SELECT source,demarre_le,termine_le,etat,code_retour,"
                "erreur_type FROM passages_collectes "
                "ORDER BY demarre_le DESC,rowid DESC LIMIT ?",
                (limite,),
            )
            return {
                "etat": "accessible",
                "sources": resume,
                "derniers_passages": [dict(x) for x in lignes],
                "precision": (
                    "Ces passages attestent de l'exécution locale des commandes. "
                    "Un code retour nul ne prouve pas la complétude ni "
                    "l'actualisation de la source officielle."
                ),
            }
    except (OSError, sqlite3.Error):
        return {"etat": "lecture_impossible", "sources": {},
                "derniers_passages": []}
