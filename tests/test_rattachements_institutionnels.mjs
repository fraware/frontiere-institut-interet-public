import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { construireRattachements, qualifierRattachement } from "../scripts/construire_rattachements_institutionnels.mjs";

const BASE = "institutionnel";
const SOURCE = [
  ["roae", "dila_roae", "roae_manifest.json", "roae/roae_00.jsonl", "nombre_services"],
  ["locales", "dila_annuaire_local", "annuaire_local_manifest.json",
    "locales/annuaire_local_000.jsonl", "nombre_services_locaux"]
];
const hacher = buf => createHash("sha256").update(buf).digest("hex");
function ecrire(racine, chemin, texte) {
  const cible = join(racine, chemin);
  mkdirSync(dirname(cible), { recursive: true });
  const brut = Buffer.from(texte);
  writeFileSync(cible, brut);
  return { octets: brut.length, sha256: hacher(brut) };
}
function entite(id, siret, source, statut = "ACTIF") {
  return {
    id: "FRONTIERE-INST-DILA-" + id, nom_officiel: "Institution " + id,
    etat: statut, identifiants: { siret },
    provenance: [{ source_id: source, identifiant_source: id }],
    responsables: [{ nom: "PERSONNE_PRIVEE_A_NE_PAS_PUBLIER" }],
    coordonnees: [{ email: "prive@example.fr" }]
  };
}
function preparer(roae, locaux) {
  const racine = mkdtempSync(join(tmpdir(), "frontiere-rattachements-"));
  for (const [i, groupe] of [roae, locaux].entries()) {
    const [dossier, source, nomManifeste, sousChemin, compteur] = SOURCE[i];
    const chemin = BASE + "/entites/" + sousChemin;
    const octets = ecrire(racine, chemin, groupe.map(x => JSON.stringify(x)).join("\n") + "\n");
    ecrire(racine, BASE + "/instantanes/" + nomManifeste, JSON.stringify({
      source_id: source, [compteur]: groupe.length,
      partitions_entites: [{ fichier: chemin, nombre: groupe.length, ...octets }]
    }));
  }
  return racine;
}
function decp(...sirets) {
  return sirets.map((s, i) => ({ source: "decp", id: s + "/MARCHE-" + i }));
}

test("une seule entité active et un même SIRET déclaré : relation documentaire", () => {
  const siret = "12345678900012", autre = "98765432100012";
  const racine = preparer(
    [entite("ROAE-1", siret, "dila_roae")],
    [entite("LOCAL-2", autre, "dila_annuaire_local")]
  );
  try {
    const a = construireRattachements(racine, decp(siret, autre, "00000000000000"));
    const b = construireRattachements(racine, decp(siret, autre, "00000000000000"));
    assert.deepEqual(a.contenu, b.contenu);
    assert.equal(a.sha256, hacher(a.contenu));
    assert.equal(a.rapport.sirets_decp_distincts, 3);
    assert.equal(a.rapport.statut, undefined);
    assert.equal(a.rapport.rattachements[siret].statut,
      "identifiant_exact_unique_dans_les_archives_dila");
    assert.equal(a.rapport.rattachements[autre].candidats[0].source_id, "dila_annuaire_local");
    assert.equal(a.rapport.rattachements["00000000000000"], undefined);
    assert.equal(a.rapport.statuts.sans_correspondance_dans_les_archives_dila, 1);
    assert.ok(!a.contenu.toString("utf8").includes("PERSONNE_PRIVEE"));
    assert.ok(!a.contenu.toString("utf8").includes("prive@example.fr"));
    assert.equal(a.rapport.verification_juridique_exterieure, false);
  } finally { rmSync(racine, { recursive: true, force: true }); }
});

test("plusieurs entités au même SIRET ne sont jamais fusionnées", () => {
  const numero = "21590271900016";
  const racine = preparer(
    [entite("ROAE-1", numero, "dila_roae")],
    [entite("LOCAL-2", numero, "dila_annuaire_local")]
  );
  try {
    const resultat = construireRattachements(racine, decp(numero)).rapport.rattachements[numero];
    assert.equal(resultat.statut, "plusieurs_entites_memes_siret");
    assert.equal(resultat.candidats.length, 2);
    assert.notEqual(resultat.candidats[0].id, resultat.candidats[1].id);
  } finally { rmSync(racine, { recursive: true, force: true }); }
});

test("une entité retirée ne reçoit pas le statut actif", () => {
  const numero = "21590271900016";
  const resultat = qualifierRattachement(numero, [
    { id: "FRONTIERE-INST-DILA-ROAE-1", nom: "Ancien établissement",
      source_id: "dila_roae", etat: "SUPPRIME" }
  ]);
  assert.equal(resultat.statut, "etat_institutionnel_non_actif_ou_inconnu");
});

test("les documents invalides et candidats dupliqués sont refusés", () => {
  assert.throws(() => qualifierRattachement("inconnu", []), /invalides/);
  const x = { id: "FRONTIERE-INST-DILA-ROAE-1", nom: "École", source_id: "dila_roae", etat: "ACTIF" };
  assert.throws(() => qualifierRattachement("21590271900016", [x, x]), /incohérente/);
  const racine = preparer([entite("ROAE-1", "21590271900016", "dila_roae")], []);
  try {
    assert.throws(() => construireRattachements(racine,
      [{ source: "boamp", id: "21590271900016/42" }]), /DECP non conforme/);
    assert.throws(() => construireRattachements(racine,
      [{ source: "decp", id: "ABCD/42" }]), /SIRET exact/);
    const file = join(racine, BASE, "entites/roae/roae_00.jsonl");
    writeFileSync(file, readFileSync(file, "utf8").replace("Institution", "InstitutiOn"));
    assert.throws(() => construireRattachements(racine, decp("21590271900016")),
      /Empreinte administrative/);
  } finally { rmSync(racine, { recursive: true, force: true }); }
});
