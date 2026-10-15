/** Résolution documentaire exacte de l'acheteur d'un marché DECP.
 *
 * L'identifiant de l'index est construit côté serveur depuis
 * acheteur_siret + "/" + id_marche. Il s'agit d'un SIRET déclaré dans
 * une notice contractuelle, non d'une identité juridique revérifiée.
 * Ne jamais déduire ce SIRET d'un libellé de nom, d'un avis BOAMP ou
 * d'une offre d'emploi.
 */
export function siretAdmissible(valeur) {
  return typeof valeur === "string" && /^[0-9]{14}$/.test(valeur);
}

export function siretAcheteur(document) {
  if (document?.source !== "decp" || typeof document.id !== "string") return null;
  const resultat = /^([0-9]{14})\/(.{1,100})$/.exec(document.id);
  return resultat ? resultat[1] : null;
}

export function appartientAuMemeAcheteur(document, siret) {
  return siretAdmissible(siret) && siretAcheteur(document) === siret;
}

/** Ordonner par date documentaire décroissante, puis identifiant stable. */
export function ordreChronologique(a, b) {
  const da = typeof a?.date === "string" ? a.date : "";
  const db = typeof b?.date === "string" ? b.date : "";
  const ida = typeof a?.id === "string" ? a.id : "";
  const idb = typeof b?.id === "string" ? b.id : "";
  return db.localeCompare(da) || ida.localeCompare(idb);
}
