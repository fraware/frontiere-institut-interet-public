/** Index documentaire étendu, découpé par source, année et lots bornés.
 * Aucun serveur, aucune dépendance, aucune collecte lors de la consultation.
 */
import { createHash } from "node:crypto";
import { mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { indexerBoamp, indexerEmplois, indexerDecp } from "./construire_index_statique.mjs";

const RACINE = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPARTITION = Object.freeze({ boamp: 5000, emplois: 5000, decp: 5000 });
const TAILLE_LOT = 700;
const MAX_OCTETS = 1_000_000;
const SHA = process.env.RENDER_GIT_COMMIT || process.env.GITHUB_SHA || "";
const revision = /^[a-f0-9]{40}$/i.test(SHA) ? SHA.toLowerCase() : null;

function ordre(a, b) {
  return b.date.localeCompare(a.date) || a.id.localeCompare(b.id);
}
function fichierLot(source, annee, index) {
  if (!/^(boamp|emplois|decp)$/.test(source) || !/^\d{4}$/.test(annee) ||
      !Number.isInteger(index) || index < 1 || index > 1000) {
    throw new Error("Chemin de partition invalide.");
  }
  return "part-" + source + "-" + annee + "-" + String(index).padStart(3, "0") + ".json";
}
export function partitionner(lignes) {
  const g = new Map();
  for (const d of lignes) {
    if (!d || !/^(boamp|emplois|decp)$/.test(d.source) ||
        !/^\d{4}-\d{2}-\d{2}$/.test(d.date || "") ||
        typeof d.id !== "string") throw new Error("Document de partition invalide.");
    const annee = d.date.slice(0, 4);
    const cle = d.source + "/" + annee;
    if (!g.has(cle)) g.set(cle, []);
    g.get(cle).push(d);
  }
  const fragments = [];
  for (const cle of [...g.keys()].sort()) {
    const [source, annee] = cle.split("/");
    const docs = g.get(cle).sort(ordre);
    for (let i = 0; i < docs.length; i += TAILLE_LOT) {
      const lot = docs.slice(i, i + TAILLE_LOT);
      const nom = fichierLot(source, annee, Math.floor(i / TAILLE_LOT) + 1);
      const brut = Buffer.from(JSON.stringify(lot) + "\n", "utf8");
      if (brut.length > MAX_OCTETS) throw new Error("Partition JSON trop volumineuse : " + nom);
      fragments.push({
        nom, source, annee, documents: lot.length,
        octets: brut.length,
        sha256: createHash("sha256").update(brut).digest("hex"),
        contenu: brut
      });
    }
  }
  return fragments;
}
export async function construirePartitions(racine = RACINE) {
  const [boamp, emplois, decp] = await Promise.all([
    Promise.resolve(indexerBoamp(racine, REPARTITION.boamp)),
    indexerEmplois(racine, REPARTITION.emplois),
    Promise.resolve(indexerDecp(racine, REPARTITION.decp))
  ]);
  const fichiers = partitionner([...boamp.extraits, ...emplois.extraits, ...decp.extraits]);
  const dossier = join(racine, "site_frontiere", "partitions");
  mkdirSync(dossier, { recursive: true });
  const ancien = readdirSync(dossier).filter(s => /^part-(boamp|emplois|decp)-\d{4}-\d{3}\.json$/.test(s));
  // Les fichiers de chaque nouvelle publication sont déterministes ;
  // éliminer les partitions périmées qui ne correspondent plus au manifeste.
  const noms = new Set(fichiers.map(f => f.nom));
  for (const nom of ancien) if (!noms.has(nom)) rmSync(join(dossier, nom));
  for (const f of fichiers) writeFileSync(join(dossier, f.nom), f.contenu);
  const manifeste = {
    version: "frontiere-partitions-v1",
    portee: "extrait_etendu_non_exhaustif",
    revision_sources: revision,
    mise_a_jour_temps_reel: false,
    limite_par_source: REPARTITION,
    originaux: {
      boamp: boamp.total_candidats,
      emplois: emplois.total_candidats,
      decp: decp.total_candidats,
    },
    partitions: fichiers.map(({ nom, source, annee, documents, octets, sha256 }) =>
      ({ fichier: nom, source, annee, documents, octets, sha256 })
    )
  };
  // Écrire le manifeste en dernier : aucun catalogue ne décrit un fragment absent.
  writeFileSync(join(dossier, "manifeste.json"), JSON.stringify(manifeste) + "\n");
  return manifeste;
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  construirePartitions().then(manifeste => {
    console.log(JSON.stringify({
      resultat: "construit", partitions: manifeste.partitions.length,
      documents: manifeste.partitions.reduce((n, p) => n + p.documents, 0),
      par_source: manifeste.limite_par_source,
    }));
  }).catch(error => {
    console.error("Index étendu non publié : " + error.message);
    process.exitCode = 1;
  });
}
