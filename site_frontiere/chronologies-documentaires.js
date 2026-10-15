/** Chronologie documentaire bornée aux publications d'un même SIRET.
 *
 * Les entrées BOAMP proviennent exclusivement des deux avis corroborés d'un
 * tirage de 17 avis. Les entrées DECP proviennent uniquement des partitions
 * statiques vérifiées. Coïncidence de SIRET et ordre des dates ne prouvent
 * ni contrat commun, ni projet commun, ni relation causale, ni besoin ouvert.
 *
 * Aucun appel réseau ou effet sur le DOM dans ce module.
 */
const SIRET = /^[0-9]{14}$/;
const MARCHE = /^([0-9]{14})\/(.{1,100})$/;
const AVIS = /^[0-9]{2}-[0-9]{2,8}$/;
const SHA = /^[0-9a-f]{64}$/;

function dateAdmise(valeur) {
  if (typeof valeur !== "string" || !/^20\d{2}-\d{2}-\d{2}$/.test(valeur)) return false;
  const date = new Date(valeur + "T00:00:00Z");
  return Number.isFinite(date.getTime()) &&
    date.toISOString().slice(0, 10) === valeur;
}
function verifier(condition, raison) {
  if (!condition) throw new Error("Chronologie documentaire : " + raison);
}

/** Fusion déterministe de documents attestés, sans créer de relations entre
 * les observations. Refuse les références malformées, étrangères ou répétées.
 * Les métadonnées DECP ne précisent pas si la date est une notification ou
 * une publication déclarée de remplacement.
 *
 * @param {string} siret Identifiant exact utilisé pour filtrer les documents.
 * @param {Array<object>} marches Notices DECP de l'index statique complet.
 * @param {Array<object>} avisCorrobores Extrait BOAMP vérifié cryptographiquement.
 * @returns {{version:string,siret:string,evenements:Array<object>,decomptes:object,
 *   limite_interpretation:string}}
 */
export function construireChronologieDocumentaire(siret, marches, avisCorrobores) {
  verifier(SIRET.test(siret), "SIRET non conforme");
  verifier(Array.isArray(marches) && marches.length <= 5000 &&
    Array.isArray(avisCorrobores) && avisCorrobores.length <= 2,
    "collections non conformes");
  const evenements = [];
  const cles = new Set();
  for (const doc of marches) {
    const id = typeof doc?.id === "string" ? MARCHE.exec(doc.id) : null;
    verifier(doc?.source === "decp" && id?.[1] === siret &&
      dateAdmise(doc.date) && typeof doc.titre === "string" &&
      doc.titre.length > 0 && doc.titre.length <= 420 &&
      typeof doc.provenance === "string" &&
      /^institutionnel\/decp\/[a-z0-9_.-]+\.json$/.test(doc.provenance) &&
      typeof doc.lien === "string", "notice DECP étrangère ou altérée");
    const cle = "decp:" + doc.id;
    verifier(!cles.has(cle), "notice DECP dupliquée");
    cles.add(cle);
    evenements.push({
      cle, source: "decp", date: doc.date, nature_date: "date_documentaire_decp",
      reference: doc.id, titre: doc.titre, provenance: doc.provenance,
      url: doc.lien, identite_contrat_boamp_demonstree: false,
      lien_projet_demonstre: false
    });
  }
  for (const avis of avisCorrobores) {
    verifier(AVIS.test(avis?.avis_boamp || "") && SIRET.test(avis.acheteur_siret) &&
      dateAdmise(avis.date_parution) &&
      Number.isSafeInteger(avis.identites_marches_decp_dans_archives) &&
      avis.identites_marches_decp_dans_archives > 0 &&
      SHA.test(avis.preuve_boamp_sha256 || "") &&
      SHA.test(avis.preuve_administrative_sha256 || ""),
      "avis BOAMP non corroboré");
    if (avis.acheteur_siret !== siret) continue;
    const cle = "boamp:" + avis.avis_boamp;
    verifier(!cles.has(cle), "avis BOAMP dupliqué");
    cles.add(cle);
    evenements.push({
      cle, source: "boamp", date: avis.date_parution,
      nature_date: "parution_avis_boamp", reference: avis.avis_boamp,
      titre: "Avis BOAMP " + avis.avis_boamp,
      provenance: "institutionnel/besoins_publics/correspondances_siret_boamp_decp_17.json",
      preuve_sha256: avis.preuve_boamp_sha256,
      identites_decp_historiques: avis.identites_marches_decp_dans_archives,
      identite_contrat_boamp_demonstree: false,
      lien_projet_demonstre: false
    });
  }
  evenements.sort((a, b) =>
    b.date.localeCompare(a.date) || a.source.localeCompare(b.source) ||
    a.reference.localeCompare(b.reference));
  return {
    version: "frontiere-chronologie-documentaire-v1",
    siret,
    decomptes: {
      documents_decp_index: marches.length,
      avis_boamp_etude: evenements.filter(x => x.source === "boamp").length
    },
    evenements,
    limite_interpretation: "La date DECP est une date de notification ou, à défaut, " +
      "de publication déclarée ; le champ source indexé ne permet pas d'identifier " +
      "laquelle pour chaque notice. Les dates BOAMP sont des dates de parution. " +
      "Leur ordre ne démontre ni lien contractuel, ni succession de phases d'un " +
      "même projet, ni besoin public non satisfait. L'extrait DECP est plafonné " +
      "à 5 000 documents et l'étude BOAMP couvre 17 avis non représentatifs."
  };
}
