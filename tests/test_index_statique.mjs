import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { createHash } from "node:crypto";
import { construire, PLAFONDS, OCTETS_MAX, metadonneesDates } from "../scripts/construire_index_statique.mjs";

function ecrire(racine, chemin, valeur) {
  const file = join(racine, chemin);
  mkdirSync(dirname(file), { recursive: true });
  const bytes = Buffer.isBuffer(valeur) ? valeur : Buffer.from(typeof valeur === "string" ? valeur : JSON.stringify(valeur));
  writeFileSync(file, bytes);
  return createHash("sha256").update(bytes).digest("hex");
}
function preparer() {
  const racine = mkdtempSync(join(tmpdir(), "frontiere-statique-"));
  const boampPath = "institutionnel/besoins_publics/annonces_boamp.json";
  const emploisBase = "institutionnel/besoins_publics/offres_postes/";
  const decpPath = "institutionnel/decp/";
  ecrire(racine, boampPath, {
    version: "avis-boamp-v1",
    annonces: [
      { id: "B001", objet: "Équipements scientifiques",
        acheteur: "Université publique", date_parution: "2026-10-10",
        avis: "https://www.boamp.fr/pages/avis/B001", categorie_marche: "SERVICES" },
      { id: "B002", objet: "<script>alert(1)</script>",
        acheteur: "Ville de Test", date_parution: "2026-09-03",
        avis: "javascript:alert(1)" },
      { id: "B003", objet: "Sans publication datée", date_parution: "" }
    ]
  });
  const empreintes_partitions = {};
  for (let i = 0; i < 16; i++) {
    const name = "lot_" + i.toString(16).padStart(2, "0") + ".jsonl";
    const lignes = [
      { reference: "EMP" + i + "A", intitule: "Responsable informatique",
        organisme: "Centre public", publication_debut: i === 0 ? "10/10/2026" : "2026-10-0" + (i % 9 + 1),
        localisation: "Lyon", metier: "Informatique", cle_enregistrement: "k" + i },
      { reference: "EMP" + i + "B", intitule: "Ingénieure de recherche",
        employeur: "Laboratoire public", premiere_publication: "2026-08-01",
        localisation: "Paris", metier: "Recherche", cle_enregistrement: "z" + i }
    ];
    empreintes_partitions[name] = ecrire(racine, emploisBase + name,
      lignes.map(x => JSON.stringify(x)).join("\n") + "\n");
  }
  ecrire(racine, "institutionnel/besoins_publics/manifest_offres_postes.json", {
    version: "emplois-publics-extraits-v1",
    offres_distinctes: 32, empreintes_partitions
  });
  const avis = {
    acheteur_siret: "12345678901234", id_marche: "M-1",
    objet: "Maintenance et vérification scientifique",
    date_notification: "2026-09-20", code_cpv: "72000000-5"
  };
  ecrire(racine, decpPath + "sonde_aife_json.json", { marches_extraits: [avis] });
  ecrire(racine, decpPath + "lot_dgfip_xml.json", { fichiers: [
    { id: "xml-2026-01", marches_extraits: [
      { ...avis, id_marche: "M-2", date_notification: "2026-08-12" },
      { ...avis, id_marche: "M-1", date_notification: "2026-09-18" }
    ] }
  ] });
  return racine;
}
async function dansFixture(fn) {
  const racine = preparer();
  try { return await fn(racine); } finally { rmSync(racine, { recursive: true, force: true }); }
}

test("index complet borné, déterministe, sans doublons ni données personnelles", async () => {
  await dansFixture(async racine => {
    const a = await construire(racine);
    const b = await construire(racine);
    assert.deepEqual(a, b);
    assert.ok(a.length < OCTETS_MAX);
    const doc = JSON.parse(a);
    assert.equal(doc.recherche_temps_reel, false);
    assert.equal(doc.portee, "echantillon_documentaire_non_exhaustif");
    assert.equal(doc.documents.length, 2 + 32 + 2);
    assert.equal(doc.sources.emplois.variantes_fichier, 32);
    assert.equal(doc.sources.decp.notices_fichiers, 3);
    assert.deepEqual(doc.documents.filter(x => x.source === "decp").map(x => x.id).sort(),
      ["12345678901234/M-1", "12345678901234/M-2"]);
    assert.equal(doc.documents.find(x => x.id === "B002").lien,
      "https://boamp-datadila.opendatasoft.com/explore/dataset/boamp/");
    assert.ok(doc.documents.every(x => x.provenance.startsWith("institutionnel/")));
    assert.equal(doc.documents.find(x => x.id === "EMP0A").date, "2026-10-10");
    assert.equal(doc.documents.find(x => x.id === "EMP1A").lien,
      "https://www.data.gouv.fr/datasets/les-offres-diffusees-sur-choisir-le-service-public/");
    assert.ok(!a.toString().includes("contact_personnel"));
    assert.equal(Object.keys(PLAFONDS).length, 3);
  });
});

test("une partition CSP altérée bloque toute publication", async () => {
  await dansFixture(async racine => {
    const path = join(racine, "institutionnel/besoins_publics/offres_postes/lot_00.jsonl");
    writeFileSync(path, '{"reference":"modifie"}\n');
    await assert.rejects(() => construire(racine), /Empreinte CSP incompatible/);
  });
});

test("décompte de variantes incompatible bloque la publication", async () => {
  await dansFixture(async racine => {
    const file = join(racine, "institutionnel/besoins_publics/manifest_offres_postes.json");
    const value = JSON.parse(readFileSync(file, "utf8"));
    value.offres_distinctes = 999;
    writeFileSync(file, JSON.stringify(value));
    await assert.rejects(() => construire(racine), /Comptage/);
  });
});

test("relevé DECP sans notices interdit une couverture simulée", async () => {
  await dansFixture(async racine => {
    writeFileSync(join(racine, "institutionnel/decp/lot_dgfip_xml.json"), '{"informations":{}}');
    await assert.rejects(() => construire(racine), /Relevé DECP sans notices/);
  });
});

test("les bornes restent explicites et sont vérifiées", () => {
  assert.ok(PLAFONDS.boamp <= 1000);
  assert.ok(PLAFONDS.emplois <= 1000);
  assert.ok(PLAFONDS.decp <= 1000);
  assert.ok(OCTETS_MAX <= 2_000_000);
});

test("la révision Git attestée est immuable et absente si inconnue", async () => {
  await dansFixture(async racine => {
    const avant = process.env.GITHUB_SHA;
    const rend = process.env.RENDER_GIT_COMMIT;
    try {
      delete process.env.RENDER_GIT_COMMIT;
      process.env.GITHUB_SHA = "a".repeat(40);
      let x = JSON.parse(await construire(racine));
      assert.equal(x.revision_sources, "a".repeat(40));
      assert.equal(x.provenance_revisionnee, true);
      process.env.GITHUB_SHA = "branche-main";
      x = JSON.parse(await construire(racine));
      assert.equal(x.revision_sources, null);
      assert.equal(x.provenance_revisionnee, false);
    } finally {
      if (avant === undefined) delete process.env.GITHUB_SHA;
      else process.env.GITHUB_SHA = avant;
      if (rend === undefined) delete process.env.RENDER_GIT_COMMIT;
      else process.env.RENDER_GIT_COMMIT = rend;
    }
  });
});

test("distinguer indexation, publication et observation avec dates sources absentes explicites", () => {
  const root = preparer();
  try {
    const m = metadonneesDates(root, "a".repeat(40), "2026-10-15T16:40:00Z");
    assert.equal(m.version, "frontiere-dates-index-v1");
    assert.equal(m.indexation_site_le, "2026-10-15T16:40:00Z");
    assert.equal(m.revision_sources, "a".repeat(40));
    assert.equal(m.etats_des_archives.decp.date_acquisition_de_chaque_marche, null);
    assert.equal(m.etats_des_archives.boamp.dernier_controle_archive_le, null);
    assert.match(m.nature_des_dates_documentaires.decp, /notification/);
    assert.notEqual(m.nature_des_dates_documentaires.decp, "Date d'acquisition");
  } finally { rmSync(root, { recursive:true, force:true }); }
});
