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
    {
        "code": "B06",
        "title": "DGA — recrutement d'ingénieurs cyber",
        "source_url": "https://www.assemblee-nationale.fr/dyn/opendata/RINFANR5L16B2068.html",
        "prompt": "Une organisation publique de défense doit recruter des ingénieurs cyber dans un marché structurellement déficitaire. Les concours d'ingénieurs fonctionnaires pourvoient environ la moitié des postes et l'affectation peut intervenir près d'un an après l'expression du besoin. Identifier les voies à comparer pour réduire le délai de mobilisation.",
        "expected_routes": ["RECRUTEMENT_CONTRACTUEL", "RECRUTEMENT_PERMANENT", "REFORME_PROCESSUS_RECRUTEMENT"],
        "expected_resource_forms": ["PERSONNE"],
        "outcome_summary": "Le recours aux ingénieurs civils contractuels est décrit comme plus immédiatement disponible que le recrutement statutaire.",
        "label_quality": "STRONG",
    },
    {
        "code": "B07",
        "title": "COMCYBER — réserve comme capacité rare mobilisable",
        "source_url": "https://www.assemblee-nationale.fr/dyn/opendata/RINFANR5L16B2068.html",
        "prompt": "Une organisation de cyberdéfense doit renforcer ponctuellement ses unités avec des compétences rares en réseaux, cryptographie, rétro-conception, analyse de vulnérabilités et audit. Identifier les formes de ressource et les voies de mobilisation adaptées à un besoin intermittent.",
        "expected_routes": ["RESERVE_OPERATIONNELLE", "MISSION_TEMPORAIRE"],
        "expected_resource_forms": ["PERSONNE", "VIVIER"],
        "outcome_summary": "La réserve cyber est utilisée pour apporter des compétences rares ou peu présentes dans les unités permanentes.",
        "label_quality": "STRONG",
    },
    {
        "code": "B08",
        "title": "Saint-Brieuc — conseil scientifique en difficulté",
        "source_url": "https://www.igedd.developpement-durable.gouv.fr/revision-de-la-comitologie-du-parc-eolien-en-mer-a4393.html",
        "prompt": "Le conseil scientifique d'un grand projet public rencontre des difficultés de fonctionnement. Des opérateurs de l'État sont alors mobilisés pour fournir des avis scientifiques, tandis que les services déconcentrés sont sursollicités. Identifier la voie de résolution et les formes de ressource les plus plausibles.",
        "expected_routes": ["MOBILISATION_OPERATEURS_PUBLICS", "REFONTE_INTERFACE_SCIENCE_DECISION"],
        "expected_resource_forms": ["ORGANISME", "EQUIPE", "CONSEIL_SCIENTIFIQUE"],
        "outcome_summary": "Le rapport décrit une substitution partielle par des opérateurs publics et un problème d'interface entre expertise scientifique et décision.",
        "label_quality": "STRONG",
    },
    {
        "code": "B09",
        "title": "IGN — montée en capacité IA",
        "source_url": "https://www.senat.fr/rap/r24-379/r24-379-syn.pdf",
        "prompt": "Un opérateur public anticipe un besoin accru d'ingénieurs formés aux techniques récentes de la donnée et de l'IA. Il veut développer rapidement une capacité interne durable. Identifier les voies et formes de ressource pertinentes.",
        "expected_routes": ["RECRUTEMENT_PERMANENT", "FORMATION_INTERNE", "EQUIPE_INTERNE"],
        "expected_resource_forms": ["PERSONNE", "EQUIPE"],
        "outcome_summary": "L'IGN a mis en œuvre un plan de recrutement de 150 talents, dont 30 data scientists, faisant passer ses équipes IA de 8 à 30 ingénieurs spécialisés en environ deux ans.",
        "label_quality": "STRONG",
    },
    {
        "code": "B10",
        "title": "Météo-France — LabIA comme centre de ressource",
        "source_url": "https://www.senat.fr/rap/r24-379/r24-379-syn.pdf",
        "prompt": "Un opérateur public veut mettre de l'expertise IA à disposition de plusieurs directions internes, conduire des projets et maintenir un travail prospectif. Identifier la forme de ressource la plus adaptée et les voies de constitution.",
        "expected_routes": ["EQUIPE_INTERNE", "CENTRE_DE_RESSOURCE", "PARTENARIATS"],
        "expected_resource_forms": ["EQUIPE"],
        "outcome_summary": "Météo-France a créé en 2020 un LabIA de quatre personnes servant de centre de ressource pour les directions de l'établissement.",
        "label_quality": "STRONG",
    },
    {
        "code": "B11",
        "title": "Météo-France — requalification techniciens vers ingénieurs",
        "source_url": "https://www.senat.fr/rap/r20-840/r20-840_mono.html",
        "prompt": "Un opérateur scientifique a besoin de davantage d'ingénieurs et de moins de techniciens. Plus de 500 postes doivent être requalifiés, mais le rythme prévu est réduit par un arbitrage de gestion. Identifier les voies de résolution d'un déficit de capacité qui provient de la structure des emplois.",
        "expected_routes": ["REQUALIFICATION_INTERNE", "FORMATION_INTERNE", "GESTION_PREVISIONNELLE_COMPETENCES"],
        "expected_resource_forms": ["PERSONNE", "VIVIER"],
        "outcome_summary": "Le programme de requalification devait convertir plus de 500 postes ; un arbitrage a réduit de 282 à 170 le nombre prévu sur cinq ans.",
        "label_quality": "STRONG",
    },
    {
        "code": "B12",
        "title": "Santé — ingénieurs du génie sanitaire",
        "source_url": "https://sante.gouv.fr/IMG/pdf/rapport_jury_igs_2024_vf.pdf",
        "prompt": "Une administration de santé doit maintenir un corps d'ingénieurs capables d'exercer des missions d'expertise scientifique, technique et d'encadrement. Le vivier de formation s'est réduit, le concours est peu visible hors des agences régionales et certains candidats ne possèdent pas les bases scientifiques attendues. Identifier les voies à comparer.",
        "expected_routes": ["FORMATION", "RECRUTEMENT_STATUTAIRE", "DIVERSIFICATION_VIVIER"],
        "expected_resource_forms": ["PERSONNE", "VIVIER", "FORMATION"],
        "outcome_summary": "Le jury recommande explicitement une réflexion pour maintenir les possibilités de recrutement statutaire dans ce corps spécialisé.",
        "label_quality": "STRONG",
    },
    {
        "code": "B13",
        "title": "CAR-SPAW — recrutement limité par le cadre administratif",
        "source_url": "https://www.igedd.developpement-durable.gouv.fr/definition-d-un-modele-de-statut-et-de-a4323.html",
        "prompt": "Un centre public d'appui scientifique et technique international rencontre des difficultés de recrutement liées au plafond d'emploi et à son positionnement dans une administration publique. Identifier si le problème porte sur la découverte de compétences ou sur la voie de mobilisation.",
        "expected_routes": ["MODIFICATION_POSITIONNEMENT", "VOIE_CONTRACTUELLE_ADAPTEE", "PARTENARIAT"],
        "expected_resource_forms": ["PERSONNE", "ORGANISME"],
        "outcome_summary": "Le rapport rattache explicitement les difficultés de recrutement au positionnement administratif et au plafond d'emploi.",
        "label_quality": "STRONG",
    },
    {
        "code": "B14",
        "title": "Risque avalanche — capacité interministérielle et opérateurs",
        "source_url": "https://www.igedd.developpement-durable.gouv.fr/mission-d-expertise-conjointe-sur-le-risque-d-a4443.html",
        "prompt": "La gestion d'un risque naturel complexe mobilise plusieurs ministères et opérateurs scientifiques spécialisés. Il faut améliorer la cohérence, la prévision et l'alerte avant un événement international majeur. Identifier la forme de ressource et la voie de mobilisation adaptées.",
        "expected_routes": ["COORDINATION_INTERMINISTERIELLE", "MOBILISATION_OPERATEURS_PUBLICS", "COOPERATION_SCIENTIFIQUE"],
        "expected_resource_forms": ["ORGANISME", "EQUIPE", "RESEAU"],
        "outcome_summary": "La mission recommande de renforcer les services territoriaux et de conforter ONF-RTM, Météo-France, INRAE et ANENA dans leurs missions.",
        "label_quality": "PROVISIONAL",
    },
    {
        "code": "B15",
        "title": "Cyberdéfense — déficit massif et fidélisation",
        "source_url": "https://www.senat.fr/rap/r22-638/r22-638_mono.html",
        "prompt": "Une organisation publique vise plusieurs milliers de postes cyber mais conserve un déficit d'environ 1 100 postes non pourvus. Les salaires publics sont moins attractifs et certaines compétences demandent environ deux ans avant autonomie. Identifier les voies de résolution à comparer.",
        "expected_routes": ["RECRUTEMENT_PERMANENT", "FIDELISATION", "ATTRACTIVITE_REMUNERATION", "FORMATION_INTERNE"],
        "expected_resource_forms": ["PERSONNE", "VIVIER"],
        "outcome_summary": "Le rapport relie le déficit à l'offre de formation, aux salaires et au besoin de fidéliser des profils longs à former.",
        "label_quality": "STRONG",
    },
    {
        "code": "B16",
        "title": "IRSN — vacance de postes et concurrence nucléaire",
        "source_url": "https://www.senat.fr/rap/a23-132-3/a23-132-31.pdf",
        "prompt": "Un organisme public d'expertise nucléaire subit une forte concurrence pour les ingénieurs spécialisés dans un contexte de relance de la filière. Des dizaines de postes restent vacants. Identifier les voies de résolution à comparer.",
        "expected_routes": ["ATTRACTIVITE_REMUNERATION", "RECRUTEMENT_PERMANENT", "FIDELISATION"],
        "expected_resource_forms": ["PERSONNE", "VIVIER"],
        "outcome_summary": "Le rapport budgétaire mentionne 91 postes vacants à l'IRSN en 2023 et relie la difficulté au regain de demande de compétences nucléaires.",
        "label_quality": "STRONG",
    },
    {
        "code": "B17",
        "title": "Sûreté nucléaire — combinaison capacités internes et partenaires externes",
        "source_url": "https://www.senat.fr/seances/s202402/s20240207/s20240207009.html",
        "prompt": "Une autorité publique de sûreté doit concentrer des compétences rares tout en conservant une capacité à compléter ses moyens internes par des partenaires externes, la recherche et des groupes permanents d'experts. Identifier les formes de ressource et voies correspondant à ce besoin hybride.",
        "expected_routes": ["CAPACITE_INTERNE", "PARTENARIATS_EXTERNES", "GROUPE_EXPERTS", "COOPERATION_RECHERCHE"],
        "expected_resource_forms": ["PERSONNE", "EQUIPE", "GROUPE_EXPERTS", "ORGANISME"],
        "outcome_summary": "Le débat législatif décrit explicitement un modèle combinant moyens internes forts, partenaires externes, recherche et groupes permanents d'experts.",
        "label_quality": "PROVISIONAL",
    },
    {
        "code": "B18",
        "title": "CNES — contrôle négatif sur le recrutement d'ingénieurs",
        "source_url": "https://www.senat.fr/compte-rendu-commissions/20240617/financ.html",
        "prompt": "Un opérateur scientifique et technique public est interrogé sur d'éventuelles difficultés de ressources humaines, mais ne signale pas de problème particulier de recrutement d'ingénieurs et les formations disponibles semblent répondre aux besoins. Identifier la meilleure orientation.",
        "expected_routes": ["MECANISMES_EXISTANTS", "AUCUNE_INTERVENTION_NOUVELLE"],
        "expected_resource_forms": ["PERSONNE"],
        "outcome_summary": "Le compte rendu indique que le CNES ne mentionne pas de problème particulier de recrutement et que les formations actuelles semblent répondre aux besoins du secteur.",
        "label_quality": "STRONG",
    },
    {
        "code": "B19",
        "title": "Santé — maintien du vivier d'ingénieurs du génie sanitaire",
        "source_url": "https://sante.gouv.fr/IMG/pdf/rapport_jury_igs_2024_vf.pdf",
        "prompt": "Une administration sanitaire doit préserver un vivier d'ingénieurs disposant de bases scientifiques, de compétences réglementaires et d'expérience d'encadrement. Une formation historique a disparu, la visibilité du concours hors des agences régionales est faible et une partie des candidats n'atteint pas le niveau scientifique attendu. Identifier les voies de résolution.",
        "expected_routes": ["FORMATION", "DIVERSIFICATION_VIVIER", "RECRUTEMENT_STATUTAIRE"],
        "expected_resource_forms": ["PERSONNE", "VIVIER", "FORMATION"],
        "outcome_summary": "Le rapport du jury appelle l'administration à agir pour maintenir les possibilités de recrutement statutaire du corps des ingénieurs du génie sanitaire.",
        "label_quality": "STRONG",
    },
    {
        "code": "B20",
        "title": "Inspection environnementale — postes techniques non pourvus",
        "source_url": "https://www.senat.fr/rap/a23-132-3/a23-132-31.pdf",
        "prompt": "Une inspection technique de l'État ouvre des dizaines de postes supplémentaires mais peine à les pourvoir. Les écarts de rémunération avec le secteur privé sont importants pour les ingénieurs. Identifier les voies de résolution prioritaires.",
        "expected_routes": ["ATTRACTIVITE_REMUNERATION", "RECRUTEMENT_PERMANENT", "REFORME_CADRE_EMPLOI"],
        "expected_resource_forms": ["PERSONNE", "VIVIER"],
        "outcome_summary": "Le rapport indique que 50 postes ouverts depuis 2020 dans l'inspection des installations classées n'étaient pas pourvus et souligne de forts écarts de rémunération avec le privé.",
        "label_quality": "STRONG",
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
                    label_quality=item.get("label_quality", "PROVISIONAL"),
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
