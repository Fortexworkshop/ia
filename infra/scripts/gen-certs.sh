#!/usr/bin/env bash
# Genere l'autorite de certification (CA) et le certificat du broker Mosquitto (MQTTS).
# Usage (Git Bash) : ./scripts/gen-certs.sh [IP_DU_PC_SERVEUR]      (defaut 192.168.10.1)
# Resultat : certs/ca.crt (a distribuer : ESP8266, IA, backend), certs/server.crt, certs/server.key
set -euo pipefail
export MSYS_NO_PATHCONV=1  # Git Bash : ne pas convertir "/CN=..." en chemin Windows

SERVER_IP="${1:-192.168.10.1}"
DAYS=730
cd "$(dirname "$0")/.."
mkdir -p certs
cd certs

if [ ! -f ca.key ]; then
  openssl genrsa -out ca.key 2048
  openssl req -x509 -new -key ca.key -sha256 -days "$DAYS" -out ca.crt \
    -subj "/O=AetherCorp FORTEX/CN=FORTEX Root CA"
fi

# SAN : noms et IP sous lesquels le broker est joint (Docker, PC serveur, ESP8266).
# L'IP est aussi mise en DNS car BearSSL (ESP8266) ne verifie que les noms DNS.
cat > server.ext <<EXT
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:mosquitto,DNS:localhost,DNS:${SERVER_IP},IP:127.0.0.1,IP:${SERVER_IP}
EXT
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/O=AetherCorp FORTEX/CN=${SERVER_IP}"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt \
  -days "$DAYS" -sha256 -extfile server.ext
rm -f server.csr server.ext
chmod 644 server.key  # lisible par l'utilisateur mosquitto du conteneur

echo "Certificats generes dans certs/ pour ${SERVER_IP} :"
openssl x509 -in server.crt -noout -subject -ext subjectAltName
