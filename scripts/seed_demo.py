from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import BenchmarkCase, Episode, Hypothesis, NeedVersion, Organization, RouteAssessment, StakeholderContact

HYPOTHESES = [
    ("H1", "Le routeur apporte une valeur substantielle", "Plusieurs cas changent utilement de voie après qualification.", "L'orientation correcte est presque toujours évidente avant Frontière."),
    ("H2", "La fragmentation des sources constitue une friction importante", "Plusieurs sources doivent être interrogées pour identifier la ressource pertinente.", "Une ou deux sources existantes suffisent presque toujours."),
    ("H3", "Les cas antérieurs améliorent les suivants", "Sources, voies, règles ou précédents sont réutilisés entre institutions.", "Chaque épisode demande une investigation presque indépendante."),
    ("H4", "Un registre confidentiel d'épisodes produit de la valeur", "Les épisodes historiques modifient des décisions courantes et les institutions contribuent.", "Les cas sont incomparables ou la contribution institutionnelle est impraticable."),
    ("H5", "L'expertise ponctuelle résout une classe importante de besoins", "Des consultations courtes résolvent ou clarifient matériellement plusieurs cas.", "Les besoins exigent presque toujours une intégration longue."),
    ("H6", "La mobilité publique constitue une friction majeure", "P2 apparaît dans plusieurs institutions et domaines.", "P2 reste exceptionnel."),
    ("H7", "Une recherche extérieure spécialisée est additionnelle", "P3 est récurrent et la recherche spécialisée trouve plus vite des ressources R5.", "Les mécanismes ordinaires produisent des résultats comparables ou supérieurs."),
    ("H8", "Le problème principal survient après identification", "Budget, droit, sécurité, accès ou préparation dominent le chemin critique.", "L'identification de la ressource domine systématiquement."),
    ("H9", "Les conditions employeur déterminent la mobilisabilité", "Un cadre crédible de départ et de retour modifie plusieurs décisions réelles.", "Les conditions de retour ont peu d'effet comportemental."),
    ("H10", "Certains déficits se prêtent mieux à une résolution distribuée", "Des problèmes mesurables sont mieux servis par un défi que par une mission individuelle.", "La connaissance institutionnelle intégrée est presque toujours indispensable."),
    ("H11", "L'interopérabilité devient un actif national", "Les mêmes classes de capacités apparaissent entre organismes et réduisent le travail de qualification.", "La taxonomie se fragmente à chaque cas."),
    ("H12", "Le coût marginal baisse avec l'expérience", "Le temps de diagnostic ou de recherche baisse à complexité comparable avec qualité stable.", "Le temps humain par cas reste stable ou augmente."),
    ("H13", "La valeur dépasse le réseau personnel initial", "Les résultats se reproduisent hors réseau fondateur.", "Les ressources décisives proviennent durablement du réseau personnel initial."),
    ("H14", "Les données opérationnelles soutiennent un observatoire utile", "Les épisodes sont assez comparables pour produire des distributions stables.", "La standardisation est artificielle ou la sélection domine les résultats."),
    ("H15", "Une intervention institutionnelle nouvelle est réellement nécessaire", "Les mécanismes existants, même mieux connectés, laissent une friction résiduelle récurrente.", "Améliorer ou connecter les mécanismes existants suffit."),
]


CONTACTS = [
    ("DINUM", "Programme Entrepreneurs d’intérêt général", 1, "Identifier les cas que les mécanismes actuels couvrent mal.", "Partager 3 à 5 cas récents particulièrement difficiles à pourvoir ou mobiliser.", "Au moins un épisode documentable.", "Responsable opérationnel du cas"),
    ("DINUM", "RH numérique — Mobilité et Parcours", 1, "Tester si P2 et la mobilité publique constituent une friction récurrente.", "Partager 2 à 3 situations où la capacité existait dans l’État mais circulait mal.", "Un cas P2 potentiel documentable.", "Administration et agent concernés"),
    ("DINUM", "Département intelligence artificielle dans l’État", 1, "Identifier des besoins D2+ actuels avec capacité technique précisément définissable.", "Partager 2 à 3 projets réellement ralentis par une capacité identifiable.", "Un besoin actuel suffisamment mûr.", "Responsable du projet"),
    ("DITP", "Agence de conseil interne de l’État", 2, "Tester la redondance avec les mécanismes publics existants.", "Identifier des cas déjà bien couverts et la frontière éventuelle avec une expertise scientifique spécialisée.", "Un contre-exemple ou une frontière de périmètre documentée.", "Administration concernée"),
    ("Organisme scientifique", "Partenariats publics / direction scientifique", 2, "Tester si l’unité pertinente est parfois une équipe ou un laboratoire.", "Partager 2 à 3 cas où une capacité collective aurait accéléré une mission publique.", "Un épisode impliquant une ressource collective.", "Équipe scientifique et responsable opérationnel"),
]

BENCHMARK_CASES = [
    {
        "code": "B01",
        "title": "France Compétences — recrutement de data scientists",
        "source_url": "https://www.senat.fr/fileadmin/Illustrations/Controle/Structures_temporaires/2024-2025/CE-Agences_Etat/TOME_I_-_Rapport_CE_Agences.pdf",
        "prompt": "Une agence publique cherche depuis plusieurs mois à recruter des profils de data scientists décrits comme spécifiques et rares. La rémunération proposée est signalée comme peu compétitive. Identifier la capacité requise, les formes de ressource pertinentes et les principales voies de résolution à tester.",
        "expected_routes": ["RECRUTEMENT_PERMANENT", "ATTRACTIVITE_REMUNERATION"],
        "expected_resource_forms": ["PERSONNE"],
        "outcome_summary": "Signal public de rareté et d'attractivité ; l'état opérationnel actuel reste à vérifier.",
    },
    {
        "code": "B02",
        "title": "Ministère de l'Agriculture — expertise scientifique et technique",
        "source_url": "https://agriculture.gouv.fr/gerer-lexpertise-dun-ministere-technique",
        "prompt": "Un ministère technique doit mobiliser rapidement de l'expertise scientifique interne et externe pour appuyer des décisions, parfois en situation de crise. Le dispositif existant identifie imparfaitement les besoins et les agents experts. Identifier les voies et formes de ressource à privilégier.",
        "expected_routes": ["RECHERCHE_PUBLIQUE", "COOPERATION_SCIENTIFIQUE", "RECHERCHE_EXTERIEURE"],
        "expected_resource_forms": ["PERSONNE", "EQUIPE", "ORGANISME"],
        "outcome_summary": "Le rapport public soutient un problème de découverte, d'orientation et de mobilisation.",
    },
    {
        "code": "B03",
        "title": "Transition écologique — articulation recherche et besoins opérationnels",
        "source_url": "https://www.igedd.developpement-durable.gouv.fr/prise-en-compte-de-la-recherche-dans-l-elaboration-a4405.html",
        "prompt": "Une administration dispose d'un réseau scientifique et technique dense, mais les productions de recherche sont dispersées et s'articulent difficilement avec les besoins opérationnels des directions centrales. Identifier le mécanisme de résolution le plus plausible et les ressources à rechercher.",
        "expected_routes": ["RECHERCHE_PUBLIQUE", "COOPERATION_SCIENTIFIQUE", "ROUTAGE"],
        "expected_resource_forms": ["EQUIPE", "LABORATOIRE", "ORGANISME"],
        "outcome_summary": "Signal public en faveur du routage et de la découverte de capacités existantes.",
    },
    {
        "code": "B04",
        "title": "Biodiversité — synthèse scientifique ponctuelle",
        "source_url": "https://www.igedd.developpement-durable.gouv.fr/preparation-d-un-etat-de-l-art-des-connaissances-a4290.html",
        "prompt": "Une administration commande un état de l'art scientifique sur plusieurs sujets complexes. Plusieurs voies sont envisagées, notamment une expertise scientifique collective ou une mission confiée à deux postdoctorants. Identifier les formes de ressource et voies adaptées.",
        "expected_routes": ["EXPERTISE_SCIENTIFIQUE_COLLECTIVE", "MISSION_COURTE"],
        "expected_resource_forms": ["EQUIPE", "LABORATOIRE", "PERSONNE"],
        "outcome_summary": "Le cas public illustre un choix entre ressource collective et ressources individuelles temporaires.",
    },
    {
        "code": "B05",
        "title": "État — tension sur les compétences data",
        "source_url": "https://www.numerique.gouv.fr/actualites/rapport-evaluation-des-besoins-de-letat-en-competences-et-expertises-en-matiere-de-donnee/",
        "prompt": "Les métiers de la donnée sont décrits comme en tension et le métier de data scientist comme critique, avec des besoins supérieurs aux effectifs disponibles et un problème d'attractivité en milieu de carrière. Identifier les voies et formes de ressource à comparer.",
        "expected_routes": ["RECRUTEMENT_PERMANENT", "MOBILITE_PUBLIQUE", "ATTRACTIVITE_REMUNERATION"],
        "expected_resource_forms": ["PERSONNE"],
        "outcome_summary": "Contexte quantitatif de tension ; il ne constitue pas encore un épisode individuel.",
    },
]

CASES = [
    ("S01", "La capacité était déjà dans l'équipe", "Capacité locale disponible", "R1 — capacité interne"),
    ("S02", "La compétence existe ailleurs dans l'État", "Capacité publique mobilisable", "R2 — capacité publique"),
    ("S03", "La compétence publique existe mais la mobilité échoue", "P2 — mobilité publique", "R5 — mobilité temporaire"),
    ("S04", "Rareté extérieure réelle", "P3 — rareté vérifiée", "R4 — recherche spécialisée"),
    ("S05", "Les candidats existent, le budget n'existe pas", "Friction budgétaire", "Préparation budgétaire"),
    ("S06", "La ressource existe, la sécurité domine", "Friction sécurité et accès", "Coordination du déploiement"),
    ("S07", "Une consultation courte suffit", "Profondeur d'intervention surestimée", "Expertise ponctuelle"),
    ("S08", "Le problème se prête à un défi", "Résolution distribuée", "Défi technique"),
    ("S09", "Le marché privé fonctionne correctement", "Aucune friction résiduelle", "Achat existant"),
    ("S10", "Le laboratoire est la bonne ressource", "Unité de ressource collective", "Coopération scientifique"),
    ("S11", "Le besoin est permanent", "Temporalité permanente", "Recrutement permanent"),
    ("S12", "Le droit de retour change la décision", "Condition employeur", "Accord employeur + mobilité"),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.scalar(select(Hypothesis.id).limit(1)):
            for code, label, positive, negative in HYPOTHESES:
                db.add(Hypothesis(code=code, label=label, definition=label, strengthening_criterion=positive, weakening_criterion=negative))
        org = db.scalar(select(Organization).where(Organization.name == "Jeu synthétique Frontière"))
        if org is None:
            org = Organization(name="Jeu synthétique Frontière", organization_type="test", public_sector=False)
            db.add(org)
            db.flush()
        if not db.scalar(select(StakeholderContact.id).limit(1)):
            for idx, (institution, function, priority, hypothesis, ask, success, next_intro) in enumerate(CONTACTS, 1):
                db.add(StakeholderContact(
                    code=f"INT-{idx:03d}", institution=institution, function=function, priority=priority,
                    hypothesis_tested=hypothesis, single_ask=ask, minimal_success=success,
                    next_intro_sought=next_intro, document_to_send="Note de recherche d’une page",
                ))
        if not db.scalar(select(BenchmarkCase.id).limit(1)):
            import json
            for item in BENCHMARK_CASES:
                db.add(BenchmarkCase(
                    code=item["code"],
                    title=item["title"],
                    source_url=item["source_url"],
                    prompt=item["prompt"],
                    expected_routes_json=json.dumps(item["expected_routes"], ensure_ascii=False),
                    expected_resource_forms_json=json.dumps(item["expected_resource_forms"], ensure_ascii=False),
                    expected_resources_json="[]",
                    outcome_summary=item["outcome_summary"],
                    label_quality="PROVISIONAL",
                ))
        existing = {e.code for e in db.scalars(select(Episode).where(Episode.synthetic.is_(True))).all()}
        for idx, (suffix, title, diagnosis, route) in enumerate(CASES, 1):
            code = f"TEST-{suffix}"
            if code in existing:
                continue
            ep = Episode(code=code, organization_id=org.id, title=title, synthetic=True, status="ORIENTE", demand_level="D3", need_preexisting_frontiere=True)
            db.add(ep); db.flush()
            db.add(NeedVersion(episode_id=ep.id, current_situation=title, desired_outcome="Identifier la plus petite intervention appropriée.", counterfactual_plan="Voie initiale supposée différente de la solution de test.", initial_frontiere_hypothesis=diagnosis))
            db.add(RouteAssessment(episode_id=ep.id, route_code=f"T{idx:02d}", route_label=route, status_initial="PLAUSIBLE", status_current="ACTIVEE", evidence_for=diagnosis))
        db.commit()
    print("Jeu de démonstration initialisé.")


if __name__ == "__main__":
    main()
