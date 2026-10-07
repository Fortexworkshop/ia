// Copier ce fichier en include/sentinel_config.h (ignore par git) et remplir les vraies valeurs.
#pragma once

#define NODE_ID "SENTINEL-X-01"

// Wi-Fi du point d'acces de la table
#define WIFI_SSID "FORTEX-TABLE"
#define WIFI_PASSWORD "change-moi"

// Broker Mosquitto du PC Serveur Local
#define MQTT_HOST "192.168.10.1"
#define MQTT_USE_TLS 1              // 1 = MQTTS (port 8883), 0 = MQTT en clair (port 1883, debug)
#define MQTT_PORT 8883
#define MQTT_USER "esp8266"
#define MQTT_PASSWORD "change-moi"

// Certificat de l'autorite (contenu de security/certs/ca.crt), pour verifier le serveur
static const char MQTT_CA_CERT[] PROGMEM = R"CERT(
-----BEGIN CERTIFICATE-----
REMPLACER_PAR_LE_CONTENU_DE_ca.crt
-----END CERTIFICATE-----
)CERT";
