# Dossiers de consultation référencés dans les vingt avis BOAMP — priorités de vérification

**État du 13 octobre 2026.** Ce registre se rattache au [relevé officiel de vingt avis](https://github.com/fraware/frontiere-institut-interet-public/actions/runs/38487483105), issu de 17 avis indépendants et de trois avis explicitement liés. Le rapport a dénombré 22 mentions documentaires, réparties entre douze adresses distinctes. Les 14 mentions classées « adresse de dossier référencée » ne représentent **pas** quatorze dossiers distincts : plusieurs lots et avis répètent une même adresse.

## Hiérarchie de contrôle

Les avis présentant une **relation explicite avec un avis antérieur** et une **adresse de dossier spécifique** forment la première priorité, car la chaîne d'avis et le numéro de consultation peuvent être comparés sans rechercher opportunément une correspondance contractuelle.

| Priorité | Avis | Identifiant documentaire | Adresse déclarée et portée de la preuve |
| --- | --- | --- | --- |
| 1 | AP-HP, 26-25119 et 26-35619 | Consultation PLACE `2957868` | [Adresse officielle citée par les deux avis](https://www.marches-publics.gouv.fr/?page=Entreprise.EntrepriseAdvancedSearch&AllCons&id=2957868&orgAcronyme=x7c). Même référence de procédure `25-39_IT` dans les deux formulaires. Adresse commune démontrée, pièces et contrat non obtenus |
| 2 | Le Grand Charolais, 25-122175 lié à 26-37752 | Annonce de consultation `1127625` | [Publication citée dans l'avis initial](https://cc-legrandcharolais.e-marchespublics.com/pack/annonce_marche_public_31312_1127625.html). Deux mentions d'une adresse unique dans l'avis initial ; l'attribution ne comporte pas cette adresse. Lien explicite entre avis, contenu du dossier non obtenu |
| 3 | Hôpital Novo, 25-141009 | Domaine général PLACE | L'avis mentionne uniquement le portail : pas de dossier individualisé identifiable par ce champ |
| 4 | DGAC, 26-59281 et 26-60102 | Domaine général `marches-publics.gouv.fr` | La relation d'avis et la référence interne `2026-SNARP-001` concordent ; le domaine seul ne permet pas d'identifier un dossier public |

Les autres dossiers comportant un identifiant de consultation suffisamment précis sont examinés ensuite, sans relation d'avis antérieur démontrée dans le champ étudié.

| Avis | Référence spécifique observable | Publication citée |
| --- | --- | --- |
| Commune d'Apatou, 25-112128 | Annonce `1122739` répétée dans cinq lots | [Annonce de marché](https://commune-apatou.e-marchespublics.com/pack/annonce_marche_public_12507_1122739.html) |
| GIE Expertise et Support, 26-17037 | `PCSLID=CSL_2026_RCHwC1j9QS` | [Dossier Achatpublic](https://www.achatpublic.com/sdm/ent/gen/ent_detail.do?PCSLID=CSL_2026_RCHwC1j9QS) |
| Musée du quai Branly, 26-11703 | Consultation PLACE `2918652` | [Consultation citée](https://www.marches-publics.gouv.fr/?page=Entreprise.EntrepriseAdvancedSearch&AllCons&id=2918652&orgAcronyme=f5j) |
| Caisse des dépôts, 26-62030 | Consultation `3024354` | [Consultation citée](https://www.marches-publics.gouv.fr/entreprise/consultation/3024354?orgAcronyme=s2d) |
| Université de Rouen Normandie, 26-56522 | `PCSLID=CSL_2026_cPvEPm0k3N` | [Dossier Achatpublic](https://www.achatpublic.com/sdm/ent/gen/ent_detail.do?PCSLID=CSL_2026_cPvEPm0k3N) |

L'avis de la Société d'exploitation de la tour Eiffel `25-94249` contient une adresse générique Achatpublic et une URL de réécriture Safelinks, derrière laquelle une référence `PCSLID` est encodée. Cette dernière **n'a pas été suivie**. Toute extraction future doit enregistrer séparément l'URL d'origine et la destination proposée, vérifier son domaine et refuser les requêtes automatiques de connexion ou d'accès protégé.

## Vérifications de consultation extérieure

Lors d'une consultation publique exploratoire des liens cités, l'outil de lecture n'a pas obtenu de contenu documentaire exploitable pour la page du Grand Charolais ni pour celles de l'AP-HP et d'Apatou. Les résultats observés sont une page comportant uniquement le marqueur technique `EMP_PUBLIC_URL` pour le Grand Charolais et des erreurs d'accès pour les deux autres pages. **Ce résultat ne démontre ni que les documents sont inexistants, ni que les dossiers sont inaccessibles depuis un navigateur autorisé.** Il n'atteste aucun retrait de DCE.

Aucun PDF de cahier des charges, aucune annexe, aucun acte contractuel signé ni procès-verbal de réception n'ont été obtenus ou certifiés dans ce passage. Les statuts demeurent `contenu_documentaire_obtenu=false`, `acte_contractuel_verifie=false`, `premiere_contribution_utile_mesuree=false`.

## Protocole du prochain examen de pièce

Pour chaque adresse individuelle, conserver la référence BOAMP, le rôle du champ eForms, le numéro de procédure, le numéro de lot et les identifiants URL. La recherche doit ensuite relever la page d'annonce accessible publiquement, l'éventuelle adresse explicite d'une pièce et les conditions d'accès, en distinguant quatre issues : pièce publique obtenue et empreinte contrôlée ; page publique confirmée sans pièce reçue ; retrait sous authentification ou conditions particulières ; statut de consultation indéterminé.

Une pièce publique téléchargée n'est attribuable à l'avis que si son contenu ou ses métadonnées fournissent une concordance suffisamment spécifique avec la procédure ou le lot. La simple présence d'une URL sur un portail, le nom de domaine commun, une proximité de dates ou une référence interne réutilisée ne valident pas un contrat. Les données personnelles, les informations confidentielles et les espaces à authentification restent exclus.

## Incidence sur l'hypothèse FRONTIÈRE

Même une consultation authentique et datée renseigne surtout **la définition publique du besoin**. Elle ne révèle pas automatiquement la disponibilité des spécialistes, la qualité des candidatures, les causes d'un délai, l'appropriation interne ou la date de première contribution utile. Les cas positifs comme les cas négatifs doivent être comparés aux dispositifs publics existants et aux solutions de substitution.

Le projet fondateur v0.3 demeure explicitement *proposé, non adopté*. Aucune enquête documentaire ne vaut décision de constituer l'Institut, mandat administratif, décision de recrutement ou conclusion de déficit de compétence.
