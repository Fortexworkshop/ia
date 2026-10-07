// SENTINEL-X : firmware du boitier ESP8266 (NodeMCU v2)
//
// - Lit DHT22 (temperature, humidite), MQ-2 (gaz) et PIR toutes les 2 s
// - Publie {"node_id","temperature","humidity","gas","pir","ip","rssi"} sur sentinel/<id>/sensors (MQTTS)
// - Ecoute sentinel/<id>/commands : {"actuator":"buzzer"|"led","state":true|false}
// - Statut en ligne / hors ligne (LWT) sur sentinel/<id>/status
// - Ecran OLED : IP, etat Wi-Fi / MQTT, dernieres mesures
// - Garde-fou local : buzzer + LED rouge si le gaz depasse LOCAL_GAS_ALARM,
//   meme sans serveur (le boitier reste utile si le reseau tombe)

#include <Arduino.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <time.h>

#if __has_include("sentinel_config.h")
#include "sentinel_config.h"
#else
#warning "include/sentinel_config.h absent : valeurs d exemple utilisees"
#include "sentinel_config.example.h"
#endif

#if MQTT_USE_TLS
#include <WiFiClientSecureBearSSL.h>
#endif

// --- Brochage (voir firmware/README.md) -----------------------------------
constexpr uint8_t PIN_DHT = D4;        // GPIO2
constexpr uint8_t PIN_PIR = D5;        // GPIO14
constexpr uint8_t PIN_BUZZER = D6;     // GPIO12
constexpr uint8_t PIN_LED_OK = D7;     // GPIO13, LED verte
constexpr uint8_t PIN_LED_ALERT = D8;  // GPIO15, LED rouge
constexpr uint8_t PIN_GAS = A0;        // MQ-2 sortie analogique (via pont diviseur 5 V -> 3,3 V)
// OLED SSD1306 I2C : SDA = D2 (GPIO4), SCL = D1 (GPIO5), adresse 0x3C

constexpr unsigned long PUBLISH_MS = 2000;
constexpr unsigned long RECONNECT_MS = 5000;
constexpr int LOCAL_GAS_ALARM = 700;  // valeur ADC (0-1023)
constexpr unsigned int BUZZER_HZ = 2000;

DHT dht(PIN_DHT, DHT22);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);

#if MQTT_USE_TLS
BearSSL::WiFiClientSecure net;
BearSSL::X509List caCert(MQTT_CA_CERT);
#else
WiFiClient net;
#endif
PubSubClient mqtt(net);

String topicSensors, topicCommands, topicStatus;
bool oledReady = false;
bool buzzerRemote = false, ledRemote = false, buzzerOn = false;
unsigned long lastPublish = 0, lastReconnect = 0;
float lastTemp = NAN, lastHum = NAN;
int lastGas = 0, lastPir = 0;
const char* mqttState = "...";

// --- Actionneurs -------------------------------------------------------------
bool localAlarm() { return lastGas >= LOCAL_GAS_ALARM; }

void applyOutputs() {
  bool buzzer = buzzerRemote || localAlarm();
  if (buzzer != buzzerOn) {
    if (buzzer) tone(PIN_BUZZER, BUZZER_HZ); else noTone(PIN_BUZZER);
    buzzerOn = buzzer;
  }
  bool linkOk = WiFi.status() == WL_CONNECTED && mqtt.connected();
  bool blink = (millis() / 500) % 2;
  digitalWrite(PIN_LED_OK, linkOk ? HIGH : LOW);
  // LED rouge : commande du superviseur, alarme locale, ou clignote si le lien est coupe
  digitalWrite(PIN_LED_ALERT, (ledRemote || localAlarm() || (!linkOk && blink)) ? HIGH : LOW);
}

void onCommand(char* topic, byte* payload, unsigned int length) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, length)) {
    Serial.println(F("[mqtt] commande JSON invalide"));
    return;
  }
  const char* actuator = doc["actuator"] | "";
  bool state = doc["state"] | false;
  if (strcmp(actuator, "buzzer") == 0) buzzerRemote = state;
  else if (strcmp(actuator, "led") == 0) ledRemote = state;
  else return;
  Serial.printf("[mqtt] commande %s -> %s\n", actuator, state ? "ON" : "OFF");
  applyOutputs();
}

// --- Ecran OLED ----------------------------------------------------------------
void drawScreen() {
  if (!oledReady) return;
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(0, 0);
  oled.println(F("SENTINEL-X"));
  oled.print(F("IP ")); oled.println(WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : String("Wi-Fi..."));
  oled.print(F("MQTT ")); oled.println(mqttState);
  oled.drawLine(0, 26, 127, 26, SSD1306_WHITE);
  oled.setCursor(0, 30);
  if (isnan(lastTemp)) oled.println(F("DHT22 : erreur"));
  else oled.printf("T %.1fC  H %.0f%%\n", lastTemp, lastHum);
  oled.printf("Gaz %d  PIR %s\n", lastGas, lastPir ? "OUI" : "non");
  if (localAlarm()) oled.println(F("!! ALARME GAZ !!"));
  else if (buzzerRemote || ledRemote) oled.println(F("Alerte superviseur"));
  else oled.println(F("Statut : normal"));
  oled.display();
}

// --- Reseau --------------------------------------------------------------------
void setupClock() {
#if MQTT_USE_TLS
  // NTP si Internet est joignable, sinon l'heure de compilation (le certificat doit etre valide)
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  unsigned long start = millis();
  while (time(nullptr) < 1700000000 && millis() - start < 3000) delay(100);
  time_t now = time(nullptr);
  if (now < 1700000000) now = BUILD_EPOCH;
  net.setX509Time(now);
  net.setTrustAnchors(&caCert);
  net.setBufferSizes(1024, 1024);  // economise la RAM de l'ESP8266
#endif
}

void connectMqtt() {
  if (mqtt.connected() || WiFi.status() != WL_CONNECTED) return;
  if (millis() - lastReconnect < RECONNECT_MS && lastReconnect != 0) return;
  lastReconnect = millis();
  String clientId = String("esp-") + NODE_ID;
  Serial.printf("[mqtt] connexion a %s:%d ...\n", MQTT_HOST, MQTT_PORT);
  // LWT : le broker publie "offline" si le boitier disparait
  if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD, topicStatus.c_str(), 1, true, "offline")) {
    mqttState = MQTT_USE_TLS ? "OK (TLS)" : "OK";
    mqtt.publish(topicStatus.c_str(), "online", true);
    mqtt.subscribe(topicCommands.c_str(), 1);
    Serial.println(F("[mqtt] connecte"));
  } else {
    mqttState = "echec";
    Serial.printf("[mqtt] echec, code %d\n", mqtt.state());
  }
}

// --- Capteurs ------------------------------------------------------------------
void readAndPublish() {
  lastTemp = dht.readTemperature();
  lastHum = dht.readHumidity();
  lastGas = analogRead(PIN_GAS);
  lastPir = digitalRead(PIN_PIR);

  if (isnan(lastTemp) || isnan(lastHum)) {
    Serial.println(F("[dht] lecture invalide, mesure non publiee"));
    return;
  }
  if (!mqtt.connected()) return;

  JsonDocument doc;
  doc["node_id"] = NODE_ID;
  doc["temperature"] = roundf(lastTemp * 10) / 10;
  doc["humidity"] = roundf(lastHum * 10) / 10;
  doc["gas"] = lastGas;
  doc["pir"] = lastPir;
  doc["ip"] = WiFi.localIP().toString();
  doc["rssi"] = WiFi.RSSI();
  char buffer[256];
  size_t n = serializeJson(doc, buffer);
  mqtt.publish(topicSensors.c_str(), reinterpret_cast<const uint8_t*>(buffer), n, false);
  Serial.println(buffer);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED_OK, OUTPUT);
  pinMode(PIN_LED_ALERT, OUTPUT);
  dht.begin();

  Wire.begin(D2, D1);
  oledReady = oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  if (!oledReady) Serial.println(F("[oled] ecran absent"));

  topicSensors = String("sentinel/") + NODE_ID + "/sensors";
  topicCommands = String("sentinel/") + NODE_ID + "/commands";
  topicStatus = String("sentinel/") + NODE_ID + "/status";

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("\n[wifi] connexion a %s\n", WIFI_SSID);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    drawScreen();
    delay(250);
  }
  if (WiFi.status() == WL_CONNECTED) Serial.printf("[wifi] IP %s\n", WiFi.localIP().toString().c_str());

  setupClock();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onCommand);
  mqtt.setBufferSize(512);
  mqtt.setKeepAlive(15);
}

void loop() {
  connectMqtt();
  mqtt.loop();

  if (millis() - lastPublish >= PUBLISH_MS) {
    lastPublish = millis();
    readAndPublish();
    drawScreen();
  }
  applyOutputs();
}
