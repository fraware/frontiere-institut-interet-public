"""Comparer les archives, l'index public borné et ses partitions, hors réseau.

Les moteurs SQLite intégraux possèdent leurs propres vérifications. Cet audit
ne les remplace pas et n'atteste pas le contenu du déploiement Render.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys

RACINE = Path(__file__).resolve().parents[1]
SOURCES = ("boamp", "emplois", "decp")
LOT = re.compile(r"part-(boamp|emplois|decp)-(\d{4})-\d{3}\.json")
REVISION = re.compile(r"[0-9a-f]{40}")


class EchecAudit(ValueError):
    """La chaîne documentaire est incohérente."""


def imposer(condition: bool, message: str) -> None:
    if not condition:
        raise EchecAudit(message)


def lire(racine: Path, nom: str, taille_max: int = 35_000_000) -> tuple[dict, bytes]:
    """Lire sans suivre de lien symbolique ou de chemin hors dépôt."""
    chemin = Path(nom)
    imposer(not chemin.is_absolute() and ".." not in chemin.parts,
            "Chemin extérieur interdit.")
    fichier = racine / chemin
    imposer(fichier.is_file() and not fichier.is_symlink()
            and 0 < fichier.stat().st_size <= taille_max,
            f"Fichier absent ou taille invalide : {nom}")
    brut = fichier.read_bytes()
    try:
        return json.loads(brut), brut
    except (ValueError, UnicodeError) as exc:
        raise EchecAudit(f"Fichier JSON illisible : {nom}") from exc


def entier(obj: dict, cle: str) -> int:
    valeur = obj.get(cle)
    imposer(type(valeur) is int and valeur >= 0, f"Décompte incorrect : {cle}")
    return valeur


def empreinte(brut: bytes) -> str:
    return hashlib.sha256(brut).hexdigest()


def identites(lignes: list, source: str) -> dict:
    index = {}
    for item in lignes:
        imposer(isinstance(item, dict) and item.get("source") == source,
                f"Source invalide : {source}")
        ident = item.get("id")
        date = item.get("date")
        imposer(isinstance(ident, str) and bool(ident.strip()) and
                isinstance(date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date),
                f"Identité ou date invalide : {source}")
        imposer(ident not in index, f"Document dupliqué : {source}/{ident}")
        index[ident] = item
    return index


def auditer(racine: Path, revision: str | None = None) -> dict:
    """Renvoyer les populations et vérifier les projections sans réseau."""
    imposer(revision is None or REVISION.fullmatch(revision) is not None,
            "Révision Git incorrecte.")
    boamp, _ = lire(racine, "institutionnel/besoins_publics/annonces_boamp.json")
    etat, _ = lire(racine, "institutionnel/besoins_publics/etat_boamp.json")
    csp, brut_csp = lire(racine, "institutionnel/besoins_publics/manifest_offres_postes.json")
    decp, _ = lire(racine, "institutionnel/decp/bilan_index_unifie.json")
    principal, _ = lire(racine, "site_frontiere/recherche-index.json", 2_000_000)
    catalogue, _ = lire(racine, "site_frontiere/partitions/manifeste.json")
    dates, _ = lire(racine, "site_frontiere/metadonnees-index.json")

    volumes = {
        "boamp": entier(etat, "annonces_distinctes_conservees"),
        "emplois": entier(csp, "offres_distinctes"),
        "decp": entier(decp, "attestations_documentaires"),
    }
    imposer(isinstance(boamp.get("annonces"), list) and
            len(boamp["annonces"]) == volumes["boamp"], "Archive BOAMP divergente.")
    imposer(entier(csp, "references_distinctes") <= volumes["emplois"]
            and len(csp.get("empreintes_partitions", {})) == 16,
            "Variantes ou partitions CSP incohérentes.")
    imposer(entier(decp, "identites_distinctes_par_siret_et_id_marche") <=
            entier(decp, "variantes_documentaires_distinctes") <= volumes["decp"],
            "Unités DECP incompatibles.")

    imposer(principal.get("portee") == "echantillon_documentaire_non_exhaustif"
            and principal.get("recherche_temps_reel") is False
            and catalogue.get("portee") == "extrait_etendu_non_exhaustif"
            and catalogue.get("mise_a_jour_temps_reel") is False,
            "Portée documentaire invalidement déclarée.")
    rev = principal.get("revision_sources")
    imposer(rev == catalogue.get("revision_sources") == dates.get("revision_sources"),
            "Versions divergentes des deux publications.")
    if revision is not None:
        imposer(rev == revision, "Sorties issues d'une autre révision Git.")

    stats = principal.get("sources")
    imposer(isinstance(stats, dict) and
            stats["emplois"].get("empreinte_manifeste") == empreinte(brut_csp),
            "Manifeste CSP différent de celui du site.")
    _, brut_boamp = lire(racine, "institutionnel/besoins_publics/annonces_boamp.json")
    imposer(stats["boamp"].get("empreinte_fichier") == empreinte(brut_boamp),
            "Archive BOAMP différente de celle du site.")
    fichiers_decp = stats["decp"].get("fichiers")
    imposer(isinstance(fichiers_decp, list) and len(fichiers_decp) == 2,
            "Attestations de sources DECP manquantes.")
    chemins = set()
    for fichier in fichiers_decp:
        chemin = fichier["chemin"]
        imposer(chemin not in chemins, "Fichier DECP dupliqué.")
        chemins.add(chemin)
        _, brut = lire(racine, chemin)
        imposer(fichier["sha256"] == empreinte(brut), "Empreinte DECP divergente.")
    imposer(chemins == {
        "institutionnel/decp/sonde_aife_json.json",
        "institutionnel/decp/lot_dgfip_xml.json",
    }, "Relevés DECP incomplets.")

    for source, cle in (("boamp", "notices_fichier"),
                        ("emplois", "variantes_fichier"),
                        ("decp", "notices_fichiers")):
        imposer(entier(stats[source], cle) == volumes[source],
                f"Population source incohérente : {source}")

    index = principal.get("documents")
    partitions = catalogue.get("partitions")
    selection = catalogue.get("selection")
    imposer(isinstance(index, list) and isinstance(partitions, list) and
            isinstance(selection, dict) and
            selection.get("couverture_nationale_etablie") is False,
            "Manifeste ou documents publics incohérents.")
    principal_par_source = {
        s: identites([x for x in index
                      if isinstance(x, dict) and x.get("source") == s], s)
        for s in SOURCES
    }
    imposer(len(index) == sum(len(x) for x in principal_par_source.values()),
            "Documents principaux de source inconnue.")

    etendus = {s: [] for s in SOURCES}
    noms = set()
    for partition in partitions:
        nom = partition.get("fichier")
        match = LOT.fullmatch(nom) if isinstance(nom, str) else None
        imposer(match is not None and nom not in noms,
                "Partition inconnue ou dupliquée.")
        noms.add(nom)
        source, annee = match.group(1), match.group(2)
        imposer(partition.get("source") == source and partition.get("annee") == annee,
                "Origine ou année de partition modifiée.")
        brut = (racine / "site_frontiere/partitions" / nom).read_bytes()
        imposer(len(brut) == entier(partition, "octets") and
                empreinte(brut) == partition.get("sha256"),
                "Contenu ou empreinte de partition incohérent.")
        lignes = json.loads(brut)
        imposer(isinstance(lignes, list) and len(lignes) == entier(partition, "documents"),
                "Nombre de documents d'une partition incorrect.")
        imposer(all(isinstance(x, dict) and isinstance(x.get("date"), str)
                    and x["date"].startswith(annee + "-") for x in lignes),
                "Document dans la mauvaise année.")
        etendus[source].extend(lignes)

    sorties = {}
    for source in SOURCES:
        uniques = identites(etendus[source], source)
        etat_source = [x for x in selection.get("sources", [])
                       if x.get("source") == source]
        imposer(len(etat_source) == 1, "Source absente de la sélection.")
        s = etat_source[0]
        plafond = entier(catalogue["limite_par_source"], source)
        imposer(entier(s, "documents_indexes") == len(uniques) and
                entier(s, "plafond") == plafond and
                entier(s, "enregistrements_sources_parcourus") == volumes[source] and
                len(principal_par_source[source]) == entier(stats[source], "retenus") and
                len(principal_par_source[source]) <= len(uniques) <= plafond and
                len(principal_par_source[source]) <= entier(principal["limites"], source),
                f"Incohérence de la sélection : {source}")
        for identifiant, doc in principal_par_source[source].items():
            correspondant = uniques.get(identifiant)
            imposer(correspondant is not None and
                    all(correspondant.get(k) == v for k, v in doc.items()),
                    f"Source, date ou document divergent : {source}/{identifiant}")
        sorties[source] = {
            "archives": volumes[source],
            "index_principal": len(principal_par_source[source]),
            "index_etendu": len(uniques),
            "plafond_principal": entier(principal["limites"], source),
            "plafond_etendu": plafond,
            "unite": {"boamp": "avis", "emplois": "variantes", "decp": "attestations"}[source],
        }

    return {
        "version": "frontiere-audit-chaine-v1",
        "revision": rev,
        "partitions_verifiees": len(noms),
        "sources": sorties,
        "couverture_nationale_demontree": False,
        "site_render_examine": False,
        "index_sqlite_reconstruit_par_ce_programme": False,
        "limite": "La projection statique ne représente pas un inventaire national complet.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--racine", type=Path, default=RACINE)
    parser.add_argument("--revision", default=os.getenv("GITHUB_SHA"))
    parser.add_argument("--rapport", required=True, type=Path)
    args = parser.parse_args()
    try:
        bilan = auditer(args.racine, args.revision)
        destination = args.rapport.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        provisoire = destination.with_name(destination.name + ".tmp")
        provisoire.write_text(json.dumps(bilan, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
        os.replace(provisoire, destination)
        print(json.dumps(bilan["sources"], ensure_ascii=False))
        return 0
    except (EchecAudit, OSError, KeyError, TypeError, ValueError) as exc:
        print("Contrôle de la chaîne refusé : " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
