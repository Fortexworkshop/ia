#!/usr/bin/env bash
# Cree les comptes MQTT (mots de passe aleatoires) et le fichier de mots de passe Mosquitto.
# Usage (Git Bash) : ./scripts/gen-mqtt-users.sh
# Resultat : mosquitto/config/passwd (hache) et mqtt-users.env (en clair, NON commite)
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."

gen() { head -c 18 /dev/urandom | base64 | tr -d '/+='; }
ESP_PASSWORD="$(gen)"
SERVEUR_PASSWORD="$(gen)"

rm -f mosquitto/config/passwd
docker run --rm -v "$(pwd -W 2>/dev/null || pwd)/mosquitto/config:/cfg" eclipse-mosquitto:2 sh -c "
  mosquitto_passwd -b -c /cfg/passwd esp8266 '${ESP_PASSWORD}' &&
  mosquitto_passwd -b /cfg/passwd serveur '${SERVEUR_PASSWORD}' &&
  chmod 0700 /cfg/passwd && chown 1883:1883 /cfg/passwd"

cat > mqtt-users.env <<ENV
# Comptes MQTT (a copier dans include/config.h de l'ESP8266 et dans le .env du depot ia)
ESP_MQTT_USER=esp8266
ESP_MQTT_PASSWORD=${ESP_PASSWORD}
SENTINEL_MQTT_USER=serveur
SENTINEL_MQTT_PASSWORD=${SERVEUR_PASSWORD}
ENV
echo "Comptes crees : esp8266, serveur. Mots de passe dans mqtt-users.env (ne pas commiter)."
