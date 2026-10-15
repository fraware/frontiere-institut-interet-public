/** Publier deux concordances documentaires BOAMP–DECP, strictement bornées
 * à l'enquête indépendante de 17 avis archivée dans le dépôt.
 *
 * Ce fichier NE crée ni liens contrat–avis, ni besoins ouverts. Il ne
 * compare jamais des noms et n'interroge aucun service réseau.
 */
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const RACINE = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const CHEMIN = "institutionnel/besoins_publics/correspondances_siret_boamp_decp_17.json";
const COTE = "institutionnel/besoins_publics/correspondances_siret_boamp_decp_17.sha256";
const SOURCE_SHA = "6dbdd44379ddbc48f2d46f59ae410653613ca880a431a38b716d4a9f7ec544d7";
const SHA = /^[a-f0-9]{64}$/;
const SIRET = /^[0-9]{14}$/;
const ID_AVIS = /^[0-9]{2}-[0-9]{2,8}$/;
const DATE = /^20[0-9]{2}-[0-9]{2}-[0-9]{2}$/;

const hash = octets => createHash("sha256").update(octets).digest("hex");
function verifier(condition, raison) {
  if (!condition) throw new Error("Avis BOAMP corroborés : " + raison);
}

/** Conserver exclusivement les champs nécessaires au regroupement,
 * et établir leur cohérence avec les mesures du rapport source.
 */
export function projeterAvisCorrobores(rapport, empreinteSource) {
  verifier(empreinteSource === SOURCE_SHA, "empreinte d'origine inconnue");
  verifier(rapport?.version === "correspondances-siret-boamp-decp-17-v1" &&
    rapport.population === "17_avis_boamp_d_un_tirage_independant_non_representatif" &&
    rapport.nombre_avis === 17 && rapport.nombre_siret_boamp_distincts === 16 &&
    rapport.nombre_avis_avec_etablissement_exact_api === 17 &&
    rapport.nombre_avis_avec_siret_egal_a_un_acheteur_decp === 2 &&
    rapport.aucune_identite_de_contrat_deduite === true &&
    (rapport.contrats_communs_demonstres === undefined ||
      rapport.contrats_communs_demonstres === 0) &&
    rapport.role_acheteur_juridiquement_etabli === false &&
    rapport.siret_boamp_initialement_sans_schema === true &&
    Array.isArray(rapport.observations) && rapport.observations.length === 17,
    "portée ou dénominateur contradictoire");

  const identifiants = new Set(), etablissements = new Set(), retenus = [];
  let valides = 0, concordants = 0;
  for (const avis of rapport.observations) {
    verifier(ID_AVIS.test(avis?.avis_boamp || "") &&
      !identifiants.has(avis.avis_boamp) && DATE.test(avis.date_parution || "") &&
      SIRET.test(avis.siret_acheteur_sans_schema_dans_avis || "") &&
      typeof avis.siret_etablissement_exact_dans_api === "boolean" &&
      typeof avis.rapprochement_acheteur_documentaire === "boolean" &&
      avis.identite_contrat_decp_demonstree === false &&
      avis.role_acheteur_juridiquement_confirme === false &&
      Number.isSafeInteger(avis.marches_decp_identites_meme_siret) &&
      avis.marches_decp_identites_meme_siret >= 0 &&
      (avis.rapprochement_acheteur_documentaire ===
        (avis.siret_etablissement_exact_dans_api &&
          avis.marches_decp_identites_meme_siret > 0)),
      "identité ou statut d'avis incompatible");
    identifiants.add(avis.avis_boamp);
    etablissements.add(avis.siret_acheteur_sans_schema_dans_avis);
    valides += Number(avis.siret_etablissement_exact_dans_api);
    concordants += Number(avis.rapprochement_acheteur_documentaire);
    const preuve = avis.preuves;
    verifier(SHA.test(preuve?.sha256_reponse_boamp || "") &&
      SHA.test(preuve?.sha256_reponse_administrative || "") &&
      typeof preuve?.chemin_siret_dans_avis === "string" &&
      preuve.chemin_siret_dans_avis.startsWith("/results/0/donnees/EFORMS/") &&
      typeof preuve?.chemin_etablissement_reponse_administrative === "string" &&
      preuve.chemin_etablissement_reponse_administrative.startsWith("/results/"),
      "preuve documentaire manquante");
    if (avis.rapprochement_acheteur_documentaire) {
      retenus.push({
        avis_boamp: avis.avis_boamp,
        date_parution: avis.date_parution,
        acheteur_siret: avis.siret_acheteur_sans_schema_dans_avis,
        identites_marches_decp_dans_archives: avis.marches_decp_identites_meme_siret,
        preuve_boamp_sha256: preuve.sha256_reponse_boamp,
        preuve_administrative_sha256: preuve.sha256_reponse_administrative,
        chemin_preuve_boamp: preuve.chemin_siret_dans_avis
      });
    }
  }
  verifier(identifiants.size === 17 && etablissements.size === 16 &&
    valides === 17 && concordants === 2 && retenus.length === 2,
    "effectifs incompatibles");
  retenus.sort((a, b) => a.avis_boamp.localeCompare(b.avis_boamp));
  return {
    version: "frontiere-avis-boamp-corrobores-v1",
    population_avis_etudies: 17,
    population_sirets_distincts: 16,
    nombre_avis_corroborees: 2,
    sources_archives_non_exhaustives: true,
    contrats_communs_demonstres: 0,
    rapprochement_par_nom: false,
    extrait_decp_public_couvert: false,
    sha256_registre_source: SOURCE_SHA,
    avis: retenus
  };
}

/** Le registre complet est re-haché avant toute mise en ligne. */
export function construireAvisCorrobores(racine = RACINE) {
  const brut = readFileSync(join(racine, CHEMIN));
  verifier(brut.length >= 1000 && brut.length <= 100000 &&
    hash(brut) === SOURCE_SHA, "contenu du registre altéré");
  const temoin = readFileSync(join(racine, COTE), "utf8");
  verifier(temoin === SOURCE_SHA + "  correspondances_siret_boamp_decp_17.json\n",
    "empreinte témoin incompatible");
  const publication = projeterAvisCorrobores(JSON.parse(brut.toString("utf8")), hash(brut));
  const contenu = Buffer.from(JSON.stringify(publication) + "\n", "utf8");
  verifier(contenu.length <= 20_000, "fichier public trop volumineux");
  return { publication, contenu, octets: contenu.length, sha256: hash(contenu) };
}
