"""API FORTEX (FastAPI).

REST
  GET  /health                     etat du backend (base, MQTT)
  POST /api/v1/alerts              reception des alertes (IA, autres briques) - jeton Bearer
  GET  /api/v1/alerts?limit=50     dernieres alertes
  POST /api/v1/alerts/{id}/ack     acquitter une alerte
  GET  /api/v1/readings?limit=60   dernieres mesures capteurs
  GET  /api/v1/devices             statut des boitiers
  POST /api/v1/commands            {actuator: "buzzer"|"led", state: bool} -> MQTT sentinel/<node>/commands
  POST /api/v1/test/{kind}         alerte de test (heat | gas | intrusion) pour la plateforme de test
WebSocket
  /ws                              flux temps reel au format du dashboard (reading, alert, command-ack)

Flux : ESP8266 -MQTT-> backend -> PostgreSQL + WebSocket ; IA -HTTP-> /api/v1/alerts -> idem.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .messages import SafetyAlarm, alert_message, now_ms, parse_sensor_payload, reading_message


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


class Hub:
    """Clients WebSocket du dashboard. broadcast() est appelable depuis n'importe quel thread."""

    def __init__(self):
        self.clients: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    async def _send_all(self, message: dict) -> None:
        text = json.dumps(message, default=str)
        for ws in list(self.clients):
            try:
                await ws.send_text(text)
            except Exception:
                self.clients.discard(ws)

    def broadcast(self, message: dict) -> None:
        if self.loop is None or not self.clients:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self.loop:
            self.loop.create_task(self._send_all(message))
        else:
            asyncio.run_coroutine_threadsafe(self._send_all(message), self.loop)


class Service:
    """Logique metier, independante du transport (MQTT, HTTP)."""

    def __init__(self, store, hub: Hub, watcher: SafetyAlarm | None, publish=None, node_id: str = ""):
        self.store = store
        self.hub = hub
        self.watcher = watcher
        self.publish = publish          # publish(topic, payload_dict) -> bool, None = MQTT absent
        self.node_id = node_id
        self.lock = threading.Lock()
        self.last_reading_at: float | None = None

    def ingest_reading(self, node: str, payload: dict) -> bool:
        reading = parse_sensor_payload(payload)
        if reading is None:
            return False
        with self.lock:
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
        self.hub.broadcast(alert_message({**alert, "id": alert_id}))
        return alert_id

    def command(self, cmd: CommandIn) -> bool:
        node = cmd.node_id or self.node_id
        payload = {"actuator": cmd.actuator, "state": cmd.state}
        delivered = bool(self.publish and self.publish(f"sentinel/{node}/commands", payload))
        self.hub.broadcast({"type": "command-ack", "ts": now_ms(), "cmd": payload, "delivered": delivered})
        return delivered


TEST_ALERTS = {
    "heat": ("TEMPERATURE", "critical", "Test : surchauffe simulee", 45.0, "°C"),
    "gas": ("GAS", "critical", "Test : fuite de gaz simulee", 700.0, ""),
    "intrusion": ("PRESENCE", "warning", "Test : intrusion simulee", 1, ""),
}


def create_app(service: Service, api_token: str = "", cors_origins: list[str] | None = None,
               mqtt_status=lambda: False, on_startup=None, on_shutdown=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app):
        service.hub.loop = asyncio.get_running_loop()
        if on_startup:
            on_startup()
        yield
        if on_shutdown:
            on_shutdown()

    app = FastAPI(title="FORTEX backend", version="1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins or ["*"],
                       allow_methods=["*"], allow_headers=["*"])

    def require_token(authorization: str | None = Header(default=None)):
        if api_token and authorization != f"Bearer {api_token}":
            raise HTTPException(401, "Jeton invalide ou absent")

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

    @app.post("/api/v1/alerts/{alert_id}/ack")
    def ack_alert(alert_id: int):
        if not service.store.acknowledge(alert_id):
            raise HTTPException(404, "Alerte inconnue")
        return {"id": alert_id, "acknowledged": True}

    @app.get("/api/v1/readings")
    def get_readings(limit: int = 60):
        return [reading_message(r, r["ts"]) for r in service.store.recent_readings(min(max(limit, 1), 1000))]

    @app.get("/api/v1/devices")
    def get_devices():
        return service.store.devices()

    @app.post("/api/v1/commands")
    def post_command(cmd: CommandIn):
        return {"delivered": service.command(cmd)}

    @app.post("/api/v1/test/{kind}", status_code=201)
    def test_alert(kind: str):
        if kind not in TEST_ALERTS:
            raise HTTPException(404, f"Test inconnu (choix : {', '.join(TEST_ALERTS)})")
        alert_type, severity, message, value, unit = TEST_ALERTS[kind]
        alert = {"node_id": service.node_id, "source": "test", "type": alert_type, "severity": severity,
                 "message": message, "data": {"value": value, "unit": unit}}
        return {"id": service.ingest_alert(alert)}

    @app.websocket("/ws")
    async def websocket(ws: WebSocket):
        await ws.accept()
        service.hub.clients.add(ws)
        try:
            while True:
                await ws.receive_text()  # le dashboard n'envoie rien ; garde la connexion ouverte
        except WebSocketDisconnect:
            pass
        finally:
            service.hub.clients.discard(ws)

    return app
