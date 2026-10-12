"""Créer un paquet documentaire aveugle pour deux lecteurs des 60 avis BOAMP.

Les preuves sont les notices originales. Aucune préqualification automatique
n'est transmise. Les formulaires vierges ne constituent aucune référence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

VERSION = "double-lecture-issues-boamp-v1"
CORPUS = (
    ("echantillon-independant-technique.json", "releve-issues-36/",
     "40f791c35adcdc67d69bb933e873b0efaa7b24dd0c74958474dc6272b94242c8", 36),
    ("epreuve-enrichie-infructueux.json", "releve-epreuve-enrichie/",
     "abdd53aa7e2c5f89dc42a74ea7e6f9afdcaf85a1ba86042bcac6f3dc86253689", 24),
)
SEMENCE = "frontiere-ordre-aveugle-boamp-2026-10-12"


class RelectureInvalide(ValueError):
    """Les données ou leur intégrité ne respectent pas le protocole."""


def sha(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def lire(z: zipfile.ZipFile, nom: str) -> dict:
    try:
        objet = json.loads(z.read(nom))
        if not isinstance(objet, dict):
            raise ValueError("JSON non structuré.")
        return objet
    except (KeyError, ValueError, UnicodeDecodeError) as exc:
        raise RelectureInvalide("Document officiel absent ou illisible : " + nom) from exc


def sources(archive: Path) -> list[dict]:
    if not zipfile.is_zipfile(archive):
        raise RelectureInvalide("Archive ZIP absente ou invalide.")
    cas, vus = [], set()
    with zipfile.ZipFile(archive) as z:
        noms = z.namelist()
        if len(noms) != len(set(noms)) or any(
                x.startswith("/") or ".." in Path(x).parts for x in noms):
            raise RelectureInvalide("Archive aux chemins dangereux ou dupliqués.")
        if z.testzip() is not None:
            raise RelectureInvalide("Archive ZIP corrompue.")
        for tirage_nom, dossier, digest, attendu in CORPUS:
            tirage = lire(z, tirage_nom)
            rapport = lire(z, dossier + "rapport.json")
            selection, releve = tirage.get("cas"), rapport.get("cas")
            if (not isinstance(selection, list) or not isinstance(releve, list)
                    or len(selection) != attendu or len(releve) != attendu
                    or tirage.get("sha256_identifiants_ordonnes") != digest):
                raise RelectureInvalide("Tirage ou relevé non conforme.")
            ids = [c.get("avis") for c in selection]
            if (len(set(ids)) != attendu or bool(vus.intersection(ids))
                    or ids != [r.get("avis") for r in releve]
                    or any(not isinstance(x, str) or
                           not re.fullmatch(r"\d{2}-\d{3,8}", x) for x in ids)):
                raise RelectureInvalide("Identifiants ou ordre incohérents.")
            calcul = sha(json.dumps(ids, ensure_ascii=False,
                                   separators=(",", ":")).encode())
            if calcul != digest:
                raise RelectureInvalide("Empreinte du tirage incohérente.")
            vus.update(ids)
            for item, obs in zip(selection, releve):
                code = item["avis"]
                if obs.get("fichier_reponse") != code + ".json":
                    raise RelectureInvalide("Réponse mal associée.")
                raw = z.read(dossier + code + ".json")
                cle = "sha256_reponse_http" if attendu == 36 else "sha256_reponse"
                if sha(raw) != obs.get(cle):
                    raise RelectureInvalide("Réponse altérée : " + code)
                env = json.loads(raw)
                if (env.get("total_count") != 1
                        or len(env.get("results", [])) != 1
                        or env["results"][0].get("idweb") != code
                        or env["results"][0].get("dateparution") != item.get("date_parution")):
                    raise RelectureInvalide("Identité BOAMP divergente : " + code)
                source = env["results"][0]
                cas.append({
                    "avis": code, "date_parution": item["date_parution"],
                    "acheteur": source.get("nomacheteur"),
                    "objet": source.get("objet"),
                    "cohorte": "tirage_36" if attendu == 36 else "epreuve_24",
                    "octets": raw, "sha256": sha(raw),
                })
    if len(cas) != 60:
        raise RelectureInvalide("Les 60 avis ne sont pas couverts.")
    return sorted(cas, key=lambda c: (
        sha((SEMENCE + "\0" + c["avis"]).encode()), c["avis"]
    ))


def ecrire(chemin: Path, objet: dict) -> None:
    chemin.write_text(json.dumps(
        objet, ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n", encoding="utf-8")


def preparer(archive: Path, sortie: Path) -> dict:
    origine = sources(archive)
    if sortie.exists() or sortie.is_symlink():
        raise RelectureInvalide("Sortie existante : refus d'écrasement.")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    temporaire = Path(tempfile.mkdtemp(prefix=".double-relecture-", dir=sortie.parent))
    try:
        (temporaire / "sources").mkdir()
        fiches, mapping = [], []
        for num, item in enumerate(origine, start=1):
            ident = f"CAS{num:03d}"
            fichier = "sources/" + ident + ".json"
            (temporaire / fichier).write_bytes(item["octets"])
            fiches.append({
                "cas": ident, "avis": item["avis"],
                "date_parution": item["date_parution"],
                "acheteur": item["acheteur"], "objet": item["objet"],
                "fichier_source": fichier, "sha256_source": item["sha256"],
            })
            mapping.append({
                "cas": ident, "avis": item["avis"], "cohorte": item["cohorte"],
            })
        paquet = {
            "version": VERSION, "nombre_cas": len(fiches), "cas": fiches,
            "prequalifications_automatiques_exclues": True,
            "references_independantes_etablies": False,
            "question": "Que démontre cet avis précis, pour chacun de ses lots ?",
        }
        ecrire(temporaire / "paquet_commun.json", paquet)
        empreinte = sha((temporaire / "paquet_commun.json").read_bytes())
        ecrire(temporaire / "correspondances_privees.json", {
            "sha256_paquet": empreinte, "cohortes": mapping,
            "sha256_archive_origine": sha(archive.read_bytes()),
            "ne_pas_transmettre_aux_lecteurs": True,
        })
        forme = [{
            "cas": x["cas"], "statut_avis": "A_VERIFIER",
            "preuve_statut": "", "lots": [],
            "observation_hors_lot": "",
            "cause_de_non_attribution": "A_VERIFIER",
            "preuve_causale_supplementaire": "", "notes": "",
        } for x in fiches]
        for nom in ("relecteur_1", "relecteur_2"):
            dest = temporaire / nom
            dest.mkdir()
            ecrire(dest / "jugements_vierges.json", {
                "version": VERSION, "sha256_paquet": empreinte,
                "identifiant_relecteur": "",
                "declaration_lecture_sans_predictions": False,
                "jugements": forme,
            })
        (temporaire / "CONSIGNES.md").write_text(
            "# Relecture des résultats officiels BOAMP\n\n"
            "Lire les fichiers sources/CASxxx.json et leur contenu donnees. "
            "Chaque jugement examine uniquement ce qui est documenté DANS cet avis. "
            "Ne pas consulter les rapports de préqualification, ni l'autre lecteur. "
            "Le fichier correspondances_privees.json ne doit pas être transmis.\n\n"
            "Statut de l'avis : RESULTATS_PAR_LOT, ATTRIBUTION_SANS_LOT, "
            "SANS_RESULTAT_DANS_CET_AVIS, ou INDETERMINE. "
            "Un avis de consultation sans attribution ne prouve pas zéro offre.\n\n"
            "Pour un avis RESULTATS_PAR_LOT, renseigner dans lots chaque identifiant "
            "de lot une seule fois avec les champs lot, decision "
            "(ATTRIBUE, NON_ATTRIBUE, INDETERMINE), code_motif (ou null), "
            "offres_totales (entier ou null), offres_electroniques (entier ou null), "
            "preuve_decision et preuve_effectifs (chemin dans donnees). "
            "Ne jamais déduire tenders=0 de no-rece, ni no-rece de tenders=0. "
            "t-esubm=0 seul ne prouve pas zéro offre totale.\n\n"
            "Cause de non-attribution : NON_ETABLIE, DOCUMENTEE ou INDETERMINEE. "
            "Pour DOCUMENTEE fournir un passage supplémentaire étayant le lien causal, "
            "sans substituer une hypothèse plausible à une preuve. "
            "Les deux formulaires sont à finaliser et sceller séparément ; "
            "A_VERIFIER ne constitue pas un verdict.\n",
            encoding="utf-8",
        )
        # Dossiers prêts à transmettre séparément, sans correspondances privées.
        for nom in ("relecteur_1", "relecteur_2"):
            dossier = temporaire / nom
            shutil.copy2(temporaire / "paquet_commun.json", dossier / "paquet_commun.json")
            shutil.copy2(temporaire / "CONSIGNES.md", dossier / "CONSIGNES.md")
            shutil.copytree(temporaire / "sources", dossier / "sources")
        temporaire.rename(sortie)
        return {"nombre_cas": len(fiches), "sha256_paquet": empreinte,
                "references_independantes_etablies": False}
    finally:
        if temporaire.exists():
            shutil.rmtree(temporaire)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        print(json.dumps(preparer(a.archive, a.sortie), ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        p.exit(1, f"Double lecture non préparée : {exc}\n")


if __name__ == "__main__":
    main()
