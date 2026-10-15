#!/bin/sh
set -eu

# Le disque est monté après la construction de l'image Docker.
# Préparer les répertoires sur le volume effectivement monté.
if [ "$FRONTIERE_DONNEES" != "/var/lib/frontiere" ]; then
    echo "FRONTIÈRE : chemin du volume persistant inattendu" >&2
    exit 1
fi
for dossier in \
    "$FRONTIERE_DONNEES" \
    "$FRONTIERE_DONNEES/boamp" \
    "$FRONTIERE_DONNEES/emplois" \
    "$FRONTIERE_DONNEES/decp" \
    "$FRONTIERE_DONNEES/ted" \
    "$FRONTIERE_DONNEES/.amorcage"
do
    mkdir -p "$dossier"
    chown frontiere:frontiere "$dossier"
done

exec gosu frontiere:frontiere python -m app.exploitation_hebergee
