# Firmware SENTINEL-X (ESP8266 NodeMCU v2)

Projet PlatformIO en C++ (framework Arduino) : `firmware/sentinel-x/`.

## Rôle

- Lit le DHT22 (température, humidité), le MQ-2 (gaz) et le PIR (présence) **toutes les 2 s**.
- Publie les mesures en **MQTTS** (TLS, port 8883, compte `esp8266`) sur `sentinel/<id>/sensors` :
  `{"node_id","temperature","humidity","gas","pir","ip","rssi"}`.
- Écoute `sentinel/<id>/commands` : `{"actuator":"buzzer"|"led","state":true|false}`, envoyé
  depuis le dashboard.
- Publie `online` ou `offline` sur `sentinel/<id>/status`. Le message `offline` est le testament
  MQTT (LWT) : le broker le publie si le boîtier disparaît.
- **Écran OLED** : nom, adresse IP, état Wi-Fi et MQTT (« OK (TLS) »), mesures, statut d'alarme.
- **LEDs** : verte = lien serveur OK ; rouge = commande du superviseur, alarme gaz locale, ou
  clignotement si le lien est coupé.
- **Garde-fou local** : buzzer et LED rouge si le gaz dépasse 700 (ADC), même sans serveur.

## Câblage

| Composant | Broche du composant | NodeMCU | GPIO |
|---|---|---|---|
| DHT22 | DATA (+ résistance 10 kΩ vers 3V3) | **D4** | 2 |
| DHT22 | VCC / GND | 3V3 / GND | |
| MQ-2 | AO (**pont diviseur** : 5 V vers 3,3 V max, par exemple 10 kΩ + 20 kΩ) | **A0** | ADC |
| MQ-2 | VCC / GND | VIN (5 V) / GND | |
| PIR HC-SR501 | OUT | **D5** | 14 |
| PIR HC-SR501 | VCC / GND | VIN (5 V) / GND | |
| Buzzer piézo | + (− vers GND) | **D6** | 12 |
| LED verte | anode (via résistance 220 Ω) | **D7** | 13 |
| LED rouge | anode (via résistance 220 Ω) | **D8** | 15 |
| OLED SSD1306 0,96" I2C | SDA / SCL | **D2** / **D1** | 4 / 5 |
| OLED SSD1306 | VCC / GND | 3V3 / GND | |

> L'entrée A0 du NodeMCU accepte au maximum 3,3 V : ne pas brancher la sortie 5 V du MQ-2 en direct.
> Le MQ-2 a besoin d'environ 1 minute de préchauffage avant des valeurs stables.

## Configuration et flash

1. Générer les certificats et les comptes MQTT dans le dépôt infra (`scripts/gen-certs.sh`,
   `scripts/gen-mqtt-users.sh`).
2. Copier `include/sentinel_config.example.h` en `include/sentinel_config.h` (ignoré par Git).
   Y renseigner le Wi-Fi de la table, l'IP du PC serveur, le mot de passe `esp8266` (fichier
   `mqtt-users.env`) et le contenu de `certs/ca.crt`.
3. Compiler et flasher :

```powershell
cd firmware\sentinel-x
..\..\.venv\Scripts\pio run -t upload
..\..\.venv\Scripts\pio device monitor
```

`pio device monitor` ouvre le moniteur série à 115200 bauds.

Sans `sentinel_config.h`, le projet compile quand même avec les valeurs d'exemple (avertissement à
la compilation) : utile pour vérifier le code.

**Heure et TLS** : pour valider le certificat, l'ESP8266 a besoin de l'heure. Il essaie NTP ; si
le réseau de la table n'a pas Internet, il utilise l'heure de compilation (`build_epoch.py`). Il
faut donc flasher **après** avoir généré les certificats.

Ressources mesurées à la compilation : RAM 36,8 %, Flash 39,8 %.
