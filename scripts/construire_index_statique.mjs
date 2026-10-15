/**
 * Produire un extrait documentaire consultable dans un site statique gratuit.
 *
 * Index délibérément borné. Provenances conservées, aucun contact personnel,
 * aucune affirmation de couverture intégrale ou de fraîcheur continue.
 * Fonctionne sous Node 20+ sans dépendance ni connexion réseau.
 */
import { createHash } from "node:crypto";
import { createReadStream, readFileSync, writeFileSync, mkdirSync, statSync } from "node:fs";
import { createInterface } from "node:readline";
import { dirname, join, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

export const PLAFONDS = Object.freeze({ boamp: 700, emplois: 700, decp: 500 });
export const OCTETS_MAX = 2_000_000;
const RACINE = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const DEPOT = "https://github.com/fraware/frontiere-institut-interet-public/blob/main/";
const SOURCE_EMPLOIS = "https://www.data.gouv.fr/datasets/les-offres-diffusees-sur-choisir-le-service-public/";
const SOURCE_BOAMP = "https://boamp-datadila.opendatasoft.com/explore/dataset/boamp/";
const SOURCE_DECP = "https://www.data.gouv.fr/datasets/api-decp/";

function verifier(affirmation, explication) {
  if (!affirmation) throw new Error(explication);
}
function charger(racine, chemin, max = 8_000_000) {
  const p = join(racine, chemin);
  const taille = statSync(p).size;
  verifier(taille > 0 && taille <= max, "Fichier absent, vide ou volumineux : " + chemin);
  const brut = readFileSync(p);
  let donnees;
  try {
    donnees = JSON.parse(brut.toString("utf8"));
  } catch (e) {
    throw new Error("JSON source non lisible : " + chemin + " (" + e.name + ")");
  }
  return { donnees, empreinte: createHash("sha256").update(brut).digest("hex") };
}
function texte(x, max = 250) {
  if (typeof x !== "string") return "";
  return x.replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max);
}
function dateISO(x) {
  if (typeof x !== "string") return "";
  const iso = /^(\d{4}-\d{2}-\d{2})/.exec(x);
  const fr = /^(\d{2})\/(\d{2})\/(\d{4})(?:$|\s)/.exec(x);
  const valeur = iso ? iso[1] : fr ? fr[3] + "-" + fr[2] + "-" + fr[1] : "";
  if (!valeur) return "";
  const date = new Date(valeur + "T00:00:00Z");
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === valeur ? valeur : "";
}
function urlAdmise(valeur, origine) {
  try {
    const u = new URL(valeur);
    if (u.protocol === "https:" && (u.hostname === "boamp.fr" || u.hostname.endsWith(".boamp.fr"))) return u.href;
  } catch { /* référence du producteur absente */ }
  return origine;
}
function cheminArchive(x) {
  verifier(/^[a-z0-9_./-]+$/i.test(x) && !x.includes(".."), "Chemin de provenance non admis.");
  return DEPOT + x.split("/").map(encodeURIComponent).join("/");
}
function ordonner(a, b) {
  return b.date.localeCompare(a.date) || a.source.localeCompare(b.source) || a.id.localeCompare(b.id);
}
function limiter(lignes, plafond) {
  const vus = new Map();
  for (const doc of lignes) {
    if (!doc || !doc.id || !doc.date || !doc.titre) continue;
    const precedent = vus.get(doc.id);
    if (!precedent || ordonner(doc, precedent) < 0) vus.set(doc.id, doc);
  }
  return [...vus.values()].sort(ordonner).slice(0, plafond);
}

export function indexerBoamp(racine, maximum = PLAFONDS.boamp) {
  const chemin = "institutionnel/besoins_publics/annonces_boamp.json";
  const { donnees, empreinte } = charger(racine, chemin);
  verifier(donnees?.version === "avis-boamp-v1" && Array.isArray(donnees.annonces), "Format BOAMP inattendu.");
  const lignes = donnees.annonces.map(x => {
    if (!x || typeof x !== "object" || !texte(x.id, 160)) return null;
    return {
      source: "boamp", id: texte(x.id, 160), titre: texte(x.objet, 450),
      organisme: texte(x.acheteur, 220), date: dateISO(x.date_parution),
      localisation: "", code: texte(x.categorie_marche, 70),
      lien: urlAdmise(x.avis, SOURCE_BOAMP),
      provenance: chemin, cle_provenance: texte(x.id, 160)
    };
  });
  return { extraits: limiter(lignes, maximum), total_candidats: donnees.annonces.length,
           origine: chemin, sha256: empreinte };
}

async function hacherFichier(fichier) {
  const hash = createHash("sha256");
  for await (const bloc of createReadStream(fichier, { highWaterMark: 1 << 20 })) hash.update(bloc);
  return hash.digest("hex");
}
function resserrer(candidats, maximum) {
  return limiter(candidats, maximum);
}
export async function indexerEmplois(racine, maximum = PLAFONDS.emplois) {
  const manifestePath = "institutionnel/besoins_publics/manifest_offres_postes.json";
  const { donnees: manifeste, empreinte } = charger(racine, manifestePath);
  verifier(manifeste.version === "emplois-publics-extraits-v1", "Manifeste CSP incompatible.");
  const partitions = manifeste.empreintes_partitions;
  verifier(partitions && Object.keys(partitions).length === 16, "Partitions CSP attendues manquantes.");
  let candidats = [];
  let lus = 0;
  for (const fichier of Object.keys(partitions).sort()) {
    verifier(/^lot_[0-9a-f]{2}\.jsonl$/.test(fichier), "Nom de partition CSP non admis.");
    const chemin = "institutionnel/besoins_publics/offres_postes/" + fichier;
    const absolu = join(racine, chemin);
    verifier(statSync(absolu).size <= 40_000_000, "Partition CSP trop volumineuse.");
    const courant = await hacherFichier(absolu);
    verifier(courant === partitions[fichier], "Empreinte CSP incompatible : " + fichier);
    const lecteur = createInterface({ input: createReadStream(absolu, { encoding: "utf8" }), crlfDelay: Infinity });
    let numeroLigne = 0;
    for await (const ligne of lecteur) {
      numeroLigne++;
      if (!ligne.trim()) continue;
      verifier(ligne.length <= 24_000, "Ligne CSP hors plafond.");
      let item;
      try {
        item = JSON.parse(ligne);
      } catch (e) {
        throw new Error("Partition CSP non lisible : " + fichier + " à la ligne " +
          numeroLigne + " (" + e.name + ")");
      }
      lus++;
      const reference = texte(item.reference, 180);
      const titre = texte(item.intitule, 300);
      const date = dateISO(item.publication_debut) || dateISO(item.premiere_publication) || dateISO(item.date_vacance);
      if (!reference || !titre || !date) continue;
      candidats.push({
        source: "emplois", id: reference, titre, organisme: texte(item.organisme || item.employeur, 200),
        date, localisation: texte(item.localisation || item.lieu_affectation, 170),
        code: texte(item.metier, 110), lien: SOURCE_EMPLOIS,
        provenance: chemin, cle_provenance: texte(item.cle_enregistrement, 64)
      });
      // Sélection des annonces les plus récentes sans matérialiser 268 000 offres en mémoire.
      if (candidats.length >= 3000) candidats = resserrer(candidats, maximum * 2);
    }
  }
  verifier(lus === manifeste.offres_distinctes, "Comptage des variantes CSP incompatible.");
  return { extraits: resserrer(candidats, maximum),
           total_candidats: lus, origine: manifestePath, sha256: empreinte };
}
export function indexerDecp(racine, maximum = PLAFONDS.decp) {
  const chemins = [
    "institutionnel/decp/sonde_aife_json.json",
    "institutionnel/decp/lot_dgfip_xml.json",
  ];
  let lignes = [], lus = 0, empreintes = [];
  for (const chemin of chemins) {
    const { donnees, empreinte } = charger(racine, chemin);
    // AIFE stocke les notices directement ; DGFiP regroupe les observations
    // par fichier XML officiel dans un tableau "fichiers".
    const lots = Array.isArray(donnees?.marches_extraits)
      ? [{ id: "", marches_extraits: donnees.marches_extraits }]
      : Array.isArray(donnees?.fichiers) ? donnees.fichiers : null;
    verifier(lots !== null && lots.every(x => x && Array.isArray(x.marches_extraits)),
      "Relevé DECP sans notices : " + chemin);
    empreintes.push({ chemin, sha256: empreinte });
    for (const lot of lots) {
      lus += lot.marches_extraits.length;
      for (const x of lot.marches_extraits) {
      if (!x || typeof x !== "object") continue;
      const siret = texte(x.acheteur_siret, 14), id = texte(x.id_marche, 100);
      if (!/^\d{14}$/.test(siret) || !id) continue;
      lignes.push({
        source: "decp", id: siret + "/" + id,
        titre: texte(x.objet, 420), organisme: "Acheteur SIRET " + siret,
        date: dateISO(x.date_notification) || dateISO(x.date_publication_declaree),
        localisation: "", code: texte(x.code_cpv, 50),
        lien: chemin === chemins[0] ? SOURCE_DECP :
          "https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-transmises-via-le-pes-marche-depuis-2024",
        provenance: chemin, cle_provenance: texte(lot.id, 40) ? texte(lot.id, 40) + "/" + id : id
      });
      }
    }
  }
  return { extraits: limiter(lignes, maximum), total_candidats: lus, origines: empreintes };
}

export async function construire(racine = RACINE) {
  const boamp = indexerBoamp(racine);
  const emplois = await indexerEmplois(racine);
  const decp = indexerDecp(racine);
  const resultats = [...boamp.extraits, ...emplois.extraits, ...decp.extraits].sort(ordonner);
  const document = {
    version: "frontiere-index-public-borne-v1",
    portee: "echantillon_documentaire_non_exhaustif",
    recherche_temps_reel: false,
    // GitHub Actions fournit GITHUB_SHA ; Render expose RENDER_GIT_COMMIT.
    // Ne jamais fabriquer une référence immuable si elle est indisponible.
    revision_sources: /^[0-9a-f]{40}$/i.test(process.env.RENDER_GIT_COMMIT || process.env.GITHUB_SHA || "")
      ? (process.env.RENDER_GIT_COMMIT || process.env.GITHUB_SHA).toLowerCase() : null,
    provenance_revisionnee: /^[0-9a-f]{40}$/i.test(process.env.RENDER_GIT_COMMIT || process.env.GITHUB_SHA || ""),
    sources: {
      boamp: { retenus: boamp.extraits.length, notices_fichier: boamp.total_candidats,
               empreinte_fichier: boamp.sha256, fichier: boamp.origine },
      emplois: { retenus: emplois.extraits.length, variantes_fichier: emplois.total_candidats,
                 empreinte_manifeste: emplois.sha256, fichier: emplois.origine },
      decp: { retenus: decp.extraits.length, notices_fichiers: decp.total_candidats,
              fichiers: decp.origines }
    },
    limites: {
      boamp: PLAFONDS.boamp, emplois: PLAFONDS.emplois, decp: PLAFONDS.decp,
      interpretation: "Sélection bornée des documents les plus récents parmi les sources archivées. Ni recensement national ni suivi en temps réel. Les contrats attribués DECP ne sont pas des consultations ouvertes."
    },
    documents: resultats
  };
  const buffer = Buffer.from(JSON.stringify(document) + "\n", "utf8");
  verifier(buffer.length <= OCTETS_MAX, "Index statique supérieur au plafond de 2 Mo.");
  return buffer;
}

async function main() {
  const params = process.argv.slice(2);
  const racineIndex = params.indexOf("--racine");
  const sortieIndex = params.indexOf("--sortie");
  const racine = racineIndex < 0 ? RACINE : resolve(params[racineIndex + 1] || "");
  const sortie = sortieIndex < 0 ? join(racine, "site_frontiere/recherche-index.json")
    : resolve(params[sortieIndex + 1] || "");
  const data = await construire(racine);
  mkdirSync(dirname(sortie), { recursive: true });
  writeFileSync(sortie, data);
  const index = JSON.parse(data);
  console.log(JSON.stringify({
    statut: "construit", octets: data.length,
    documents: index.documents.length,
    par_source: Object.fromEntries(Object.entries(index.sources).map(([k, v]) => [k, v.retenus]))
  }));
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(e => {
    console.error("Index FRONTIÈRE non publié : " + e.message);
    process.exitCode = 1;
  });
}
