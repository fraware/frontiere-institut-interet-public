"""Inventorier les liens exacts vers les pièces de consultation des avis officiels.

Cette restitution ne télécharge pas les pièces, ne contourne aucune
identification et ne certifie ni livraison ni réception des prestations.
"""
from __future__ import annotations

import argparse
from collections import Counter
import html
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

try:
    from scripts.collecter_notices_pilotes_boamp import verifier_capture
    from scripts.collecter_avis_lies_boamp import verifier_lies
    from scripts.capturer_avis_amont_boamp import verifier_amont
    from scripts.qualifier_captures_notices_boamp import ecrire
except ModuleNotFoundError:
    from collecter_notices_pilotes_boamp import verifier_capture
    from collecter_avis_lies_boamp import verifier_lies
    from capturer_avis_amont_boamp import verifier_amont
    from qualifier_captures_notices_boamp import ecrire

VERSION = "inventaire-references-pieces-boamp-v1"


class InventaireInvalide(ValueError):
    """Référence de document mal formée ou contradiction de provenance."""


def parcourir(noeud, chemin=""):
    if isinstance(noeud, dict):
        for cle, valeur in noeud.items():
            cible = chemin + "/" + cle.replace("~", "~0").replace("/", "~1")
            if cle == "cac:CallForTendersDocumentReference":
                for indice, item in enumerate(valeur if isinstance(valeur, list) else [valeur]):
                    if not isinstance(item, dict):
                        raise InventaireInvalide("Référence de consultation mal structurée.")
                    provenance = cible + ("/" + str(indice) if isinstance(valeur, list) else "")
                    yield provenance, item
            else:
                yield from parcourir(valeur, cible)
    elif isinstance(noeud, list):
        for indice, item in enumerate(noeud):
            yield from parcourir(item, chemin + "/" + str(indice))


def references(notice: dict) -> list[dict]:
    brut = notice.get("donnees")
    if not isinstance(brut, str):
        raise InventaireInvalide("Formulaire officiel absent.")
    try:
        formulaire = json.loads(brut)
    except json.JSONDecodeError as exc:
        raise InventaireInvalide("Formulaire officiel illisible.") from exc
    documents = []
    for origine, reference in parcourir(formulaire):
        attachement = reference.get("cac:Attachment")
        externe = attachement.get("cac:ExternalReference") if isinstance(attachement, dict) else None
        uri = externe.get("cbc:URI") if isinstance(externe, dict) else None
        identifiant = reference.get("cbc:ID")
        if isinstance(identifiant, dict):
            identifiant = identifiant.get("#text")
        identifiant = identifiant if isinstance(identifiant, str) else None
        if uri is None:
            documents.append({
                "origine_champ": origine, "identifiant_document_declare": identifiant,
                "uri_litterale": None, "uri_normalisee": None,
                "statut": "reference_sans_uri", "contenu_piece_obtenu": False,
            })
            continue
        if not isinstance(uri, str):
            raise InventaireInvalide("URI documentaire non textuelle.")
        url = html.unescape(uri)
        cible = urlsplit(url)
        if (cible.scheme not in ("https", "http") or not cible.netloc or
                cible.username or cible.password):
            raise InventaireInvalide("URI documentaire non admissible.")
        parametres = parse_qs(cible.query)
        # Pour cette plateforme, seul un identifiant DCE explicite
        # distingue un dossier déterminé du portail générique.
        dossier_precis = (
            cible.hostname == "www.marches-publics.info"
            and parametres.get("type") == ["DCE"]
            and len(parametres.get("IDM", [])) == 1
            and parametres["IDM"][0].isdigit()
        )
        documents.append({
            "origine_champ": origine, "identifiant_document_declare": identifiant,
            "uri_litterale": uri, "uri_normalisee": url,
            "statut": (
                "lien_dossier_consultation_identifie"
                if dossier_precis else "lien_portail_generique"
            ),
            "contenu_piece_obtenu": False,
        })
    return documents


def produire(principaux: Path, lies: Path, amont: Path, registre: Path) -> dict:
    prim = verifier_capture(principaux)
    suivis = verifier_lies(lies, principaux)
    amonts = verifier_amont(amont, principaux, lies, registre)
    familles = [
        (principaux, "six_cas_pilotes", prim["cas"], "identifiant",
         "fichier_reponse", "sha256_reponse_http", "etat_observation",
         "notice_retrouvee_et_identifiee"),
        (lies, "avis_explicitement_lie", suivis["avis"], "identifiant",
         "fichier", "sha256", "etat_recherche", "notice_retrouvee"),
        (amont, "avis_amont_par_reference", amonts["avis"], "avis_amont",
         "fichier_reponse", "sha256_reponse_http", "statut",
         "avis_amont_identifie_par_reference"),
    ]
    inventaire, codes = [], set()
    for dossier, famille, fiches, idcle, fcle, sha_cle, etatcle, etat_ok in familles:
        for fiche in fiches:
            code = fiche[idcle]
            if code in codes:
                raise InventaireInvalide("Avis dupliqué entre archives.")
            codes.add(code)
            observe = fiche[etatcle] == etat_ok
            etat_observation = ("notice_observee" if observe else
                "notice_relevee_date_divergente" if fiche[etatcle] == "date_officielle_divergente"
                else "absent_du_releve")
            references_documentaires = []
            if observe:
                notice = json.loads((dossier / fiche[fcle]).read_bytes())["results"][0]
                references_documentaires = references(notice)
            inventaire.append({
                "avis": code, "famille": famille,
                "statut_observation": etat_observation,
                "fichier_source": fiche[fcle],
                "sha256_reponse_http": fiche[sha_cle],
                "references_documentaires_officielles": references_documentaires,
                "pieces_de_consultation_obtenues": False,
                "proces_verbal_de_reception_obtenu": False,
                "premiere_utilisation_scientifique_documentee": False,
            })
    return {
        "version": VERSION,
        "nombre_avis": len(inventaire),
        "repartition_familles": dict(sorted(Counter(x["famille"] for x in inventaire).items())),
        "avis_avec_lien_de_consultation": sum(
            any(d["uri_normalisee"] for d in x["references_documentaires_officielles"])
            for x in inventaire
        ),
        "avis_avec_lien_dossier_precis": sum(
            any(d["statut"] == "lien_dossier_consultation_identifie"
                for d in x["references_documentaires_officielles"])
            for x in inventaire
        ),
        "avis_avec_lien_portail_generique": sum(
            any(d["statut"] == "lien_portail_generique"
                for d in x["references_documentaires_officielles"])
            for x in inventaire
        ),
        "nombre_pieces_contenu_obtenu": 0,
        "preuves_de_reception_obtenues": 0,
        "preuves_de_premiere_utilisation_obtenues": 0,
        "avis": inventaire,
        "interpretation": (
            "Les liens sont transcrits de documents officiels archivés. "
            "Une adresse de consultation ne constitue pas une pièce obtenue. "
            "Les documents confidentiels et les traces de réception ou "
            "d'utilisation effective ne sont pas présumés."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--principaux", type=Path, required=True)
    p.add_argument("--lies", type=Path, required=True)
    p.add_argument("--amont", type=Path, required=True)
    p.add_argument("--registre", type=Path,
                   default=Path("evaluation/avis_amont_cibles_boamp_v1.json"))
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args()
    try:
        rapport = produire(a.principaux, a.lies, a.amont, a.registre)
        ecrire(rapport, a.sortie)
        print(json.dumps({
            "avis": rapport["nombre_avis"],
            "avec_lien_consultation": rapport["avis_avec_lien_de_consultation"],
            "avec_lien_dossier_precis": rapport["avis_avec_lien_dossier_precis"],
            "pieces_obtenues": rapport["nombre_pieces_contenu_obtenu"],
        }, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.exit(1, f"Inventaire documentaire non validé : {exc}\n")


if __name__ == "__main__":
    main()
