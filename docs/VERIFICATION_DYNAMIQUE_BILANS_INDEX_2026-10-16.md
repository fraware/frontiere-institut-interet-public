# Vérification dynamique des bilans intégraux — F-003/F-004

Les index locaux de recrutements et de commande publique possèdent déjà des contrôles d'intégrité sur leurs sources. La procédure principale de vérification comparait toutefois leurs résultats aux nombres **268 102** et **5 196**, inscrits en dur lors des premiers relevés. Une collecte automatique augmentant ces effectifs pouvait ainsi faire échouer une reconstruction correcte.

`scripts/verifier_bilans_index_ci.py` compare maintenant chaque bilan à son manifeste **de la même révision**, avec une vérification indépendante dans chaque tâche GitHub Actions. Les deux tâches n'échangent pas de fichiers temporaires : le bilan CSP est contrôlé dans la tâche CSP, le bilan BOAMP–DECP dans la tâche correspondante. Les identités, variantes et attestations restent des unités différentes.

La comparaison ne prétend pas valider l'exactitude des données du producteur ; les indexeurs existants vérifient les partitions et attestations cryptographiques et les nouvelles vérifications confirment les décomptes publiés dans les bilans. Les références réelles sont toujours cherchées séparément dans la CI. Le rapport transversal de l'issue [537](https://github.com/fraware/frontiere-institut-interet-public/issues/537) demeure à achever, notamment sur le déploiement Render.

Tests : `python -m pytest -q tests/test_verifier_bilans_index_ci.py`. Les tests incluent un changement coordonné de population, un décalage d'un compteur, une valeur de type booléen, un manifeste incomplet et une affirmation de relation contractuelle non établie.

Une limite distincte demeure : d'autres procédures utilisent aussi des nombres historiques fixes, parfois légitimement pour un échantillon préenregistré. Leur actualisation demande un examen spécifique afin de ne pas modifier silencieusement un protocole de recherche.
