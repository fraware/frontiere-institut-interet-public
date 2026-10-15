/** Typologie probatoire des documents publics archivés par FRONTIÈRE.
 *
 * Les trois catégories sont des CONSTATS DOCUMENTAIRES, pas des prévisions
 * de besoin ni un diagnostic de capacités manquantes. Un avis BOAMP ne
 * renseigne pas ici suffisamment son sous-type pour conclure à une
 * consultation ouverte ; une attribution DECP ne prouve pas son exécution.
 * Ce module pur est utilisé par le générateur et par le navigateur.
 */
export const VERSION_QUALIFICATION = "frontiere-qualification-besoins-v1";

export const TYPES_DOCUMENTAIRES = Object.freeze({
  boamp: Object.freeze({
    code: "avis_commande_publique_publie",
    titre: "Avis de commande publique publié",
    conclusion_besoin: "non_etablie",
    conclusion_execution: "non_etablie",
    explication: "Le seul avis indexé ne précise pas suffisamment son type et " +
      "ne prouve ni consultation encore ouverte ni besoin non satisfait."
  }),
  emplois: Object.freeze({
    code: "recrutement_public_annonce",
    titre: "Recherche de compétences publiée",
    conclusion_besoin: "recherche_de_competences_a_la_publication",
    conclusion_execution: "non_etablie",
    explication: "L'offre documente une recherche de compétences à sa date " +
      "de publication, sans établir sa validité actuelle, un recrutement " +
      "effectif ou une pénurie de compétences."
  }),
  decp: Object.freeze({
    code: "marche_public_attribue_declare",
    titre: "Attribution de marché déclarée",
    conclusion_besoin: "besoin_actuel_non_etabli",
    conclusion_execution: "non_etablie",
    explication: "La notice de marché attribué documente une opération " +
      "contractuelle déclarée ; elle ne prouve ni livraison, ni exécution " +
      "effective, ni capacité actuellement manquante."
  })
});

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const PROVENANCES = {
  boamp: /^institutionnel\/besoins_publics\/annonces_boamp\.json$/,
  emplois: /^institutionnel\/besoins_publics\/offres_postes\/lot_[0-9a-f]{2}\.jsonl$/,
  decp: /^institutionnel\/decp\/(sonde_aife_json|lot_dgfip_xml)\.json$/
};

function valideDate(date) {
  if (typeof date !== "string" || !DATE.test(date)) return false;
  const d = new Date(date + "T00:00:00Z");
  return Number.isFinite(d.valueOf()) && d.toISOString().slice(0, 10) === date;
}

/** Qualification déterministe à provenance identifiée.
 *
 * @param {object} document Enregistrement extrait d'une archive vérifiée.
 * @returns {{version:string,type:string,besoin:string,execution:string,etat_actuel:string}}
 */
export function qualifierDocument(document) {
  const source = document?.source;
  const type = Object.hasOwn(TYPES_DOCUMENTAIRES, source)
    ? TYPES_DOCUMENTAIRES[source] : null;
  if (!type || typeof document.id !== "string" || !document.id.trim() ||
      typeof document.titre !== "string" || !document.titre.trim() ||
      !valideDate(document.date) ||
      typeof document.provenance !== "string" ||
      !PROVENANCES[source].test(document.provenance)) {
    throw new Error("Document public sans provenance, identité ou date admise.");
  }
  if (source === "decp" && !/^[0-9]{14}\/.{1,100}$/.test(document.id)) {
    throw new Error("Référence d'acheteur DECP sans SIRET déclaré.");
  }
  return {
    version: VERSION_QUALIFICATION,
    type: type.code,
    besoin: type.conclusion_besoin,
    execution: type.conclusion_execution,
    etat_actuel: "non_etabli"
  };
}

/** Prouver que les catégories additionnent exactement les documents retenus,
 * sans produire de taux national ni créer une catégorie de besoin présumé.
 */
export function bilanQualifications(documents) {
  if (!Array.isArray(documents)) throw new Error("Documents à qualifier absents.");
  const sources = ["boamp", "emplois", "decp"];
  const comptages = new Map(sources.map(source => [source, 0]));
  const identites = new Set();
  for (const document of documents) {
    const attendu = qualifierDocument(document);
    const cle = document.source + "\u0000" + document.id;
    if (identites.has(cle) ||
        JSON.stringify(document.qualification) !== JSON.stringify(attendu)) {
      throw new Error("Qualification documentaire incohérente ou dupliquée.");
    }
    identites.add(cle);
    comptages.set(document.source, comptages.get(document.source) + 1);
  }
  const total = [...comptages.values()].reduce((a, b) => a + b, 0);
  return {
    version: VERSION_QUALIFICATION,
    documents_qualifies: total,
    couverture_nationale_demonstree: false,
    besoins_actuels_non_satisfaits_demonstres: 0,
    projets_communs_demonstres: 0,
    hypotheses_de_besoins: 0,
    sources: sources.map(source => ({
      source, type: TYPES_DOCUMENTAIRES[source].code,
      documents: comptages.get(source)
    })),
    precision: "Les catégories qualifient les documents de l'extrait indexé. " +
      "Les offres d'emploi signalent une recherche de compétences à la date " +
      "de publication. Ni besoin encore ouvert, ni projet commun, ni exécution " +
      "effective ne sont déduits des avis BOAMP ou des attributions DECP."
  };
}
