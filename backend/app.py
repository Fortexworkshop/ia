"""API FORTEX (FastAPI).

REST
  GET  /health                     etat du backend (base, MQTT)
  POST /api/v1/alerts              reception des alertes (IA, autres briques) - jeton Bearer
  GET  /api/v1/alerts?limit=50     dernieres alertes
  POST /api/v1/alerts/{id}/ack     acquitter une alerte
  GET  /api/v1/readings?limit=60   dernieres mesures capteurs
  GET  /api/v1/devices             statut des boitiers
  GET  /api/v1/people              individus de la liste blanche (donnees + visage)
  POST /api/v1/people              ajoute/modifie un individu (jeton) : {name, notes, photo}
  DELETE /api/v1/people/{name}     retire un individu (jeton) : donnees et empreinte faciale
  GET  /api/v1/presence            journal de presence (detections et pointages)
  POST /api/v1/presence            ajoute un evenement (jeton) : {kind, person, message}
  GET  /api/v1/vision              etat du processus de vision (la webcam est exclusive)
  POST /api/v1/vision/start|stop   demarre / arrete la vision (jeton) : libere la camera
  POST /api/v1/commands            {actuator: "buzzer"|"led", state: bool} -> MQTT sentinel/<node>/commands
  POST /api/v1/test/{kind}         alerte de test (heat | gas | intrusion) pour la plateforme de test
WebSocket
  /ws                              flux temps reel au format du dashboard (reading, alert, command-ack)

Flux : ESP8266 -MQTT-> backend -> PostgreSQL + WebSocket ; IA -HTTP-> /api/v1/alerts -> idem.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from .metrics import render as render_metrics
from .messages import SafetyAlarm, alert_message, now_ms, parse_sensor_payload, reading_message
from .people import PeopleStore
from .presence import PresenceLog
from .vision import VisionController

# Journal d'audit (OWASP A09) : qui a fait quelle action sensible, depuis quelle adresse.
# scripts/backend.py l'ecrit dans data/audit.log.
audit_log = logging.getLogger("fortex.audit")


def audit(request: Request | None, action: str, **details) -> None:
    client = request.client.host if request and request.client else "?"
    extra = " ".join(f"{k}={v!r}" for k, v in details.items())
    audit_log.info("%s client=%s %s", action, client, extra)

# En-tetes de securite de l'API (OWASP A02) : pas d'interpretation de type, pas d'integration
# dans un cadre, pas de fuite d'URL, pas de cache des reponses (donnees personnelles).
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class AlertIn(BaseModel):
    node_id: str = "inconnu"
    source: str = "?"
    type: str = Field(min_length=1, max_length=50)
    severity: Literal["info", "warning", "critical"] = "warning"
    message: str = Field(default="", max_length=1000)
    timestamp: str | None = None
    data: dict = Field(default_factory=dict)


class CommandIn(BaseModel):
    actuator: Literal["buzzer", "led"]
    state: bool
    node_id: str | None = None


class PresenceIn(BaseModel):
    kind: Literal["detection", "entree", "pause", "reprise", "sortie"] = "detection"
    person: str = Field(default="", max_length=80)
    ts: str = ""          # horodatage ISO de la source ; vide = heure du backend


class PersonIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    notes: str = Field(default="", max_length=500)
    # data URL ou base64 ; vide = pas de visage a enregistrer. Taille bornee (OWASP A06 : deni de service)
    photo: str = Field(default="", max_length=8_000_000)
    previous: str | None = None  # ancien nom, si l'individu est renomme


class Hub:
    """Clients WebSocket du dashboard. broadcast() est appelable depuis n'importe quel thread."""

    def __init__(self):
        self.clients: set[WebSocket] = set()
        # clients authentifies (code operateur) : seuls a recevoir les donnees personnelles (presence)
        self.operators: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def discard(self, ws: WebSocket) -> None:
        self.clients.discard(ws)
        self.operators.discard(ws)

    async def _send_all(self, message: dict, private: bool = False) -> None:
        text = json.dumps(message, default=str)
        for ws in list(self.operators if private else self.clients):
            try:
                await ws.send_text(text)
            except Exception:
                self.discard(ws)

    def broadcast(self, message: dict, private: bool = False) -> None:
        if self.loop is None or not self.clients:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self.loop:
            self.loop.create_task(self._send_all(message, private))
        else:
            asyncio.run_coroutine_threadsafe(self._send_all(message, private), self.loop)


class Service:
    """Logique metier, independante du transport (MQTT, HTTP)."""

    def __init__(self, store, hub: Hub, watcher: SafetyAlarm | None, publish=None, node_id: str = "",
                 auto_alarm: tuple[str, ...] = ("INTRUSION",)):
        self.store = store
        self.hub = hub
        self.watcher = watcher
        self.publish = publish          # publish(topic, payload_dict) -> bool, None = MQTT absent
        self.node_id = node_id
        self.auto_alarm = auto_alarm  # types d'alerte qui declenchent buzzer + LED du boitier
        self.lock = threading.Lock()
        self.last_reading_at: float | None = None
        # compteurs pour GET /metrics (Prometheus / Grafana)
        self.readings_total = 0
        self.rejected_total = 0
        self.commands_total = 0
        self.alerts_total: dict[tuple[str, str], int] = {}

    def ingest_reading(self, node: str, payload: dict) -> bool:
        reading = parse_sensor_payload(payload)
        if reading is None:
            self.rejected_total += 1
            return False
        with self.lock:
            self.readings_total += 1
            when = self.store.add_reading(node, reading)
            self.store.touch_status(node, payload.get("ip"))
            self.last_reading_at = time.time()
        self.hub.broadcast(reading_message(reading, when))
        for alert in (self.watcher.check(node, reading) if self.watcher else []):
            self.ingest_alert(alert)
        return True

    def ingest_alert(self, alert: dict) -> int:
        with self.lock:
            alert_id = self.store.add_alert(alert)
            key = (str(alert.get("type", "?")).upper(), str(alert.get("source", "?")))
            self.alerts_total[key] = self.alerts_total.get(key, 0) + 1
        self.hub.broadcast(alert_message({**alert, "id": alert_id}))
        if str(alert.get("type", "")).upper() in self.auto_alarm:
            # Alarme physique : le superviseur la coupe depuis le dashboard (boutons Buzzer / LED)
            node = alert.get("node_id") or self.node_id
            self.command(CommandIn(actuator="buzzer", state=True, node_id=node))
            self.command(CommandIn(actuator="led", state=True, node_id=node))
        return alert_id

    def command(self, cmd: CommandIn) -> bool:
        node = cmd.node_id or self.node_id
        payload = {"actuator": cmd.actuator, "state": cmd.state}
        delivered = bool(self.publish and self.publish(f"sentinel/{node}/commands", payload))
        self.commands_total += 1
        self.hub.broadcast({"type": "command-ack", "ts": now_ms(), "cmd": payload, "delivered": delivered})
        return delivered


TEST_ALERTS = {
    "heat": ("TEMPERATURE", "critical", "Test : surchauffe simulee", 45.0, "°C"),
    "gas": ("GAS", "critical", "Test : fuite de gaz simulee", 700.0, ""),
    "intrusion": ("PRESENCE", "warning", "Test : intrusion simulee", 1, ""),
}


def create_app(service: Service, api_token: str = "", cors_origins: list[str] | None = None,
               mqtt_status=lambda: False, on_startup=None, on_shutdown=None,
               people: PeopleStore | None = None,
               presence: PresenceLog | None = None,
               vision: VisionController | None = None, mosquitto_log=None,
               dashboard_token: str = "") -> FastAPI:
    """api_token : machines (IA -> alertes, presence), tous les droits.
    dashboard_token : operateur du dashboard (individus, vision, buzzer/LED), sans pouvoir emettre
    d'alertes : il est lisible dans le navigateur, il ne doit donc pas valoir le jeton de l'IA."""
    @asynccontextmanager
    async def lifespan(_app):
        service.hub.loop = asyncio.get_running_loop()
        if on_startup:
            on_startup()
        yield
        if on_shutdown:
            on_shutdown()

    app = FastAPI(title="FORTEX backend", version="1.0", lifespan=lifespan)
    # Aucune origine par defaut (OWASP A02) : seules les origines configurees lisent l'API
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins or [],
                       allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    def require_token(authorization: str | None = Header(default=None)):
        if api_token and authorization != f"Bearer {api_token}":
            raise HTTPException(401, "Jeton invalide ou absent")

    operator_tokens = {t for t in (api_token, dashboard_token) if t}

    def require_operator(authorization: str | None = Header(default=None)):
        accepted = {f"Bearer {t}" for t in operator_tokens}
        if accepted and authorization not in accepted:
            raise HTTPException(401, "Jeton operateur invalide ou absent")

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics():
        """Format Prometheus : supervision et MCO dans Grafana (infra/grafana)."""
        return render_metrics(service, mqtt_status(), vision.running if vision else None, mosquitto_log)

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "database": service.store.backend,
            "database_ok": service.store.healthy(),
            "mqtt_connected": mqtt_status(),
            "last_reading_age_s": None if service.last_reading_at is None
            else round(time.time() - service.last_reading_at, 1),
            "websocket_clients": len(service.hub.clients),
        }

    @app.post("/api/v1/alerts", status_code=201, dependencies=[Depends(require_token)])
    def post_alert(alert: AlertIn):
        return {"id": service.ingest_alert(alert.model_dump())}

    @app.get("/api/v1/alerts")
    def get_alerts(limit: int = 50):
        return [alert_message(a) | {"acknowledged": a.get("acknowledged", False)}
                for a in service.store.recent_alerts(min(max(limit, 1), 500))]

    @app.post("/api/v1/alerts/{alert_id}/ack", dependencies=[Depends(require_operator)])
    def ack_alert(alert_id: int, request: Request):
        if not service.store.acknowledge(alert_id):
            raise HTTPException(404, "Alerte inconnue")
        audit(request, "ACK", alert=alert_id)
        service.hub.broadcast({"type": "ack", "id": alert_id})  # les autres postes se mettent a jour
        return {"id": alert_id, "acknowledged": True}

    @app.get("/api/v1/readings")
    def get_readings(limit: int = 60):
        return [reading_message(r, r["ts"]) for r in service.store.recent_readings(min(max(limit, 1), 1000))]

    @app.get("/api/v1/devices")
    def get_devices():
        return service.store.devices()

    @app.post("/api/v1/commands", dependencies=[Depends(require_operator)])
    def post_command(cmd: CommandIn, request: Request):
        audit(request, "COMMAND", actuator=cmd.actuator, state=cmd.state)
        return {"delivered": service.command(cmd)}

    @app.get("/api/v1/people", dependencies=[Depends(require_operator)])  # donnees personnelles
    def get_people():
        """Liste blanche : individus declares dans le dashboard et empreintes enregistrees en CLI."""
        return people.list() if people else []

    @app.post("/api/v1/people", status_code=201, dependencies=[Depends(require_operator)])
    def post_person(person: PersonIn, request: Request):
        if people is None:
            raise HTTPException(503, "Liste des individus indisponible sur ce backend")
        audit(request, "PERSON_SAVE", name=person.name, previous=person.previous or "", photo=bool(person.photo))
        try:
            return people.save(person.name, person.notes, person.photo, previous=person.previous or "")
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    @app.delete("/api/v1/people/{name}", dependencies=[Depends(require_operator)])
    def delete_person(name: str, request: Request):
        """Droit a l'effacement (RGPD) : retire les donnees et l'empreinte faciale."""
        audit(request, "PERSON_DELETE", name=name)
        if people is None or not people.delete(name):
            raise HTTPException(404, "individu inconnu")
        return {"deleted": name}

    @app.get("/api/v1/presence", dependencies=[Depends(require_operator)])  # donnees personnelles
    def get_presence(limit: int = 50):
        """Journal de presence, du plus recent au plus ancien."""
        return presence.recent(limit) if presence else []

    @app.post("/api/v1/presence", status_code=201, dependencies=[Depends(require_token)])
    def post_presence(event: PresenceIn):
        if presence is None:
            raise HTTPException(503, "Journal de presence indisponible sur ce backend")
        try:
            saved = presence.add(event.kind, event.person, event.ts)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        service.hub.broadcast({"type": "presence", **saved}, private=True)
        return saved

    @app.get("/api/v1/vision")
    def get_vision():
        """Etat du script de vision. La webcam est exclusive : l'arreter la libere."""
        return vision.status() if vision else {"running": False, "available": False}

    @app.post("/api/v1/vision/start", dependencies=[Depends(require_operator)])
    def start_vision(request: Request):
        audit(request, "VISION_START")
        if vision is None:
            raise HTTPException(503, "Pilotage de la vision indisponible sur ce backend")
        return vision.start()

    @app.post("/api/v1/vision/stop", dependencies=[Depends(require_operator)])
    def stop_vision(request: Request):
        audit(request, "VISION_STOP")
        if vision is None:
            raise HTTPException(503, "Pilotage de la vision indisponible sur ce backend")
        return vision.stop()

    @app.post("/api/v1/test/{kind}", status_code=201, dependencies=[Depends(require_operator)])
    def test_alert(kind: str, request: Request):
        if kind not in TEST_ALERTS:
            raise HTTPException(404, f"Test inconnu (choix : {', '.join(TEST_ALERTS)})")
        audit(request, "EXERCISE", kind=kind)
        alert_type, severity, message, value, unit = TEST_ALERTS[kind]
        alert = {"node_id": service.node_id, "source": "test", "type": alert_type, "severity": severity,
                 "message": message, "data": {"value": value, "unit": unit}}
        return {"id": service.ingest_alert(alert)}

    @app.websocket("/ws")
    async def websocket(ws: WebSocket):
        """Mesures et alertes pour tous ; presence (donnees personnelles) pour les operateurs.
        Authentification par un premier message {"type": "auth", "token": ...} : le code ne passe
        pas dans l'URL (journaux, historique). Sans jeton configure (developpement), tous sont operateurs."""
        await ws.accept()
        service.hub.clients.add(ws)
        if not operator_tokens:
            service.hub.operators.add(ws)
        try:
            while True:
                try:
                    msg = json.loads(await ws.receive_text())
                except ValueError:
                    continue  # message illisible : ignore (OWASP A10)
                if isinstance(msg, dict) and msg.get("type") == "auth":
                    ok = not operator_tokens or msg.get("token") in operator_tokens
                    (service.hub.operators.add if ok else service.hub.operators.discard)(ws)
                    if not ok:
                        audit(None, "WS_AUTH_FAILED", client=ws.client.host if ws.client else "?")
                    await ws.send_json({"type": "auth", "ok": ok})
        except WebSocketDisconnect:
            pass
        finally:
            service.hub.discard(ws)

    return app
