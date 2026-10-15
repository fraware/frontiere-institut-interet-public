/** Rapprochements documentaires exacts DECP–DILA, à partir des seules
 * archives versionnées. Aucune recherche par nom, aucun appel réseau.
 *
 * Les résultats expriment la coïncidence d'un SIRET déclaré dans deux
 * producteurs distincts. Ils ne valident ni la personnalité juridique de
 * l'acheteur ni sa compétence pour un marché particulier.
 */
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const RACINE = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SOURCES = Object.freeze([
  { code: "roae", source_id: "dila_roae",
    manifeste: "institutionnel/instantanes/roae_manifest.json",
    prefixe: /^institutionnel\/entites\/roae\/roae_[0-9]{2}\.jsonl$/,
    compteur: "nombre_services" },
  { code: "annuaire_local", source_id: "dila_annuaire_local",
    manifeste: "institutionnel/instantanes/annuaire_local_manifest.json",
    prefixe: /^institutionnel\/entites\/locales\/annuaire_local_[0-9]{3}\.jsonl$/,
    compteur: "nombre_services_locaux" }
]);
const SIRET = /^[0-9]{14}$/;
const SHA = /^[a-f0-9]{64}$/;
const ID = /^FRONTIERE-INST-[A-Z0-9-]+$/;
const MAX_ENTITES = 120_000;
const MAX_SORTIE = 2_000_000;

function empreinte(octets) {
  return createHash("sha256").update(octets).digest("hex");
}
function lireJson(chemin) {
  const contenu = readFileSync(chemin);
  return { valeur: JSON.parse(contenu.toString("utf8")), sha256: empreinte(contenu) };
}
/** Réduire les entités aux champs publics strictement nécessaires. */
export function qualifierRattachement(siret, candidates) {
  if (!SIRET.test(siret) || !Array.isArray(candidates)) {
    throw new Error("Candidats institutionnels invalides.");
  }
  const tries = [...candidates].sort((a, b) => a.id.localeCompare(b.id));
  const ids = new Set();
  for (const entite of tries) {
    if (!ID.test(entite?.id) || typeof entite?.nom !== "string" ||
        entite.nom.length > 350 || !entite.nom.trim() ||
        !["dila_roae", "dila_annuaire_local"].includes(entite?.source_id) ||
        !["ACTIF", "INCONNU", "TRANSFORME", "FUSIONNE", "SUPPRIME"].includes(entite?.etat) ||
        ids.has(entite.id)) {
      throw new Error("Identité institutionnelle incohérente.");
    }
    ids.add(entite.id);
  }
  let statut = "sans_correspondance_dans_les_archives_dila";
  if (tries.length > 1) statut = "plusieurs_entites_memes_siret";
  else if (tries.length === 1) {
    statut = tries[0].etat === "ACTIF"
      ? "identifiant_exact_unique_dans_les_archives_dila"
      : "etat_institutionnel_non_actif_ou_inconnu";
  }
  return { siret, statut, candidats: tries };
}

function demanderSirets(extraits) {
  if (!Array.isArray(extraits)) throw new Error("Extraits DECP absents.");
  const resultat = new Set();
  for (const doc of extraits) {
    if (doc?.source !== "decp" || typeof doc.id !== "string") {
      throw new Error("Extrait DECP non conforme.");
    }
    const match = /^([0-9]{14})\/(.{1,100})$/.exec(doc.id);
    if (!match) throw new Error("Référence DECP sans SIRET exact.");
    resultat.add(match[1]);
  }
  return resultat;
}

/** Construire un objet utilisable uniquement pour les SIRET de l'extrait
 * statique réellement publié. Chaque partition officielle est re-hachée.
 */
export function construireRattachements(racine = RACINE, extraits = []) {
  const recherches = demanderSirets(extraits);
  const correspondances = new Map();
  const sources = [];
  for (const source of SOURCES) {
    const { valeur: manifeste, sha256 } = lireJson(join(racine, source.manifeste));
    if (manifeste.source_id && manifeste.source_id !== source.source_id) {
      throw new Error("Source du manifeste incohérente : " + source.code);
    }
    const partitions = manifeste.partitions_entites;
    if (!Array.isArray(partitions) || partitions.length === 0 ||
        partitions.length > 256 || !Number.isSafeInteger(manifeste[source.compteur])) {
      throw new Error("Manifeste d'entités absent ou incorrect : " + source.code);
    }
    let lues = 0;
    const chemins = new Set();
    for (const part of partitions) {
      if (!source.prefixe.test(part?.fichier) || chemins.has(part.fichier) ||
          !Number.isSafeInteger(part.nombre) || part.nombre < 0 ||
          !Number.isSafeInteger(part.octets) || part.octets <= 0 ||
          part.octets > 4_000_000 || !SHA.test(part.sha256)) {
        throw new Error("Partition administrative non conforme : " + source.code);
      }
      chemins.add(part.fichier);
      const octets = readFileSync(join(racine, part.fichier));
      if (octets.length !== part.octets || empreinte(octets) !== part.sha256) {
        throw new Error("Empreinte administrative incompatible : " + part.fichier);
      }
      const lignes = octets.toString("utf8").split("\n").filter(Boolean);
      if (lignes.length !== part.nombre) {
        throw new Error("Décompte administratif incohérent : " + part.fichier);
      }
      lues += lignes.length;
      if (lues > MAX_ENTITES) throw new Error("Référentiel administratif hors limites.");
      for (const ligne of lignes) {
        const entite = JSON.parse(ligne);
        const numero = entite?.identifiants?.siret;
        if (!SIRET.test(numero || "") || !recherches.has(numero)) continue;
        if (!Array.isArray(entite.provenance) ||
            !entite.provenance.some(p => p?.source_id === source.source_id)) {
          throw new Error("Identité institutionnelle sans provenance attendue.");
        }
        const candidats = correspondances.get(numero) || [];
        candidats.push({
          id: entite.id, nom: entite.nom_officiel,
          etat: entite.etat, source_id: source.source_id
        });
        correspondances.set(numero, candidats);
      }
    }
    if (lues !== manifeste[source.compteur]) {
      throw new Error("Référentiel incomplet : " + source.code);
    }
    sources.push({ source_id: source.source_id, manifeste: source.manifeste,
      sha256_manifeste: sha256, entites_lues: lues });
  }

  const rattachements = {};
  const statuts = {};
  for (const siret of [...recherches].sort()) {
    const fiche = qualifierRattachement(siret, correspondances.get(siret) || []);
    statuts[fiche.statut] = (statuts[fiche.statut] || 0) + 1;
    // Les numéros sans correspondance ne sont pas répétés dans le fichier.
    // L'absence d'entrée n'est jamais une preuve d'inexistence juridique.
    if (fiche.candidats.length) rattachements[siret] = fiche;
  }
  const rapport = {
    version: "frontiere-rattachements-acheteurs-dila-v1",
    portee: "siret_exacts_dans_extrait_decp_et_archives_dila",
    verification_juridique_exterieure: false,
    rapprocher_par_nom: false,
    source_achats: "decp_archives_publiees_extrait_statique",
    documents_decp_indexes: extraits.length,
    sirets_decp_distincts: recherches.size,
    statuts: Object.fromEntries(Object.entries(statuts).sort()),
    sources, rattachements
  };
  const contenu = Buffer.from(JSON.stringify(rapport) + "\n");
  if (contenu.length > MAX_SORTIE) {
    throw new Error("Rapprochements trop volumineux pour le site statique.");
  }
  return { rapport, contenu, octets: contenu.length, sha256: empreinte(contenu) };
}
