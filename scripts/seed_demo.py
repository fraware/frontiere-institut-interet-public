from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Episode, Hypothesis, NeedVersion, Organization, RouteAssessment

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
