import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { construireAvisCorrobores, projeterAvisCorrobores } from
  "../scripts/construire_avis_boamp_corrobores.mjs";

const SOURCE = "institutionnel/besoins_publics/correspondances_siret_boamp_decp_17.json";
const TEMOIN = "institutionnel/besoins_publics/correspondances_siret_boamp_decp_17.sha256";
const SHA = "6dbdd44379ddbc48f2d46f59ae410653613ca880a431a38b716d4a9f7ec544d7";
const IDENTITES = [
  ["25-94670", "21060027600013", 5],
  ["26-62030", "18002002600019", 1]
];
const h = bytes => createHash("sha256").update(bytes).digest("hex");
const lireSource = () => JSON.parse(readFileSync(SOURCE, "utf8"));

test("les deux avis corroborés proviennent de l'enquête immuable de 17 avis", () => {
  const { publication, contenu, octets, sha256 } = construireAvisCorrobores();
  assert.equal(sha256, h(contenu));
  assert.equal(octets, contenu.length);
  assert.equal(publication.population_avis_etudies, 17);
  assert.equal(publication.population_sirets_distincts, 16);
  assert.equal(publication.nombre_avis_corroborees, 2);
  assert.equal(publication.contrats_communs_demonstres, 0);
  assert.equal(publication.extrait_decp_public_couvert, false);
  assert.equal(publication.sha256_registre_source, SHA);
  assert.deepEqual(publication.avis.map(x => [
    x.avis_boamp, x.acheteur_siret, x.identites_marches_decp_dans_archives
  ]), IDENTITES);
  assert.equal(JSON.stringify(publication).includes("denomination_publique"), false);
});

test("une conclusion excessive ou une preuve absente est refusée", () => {
  const cas = [
    a => { a.contrats_communs_demonstres = 1; },
    a => { a.aucune_identite_de_contrat_deduite = false; },
    a => { a.nombre_avis_avec_siret_egal_a_un_acheteur_decp = 3; },
    a => { a.observations[0].identite_contrat_decp_demonstree = true; },
    a => { a.observations[0].preuves.sha256_reponse_boamp = "erroné"; },
    a => { a.observations[0].siret_etablissement_exact_dans_api = false; },
    a => { a.observations[0].siret_acheteur_sans_schema_dans_avis = "nom"; },
    a => { a.observations[1].avis_boamp = a.observations[0].avis_boamp; },
    a => { a.observations.pop(); }
  ];
  for (const modifier of cas) {
    const rapport = lireSource();
    modifier(rapport);
    assert.throws(() => projeterAvisCorrobores(rapport, SHA),
      /Avis BOAMP corroborés/, "Mutation non refusée");
  }
  assert.throws(() => projeterAvisCorrobores(lireSource(), "a".repeat(64)),
    /empreinte d'origine inconnue/);
});

test("la moindre modification des octets archivés bloque la publication", () => {
  const racine = mkdtempSync(join(tmpdir(), "frontiere-avis-verifies-"));
  try {
    for (const chemin of [SOURCE, TEMOIN]) {
      const cible = join(racine, chemin);
      mkdirSync(dirname(cible), { recursive: true });
      writeFileSync(cible, readFileSync(chemin));
    }
    assert.equal(construireAvisCorrobores(racine).publication.avis.length, 2);
    const source = join(racine, SOURCE);
    const original = readFileSync(source, "utf8");
    writeFileSync(source, original.replace('"nombre_avis": 17', '"nombre_avis": 18'));
    assert.throws(() => construireAvisCorrobores(racine),
      /contenu du registre altéré/);
  } finally {
    rmSync(racine, { recursive: true, force: true });
  }
});
