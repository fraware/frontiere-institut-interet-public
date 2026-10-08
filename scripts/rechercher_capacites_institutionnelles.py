"""Recherche documentaire locale dans le référentiel institutionnel FRONTIÈRE.

Indexation explicite des missions et capacités publiées. Une correspondance
lexicale n'établit ni compétence effective ni disponibilité. Aucun réseau.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import unicodedata
from typing import Any

VERSION_INDEX = "recherche-missions-institutionnelles-v2"
RACINE = Path(__file__).resolve().parents[1]
DEFAULT_ENTITES = RACINE / "institutionnel" / "entites"
DEFAULT_INDEX = RACINE / "data" / "recherche_institutionnelle.sqlite3"
MOTS_GENERIQUES = {
    "a", "au", "aux", "avec", "ce", "ces", "cette", "de", "des", "du",
    "dans", "en", "et", "est", "la", "le", "les", "leur", "leurs", "l",
    "d", "ou", "par", "pour", "sur", "une", "un", "des", "que", "qui",
    "service", "services", "public", "publique", "publiques", "publics",
    "organisme", "organismes", "institution", "institutions", "capacite",
    "capacites", "competence", "competences", "besoin", "besoins",
    "recherche", "rechercher", "trouver", "mobiliser", "ressource", "ressources",
}


def normaliser(texte: str) -> list[str]:
    if not isinstance(texte, str):
        raise ValueError("Le texte de recherche doit être une chaîne.")
    texte = texte.casefold().replace("œ", "oe").replace("æ", "ae")
    sans_accents = "".join(
        c for c in unicodedata.normalize("NFKD", texte)
        if not unicodedata.combining(c)
    )
    return re.findall(r"[a-z0-9]+", sans_accents)


def termes_recherche(texte: str) -> list[str]:
    if not 2 <= len(texte.strip()) <= 300:
        raise ValueError("La requête doit compter de 2 à 300 caractères.")
    mots = list(dict.fromkeys(
        token for token in normaliser(texte) if token not in MOTS_GENERIQUES
    ))
    if not mots:
        raise ValueError("La requête doit contenir un terme distinctif.")
    if len(mots) > 10:
        raise ValueError("Dix termes distinctifs au maximum sont acceptés.")
    return mots


def faits_publies(entite: dict[str, Any], cle: str) -> list[dict[str, str]]:
    """Ne jamais déduire une compétence de champs analytiques ou sans source."""
    valeurs = entite.get(cle) or []
    if not isinstance(valeurs, list):
        raise ValueError(f"{cle} doit être une liste.")
    resultat = []
    for item in valeurs:
        if not isinstance(item, dict):
            continue
        if item.get("nature") != "PUBLIEE":
            continue
        source = item.get("source_id")
        texte = next(
            (item[k].strip() for k in ("texte", "description", "libelle", "intitule")
             if isinstance(item.get(k), str) and item[k].strip()),
            None,
        )
        if texte and isinstance(source, str) and source.strip():
            resultat.append({"texte": texte, "source_id": source})
    return resultat


def preparer_entite(entite: dict[str, Any], fichier: str) -> dict[str, Any]:
    identifiant = entite.get("id")
    nom = entite.get("nom_officiel")
    if not isinstance(identifiant, str) or not identifiant.startswith("FRONTIERE-INST-"):
        raise ValueError(f"{fichier} : identifiant institutionnel invalide.")
    if not isinstance(nom, str) or not nom.strip():
        raise ValueError(f"{fichier} : nom officiel absent.")
    provenance = entite.get("provenance")
    if not isinstance(provenance, list) or not provenance:
        raise ValueError(f"{fichier}/{identifiant} : provenance absente.")
    sources = []
    for p in provenance:
        if not isinstance(p, dict) or not isinstance(p.get("source_id"), str):
            continue
        sources.append({
            "source_id": p["source_id"],
            "identifiant_source": p.get("identifiant_source"),
            "url": p.get("url"),
            "collecte_le": p.get("collecte_le"),
            "empreinte": p.get("empreinte"),
        })
    if not sources:
        raise ValueError(f"{fichier}/{identifiant} : aucune provenance exploitable.")
    alias_bruts = entite.get("aliases") or []
    aliases = [x for x in alias_bruts if isinstance(x, str)] if isinstance(alias_bruts, list) else []
    missions = faits_publies(entite, "missions")
    capacites = faits_publies(entite, "capacites")
    domaines = faits_publies(entite, "domaines_recherche")
    return {
        "identifiant": identifiant,
        "nom": nom.strip(),
        "etat": entite.get("etat") if isinstance(entite.get("etat"), str) else "INCONNU",
        "famille": entite.get("famille") if isinstance(entite.get("famille"), str) else "",
        "type_institutionnel": entite.get("type_institutionnel") or "",
        "observe_le": entite.get("observe_le") or "",
        "fichier": fichier,
        "missions": missions,
        "capacites": capacites,
        "domaines": domaines,
        "sources": sources,
        "nom_index": " ".join(normaliser(" ".join([nom] + aliases))),
        "mission_index": " ".join(normaliser(" ".join(x["texte"] for x in missions))),
        "capacite_index": " ".join(normaliser(" ".join(x["texte"] for x in capacites))),
        "domaine_index": " ".join(normaliser(" ".join(x["texte"] for x in domaines))),
    }


def fichiers_sources(repertoire: Path) -> list[Path]:
    if not repertoire.is_dir():
        raise ValueError(f"Répertoire institutionnel absent : {repertoire}")
    racine = repertoire.resolve()
    fichiers = sorted(repertoire.rglob("*.jsonl"))
    if not fichiers:
        raise ValueError("Aucun fichier institutionnel JSONL trouvé.")
    for fichier in fichiers:
        if not fichier.resolve().is_relative_to(racine):
            raise ValueError("Fichier source externe au répertoire institutionnel.")
    return fichiers


def initialiser_tables(db: sqlite3.Connection) -> None:
    db.executescript("""
        CREATE TABLE informations (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
        CREATE TABLE fichiers (
            nom TEXT PRIMARY KEY, sha256 TEXT NOT NULL, octets INTEGER NOT NULL,
            lignes INTEGER NOT NULL
        );
        CREATE TABLE organismes (
            numero INTEGER PRIMARY KEY,
            identifiant TEXT NOT NULL UNIQUE,
            nom TEXT NOT NULL,
            etat TEXT NOT NULL,
            famille TEXT NOT NULL,
            type_institutionnel TEXT NOT NULL,
            observe_le TEXT NOT NULL,
            fichier TEXT NOT NULL,
            missions_json TEXT NOT NULL,
            capacites_json TEXT NOT NULL,
            domaines_json TEXT NOT NULL,
            sources_json TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE termes USING fts5(
            nom_index, mission_index, capacite_index, domaine_index,
            tokenize = 'unicode61 remove_diacritics 2'
        );
    """)


def construire_index(repertoire: Path, index: Path) -> dict:
    fichiers = fichiers_sources(repertoire)
    index.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=".frontiere-index-", suffix=".sqlite3",
        dir=index.parent, delete=False,
    ) as fichier_temp:
        temporaire = Path(fichier_temp.name)
    db: sqlite3.Connection | None = None
    try:
        db = sqlite3.connect(temporaire)
        initialiser_tables(db)
        manifest = []
        nombre_entites = 0
        nombre_missions = 0
        nombre_capacites = 0
        nombre_domaines = 0
        for fichier in fichiers:
            nom_rel = fichier.relative_to(repertoire).as_posix()
            hachage = hashlib.sha256()
            total_lignes = 0
            total_octets = 0
            with fichier.open("rb") as source:
                for numero_ligne, ligne in enumerate(source, 1):
                    hachage.update(ligne)
                    total_octets += len(ligne)
                    if not ligne.strip():
                        continue
                    total_lignes += 1
                    try:
                        original = json.loads(ligne)
                        if not isinstance(original, dict):
                            raise ValueError("L'entrée n'est pas un objet.")
                        item = preparer_entite(original, f"{nom_rel}:{numero_ligne}")
                    except (ValueError, UnicodeDecodeError, TypeError) as exc:
                        raise ValueError(f"Source non indexable {nom_rel}:{numero_ligne} : {exc}") from exc
                    try:
                        curseur = db.execute(
                            """INSERT INTO organismes (
                                identifiant, nom, etat, famille, type_institutionnel,
                                observe_le, fichier, missions_json, capacites_json,
                                domaines_json, sources_json
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                item["identifiant"], item["nom"], item["etat"], item["famille"],
                                item["type_institutionnel"], item["observe_le"], item["fichier"],
                                json.dumps(item["missions"], ensure_ascii=False),
                                json.dumps(item["capacites"], ensure_ascii=False),
                                json.dumps(item["domaines"], ensure_ascii=False),
                                json.dumps(item["sources"], ensure_ascii=False),
                            ),
                        )
                    except sqlite3.IntegrityError as exc:
                        raise ValueError(
                            f"Identifiant institutionnel dupliqué : {item['identifiant']}."
                        ) from exc
                    db.execute(
                        "INSERT INTO termes(rowid, nom_index, mission_index, capacite_index, domaine_index)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (
                            curseur.lastrowid, item["nom_index"], item["mission_index"],
                            item["capacite_index"], item["domaine_index"],
                        ),
                    )
                    nombre_entites += 1
                    nombre_missions += len(item["missions"])
                    nombre_capacites += len(item["capacites"])
                    nombre_domaines += len(item["domaines"])
            digest = hachage.hexdigest()
            manifest.append([nom_rel, digest, total_octets, total_lignes])
            db.execute(
                "INSERT INTO fichiers(nom, sha256, octets, lignes) VALUES (?, ?, ?, ?)",
                (nom_rel, digest, total_octets, total_lignes),
            )
        identite = hashlib.sha256(
            json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        for cle, valeur in {
            "version": VERSION_INDEX,
            "empreinte_sources": identite,
            "nombre_entites": str(nombre_entites),
            "nombre_missions": str(nombre_missions),
            "nombre_capacites": str(nombre_capacites),
            "nombre_domaines": str(nombre_domaines),
        }.items():
            db.execute("INSERT INTO informations(cle, valeur) VALUES (?, ?)", (cle, valeur))
        db.commit()
        db.close()
        db = None
        os.replace(temporaire, index)
    finally:
        if db is not None:
            db.close()
        temporaire.unlink(missing_ok=True)
    return {
        "version_schema": VERSION_INDEX,
        "nombre_fichiers": len(fichiers),
        "nombre_entites": nombre_entites,
        "nombre_missions_publiees": nombre_missions,
        "nombre_capacites_explicitement_publiees": nombre_capacites,
        "nombre_domaines_scientifiques_publies": nombre_domaines,
        "empreinte_sha256_sources": identite,
        "avertissement": (
            "L'index couvre des notices et leurs missions publiées, "
            "sans prouver l'existence ni la mobilisation effective des capacités."
        ),
    }


def ouvrir_index(index: Path) -> sqlite3.Connection:
    if not index.is_file():
        raise ValueError("Index absent : exécuter d'abord --construire.")
    db = sqlite3.connect(f"file:{index.resolve()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        info = db.execute(
            "SELECT valeur FROM informations WHERE cle = 'version'"
        ).fetchone()
        if info is None or info["valeur"] != VERSION_INDEX:
            raise ValueError("Version d'index non compatible : reconstruire.")
    except (sqlite3.Error, ValueError):
        db.close()
        raise
    return db


def verifier_sources(db: sqlite3.Connection, repertoire: Path) -> dict:
    attendu = {
        ligne["nom"]: (ligne["sha256"], ligne["octets"])
        for ligne in db.execute("SELECT nom, sha256, octets FROM fichiers")
    }
    fichiers = fichiers_sources(repertoire)
    presents = {p.relative_to(repertoire).as_posix(): p for p in fichiers}
    manquants = sorted(set(attendu) - set(presents))
    ajoutes = sorted(set(presents) - set(attendu))
    modifies = []
    for nom in sorted(set(presents) & set(attendu)):
        source = presents[nom]
        h = hashlib.sha256()
        with source.open("rb") as f:
            for bloc in iter(lambda: f.read(1024 * 1024), b""):
                h.update(bloc)
        if (h.hexdigest(), source.stat().st_size) != attendu[nom]:
            modifies.append(nom)
    return {
        "conforme": not (manquants or ajoutes or modifies),
        "fichiers_controles": len(presents),
        "fichiers_manquants": manquants,
        "fichiers_ajoutes": ajoutes,
        "fichiers_modifies": modifies,
    }


def correspondances(texte: str, termes: list[str]) -> list[str]:
    presentes = set(normaliser(texte))
    return [mot for mot in termes if mot in presentes]


def chercher(
    db: sqlite3.Connection,
    requete: str,
    *,
    limite: int = 10,
    famille: str | None = None,
) -> dict:
    mots = termes_recherche(requete)
    if type(limite) is not int or not 1 <= limite <= 25:
        raise ValueError("La limite doit être comprise entre 1 et 25.")
    if famille is not None and not re.fullmatch(r"[a-z0-9_]{1,100}", famille):
        raise ValueError("Famille institutionnelle incorrecte.")
    expression = " OR ".join(f'"{mot}"' for mot in mots)
    filtre = "AND o.famille = ?" if famille is not None else ""
    sql = (
        "SELECT o.*, t.nom_index, t.mission_index, t.capacite_index, t.domaine_index, "
        "bm25(termes, 1.0, 6.0, 8.0, 4.0) AS pertinence_lexicale "
        "FROM termes AS t JOIN organismes AS o ON o.numero = t.rowid "
        f"WHERE termes MATCH ? AND o.etat = 'ACTIF' {filtre} "
        "ORDER BY pertinence_lexicale, o.identifiant LIMIT 1000"
    )
    params = [expression] + ([famille] if famille is not None else [])
    lignes = db.execute(sql, params).fetchall()
    documentees = []
    disciplinaires = []
    nominatives = []
    for item in lignes:
        concordance_capacite = correspondances(item["capacite_index"], mots)
        concordance_mission = correspondances(item["mission_index"], mots)
        concordance_domaine = correspondances(item["domaine_index"], mots)
        concordance_nom = correspondances(item["nom_index"], mots)
        selection = (
            "capacite_publiee" if concordance_capacite
            else "mission_publiee" if concordance_mission
            else "domaine_scientifique_publie" if concordance_domaine
            else "nom_seul"
        )
        # Aucune équivalence sémantique inférée au-delà des mots réellement cités.
        preuves = json.loads(
            item["capacites_json"] if concordance_capacite else
            item["missions_json"] if concordance_mission else
            item["domaines_json"] if concordance_domaine else "[]"
        )
        candidats_passages = [
            p for p in preuves if set(normaliser(p["texte"])) & set(mots)
        ][:2]
        sources = json.loads(item["sources_json"])
        sortie = {
            "identifiant": item["identifiant"],
            "nom": item["nom"],
            "famille": item["famille"],
            "type_institutionnel": item["type_institutionnel"],
            "observe_le": item["observe_le"],
            "fichier_indexe": item["fichier"],
            "type_correspondance": selection,
            "mots_retrouves_dans_les_missions": concordance_mission,
            "mots_retrouves_dans_les_capacites": concordance_capacite,
            "mots_retrouves_dans_les_domaines_scientifiques": concordance_domaine,
            "mots_retrouves_dans_le_nom": concordance_nom,
            "passages_publies": candidats_passages,
            "provenance_notice": sources,
            "disponibilite": "INCONNUE",
            "mobilisabilite": "NON_ETABLIE",
        }
        couverture = len(set(concordance_mission + concordance_capacite + concordance_domaine))
        rang = (-couverture, float(item["pertinence_lexicale"]), item["identifiant"])
        if concordance_mission or concordance_capacite:
            documentees.append((rang, sortie))
        elif concordance_domaine:
            disciplinaires.append((rang, sortie))
        else:
            nominatives.append((rang, sortie))
    documentees.sort(key=lambda x: x[0])
    disciplinaires.sort(key=lambda x: x[0])
    nominatives.sort(key=lambda x: x[0])
    info = {
        ligne["cle"]: ligne["valeur"] for ligne in db.execute("SELECT cle, valeur FROM informations")
    }
    return {
        "version_schema": "orientation-documentaire-v2",
        "requete": requete,
        "termes_distinctifs": mots,
        "empreinte_sha256_sources_indexees": info["empreinte_sources"],
        "organismes_dans_index": int(info["nombre_entites"]),
        "candidats_lexicaux_examines": len(lignes),
        "correspondances_aux_missions_ou_capacites_publiees": [x[1] for x in documentees[:limite]],
        "correspondances_aux_domaines_scientifiques_publies": [x[1] for x in disciplinaires[:limite]],
        "correspondances_de_nom_uniquement": [x[1] for x in nominatives[:limite]],
        "recherche_bornee_aux_1000_premiers_candidats": len(lignes) == 1000,
        "limites": [
            "Le classement est lexical : il ne mesure pas la pertinence opérationnelle.",
            "Une mission officielle n'établit pas une compétence spécialisée disponible.",
            "Un domaine scientifique recense un rattachement disciplinaire sans attester de moyens mobilisables.",
            "Une concordance de nom est une piste d'identification, pas une preuve de capacité.",
            "Les organismes non actifs dans la notice sont exclus ; un état ACTIF historique ne prouve pas une activité actuelle.",
            "Les liens renvoient à la provenance des notices, pas nécessairement au passage original précis.",
            "L'absence de résultat ne prouve pas l'absence de capacité dans le secteur public.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rechercher des missions publiques dans le référentiel local.")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--construire", action="store_true", help="Construire l'index à partir des notices locales.")
    modes.add_argument("--verifier-index", action="store_true", help="Comparer l'index avec les fichiers sources.")
    modes.add_argument("--requete", help="Rechercher des mots dans les missions et les noms officiels.")
    parser.add_argument("--entites", type=Path, default=DEFAULT_ENTITES)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--limite", type=int, default=10)
    parser.add_argument("--famille", help="Limiter à une famille institutionnelle exacte.")
    args = parser.parse_args()

    try:
        if args.construire:
            resultat = construire_index(args.entites, args.index)
        else:
            with closing(ouvrir_index(args.index)) as db:
                controle = verifier_sources(db, args.entites)
                if not controle["conforme"]:
                    raise ValueError(
                        "Index périmé : sources ajoutées, modifiées ou retirées ; "
                        "reconstruire avant d'interroger."
                    )
                resultat = (
                    {"version_schema": VERSION_INDEX, "verification_sources": controle}
                    if args.verifier_index
                    else chercher(db, args.requete, limite=args.limite, famille=args.famille)
                )
                resultat["verification_sources"] = controle
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"Échec de la recherche institutionnelle : {exc}\n")
    print(json.dumps(resultat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
