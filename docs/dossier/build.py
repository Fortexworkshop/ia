"""Genere le dossier technique SENTINEL-X et le poster, en deux fichiers separes.

Le dossier (A4) assemble les sources du depot :
  - les schemas reseau et de cablage, dessines ici en SVG ;
  - docs/SECURITE.md (matrice de securite et durcissement) ;
  - docs/IA.md (documentation de l'intelligence artificielle).

Le poster est un document autonome, compose en A3 portrait (son format de base) : il
ne partage plus le PDF du dossier, qui reste donc entierement en A4.

Usage :
    python docs/dossier/build.py [--group 3] [--out ../../rendus]

Produit dans le dossier de sortie :
    Workshop2026-M1-G<n>-Dossier.pdf   (A4)
    Workshop2026-M1-G<n>-Poster.pdf    (A3 portrait)
"""

from __future__ import annotations

import argparse
import base64
import re
import subprocess
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent          # Fortex/
DOCS = ROOT / "docs"

FONT = "system-ui, 'Segoe UI', 'DejaVu Sans', sans-serif"
MONO = "'DejaVu Sans Mono', ui-monospace, monospace"

# Charte graphique FORTEX (dev/dashboard/src/tokens.css), theme clair : le dossier est imprime,
# le poster reste en theme sombre comme l'application. Aucune valeur en dur ailleurs.
INK, MUTED, FAINT = "#141820", "#48515e", "#5b6574"
LINE, DIVIDER = "#6f7a89", "#dde1e7"
ACCENT, ACCENT_STRONG = "#1d5bc6", "#123f8c"
OK, WARN, CRIT, STALE = "#17703f", "#8a5300", "#b3261e", "#5b3cc4"
OK_BG, WARN_BG, CRIT_BG = "#e3f4ea", "#fdf1dc", "#fbe9e8"
SURFACE, SURFACE2, SURFACE3 = "#ffffff", "#f6f7f9", "#e8ebef"

# Theme sombre de la charte, pour le poster.
D_BG, D_SURFACE, D_SURFACE2, D_SURFACE3 = "#0d1117", "#151b23", "#1b222c", "#242c38"
D_TEXT, D_MUTED, D_FAINT = "#e6e9ee", "#a4adba", "#8a94a3"
D_BORDER, D_DIVIDER = "#6b7686", "#2a323e"
D_ACCENT, D_ACCENT_STRONG = "#79aaf7", "#a8c8fb"
D_CRITICAL, D_WARNING, D_OK, D_STALE = "#ff6b66", "#f2b440", "#5fcf95", "#c3a6ff"

# Logo FORTEX : bastion en plan (le « fort ») autour d'un capteur — dev/dashboard/src/components/Icon.jsx
LOGO_PATH = "M16 2 6 6v4H2l4 6-4 6h4v4l10 4 10-4v-4h4l-4-6 4-6h-4V6L16 2z"


def logo_svg(x: float, y: float, size: float, stroke: str, accent: str) -> str:
    """Logo FORTEX a la position (x, y), a l'echelle demandee. Geometrie identique a l'application."""
    k = size / 32
    return (f'<g transform="translate({x} {y}) scale({k})">'
            f'<path d="{LOGO_PATH}" fill="none" stroke="{stroke}" stroke-width="2" stroke-linejoin="round"/>'
            f'<circle cx="16" cy="16" r="4" fill="{accent}"/>'
            f'<circle cx="16" cy="16" r="8" fill="none" stroke="{accent}" stroke-width="1.5" '
            f'stroke-dasharray="3 3"/></g>')


# --------------------------------------------------------------------------- Markdown

def _inline(text: str) -> str:
    """Gras, italique, code en ligne et liens d'un sous-ensemble volontairement restreint."""
    text = escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)


def _table(rows: list[str]) -> str:
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    body = [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]
    head = "".join(f"<th>{_inline(c)}</th>" for c in header)
    lines = ["<table>", f"<thead><tr>{head}</tr></thead>", "<tbody>"]
    for row in body:
        lines.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


def md_to_html(text: str) -> str:
    """Convertit le Markdown des documents sources (sous-ensemble documente)."""
    out: list[str] = []
    lines = text.splitlines()
    i, paragraph, quote = 0, [], []

    def flush_paragraph() -> None:
        if paragraph:
            out.append("<p>" + _inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def flush_quote() -> None:
        if quote:
            out.append("<blockquote>" + _inline(" ".join(quote)) + "</blockquote>")
            quote.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph(); flush_quote()
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            i += 1
            out.append("<pre>" + escape("\n".join(block)) + "</pre>")
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= set("|-: "):
            flush_paragraph(); flush_quote()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i]); i += 1
            out.append(_table(rows))
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph(); flush_quote()
            level = len(heading.group(1))
            # Les titres des sources demarrent a 1 : decales d'un niveau dans le dossier.
            out.append(f"<h{min(level + 1, 6)}>{_inline(heading.group(2))}</h{min(level + 1, 6)}>")
            i += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            quote.append(stripped.lstrip(">").strip())
            i += 1
            continue

        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            flush_paragraph(); flush_quote()
            ordered = bool(re.match(r"^\d+\.\s+", stripped))
            items = []
            while i < len(lines) and (re.match(r"^[-*]\s+", lines[i].strip()) or re.match(r"^\d+\.\s+", lines[i].strip())):
                items.append(re.sub(r"^([-*]|\d+\.)\s+", "", lines[i].strip()))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(item)}</li>" for item in items) + f"</{tag}>")
            continue

        if stripped in {"---", "***", "___"}:
            flush_paragraph(); flush_quote()
            out.append("<hr />")
            i += 1
            continue

        if not stripped:
            flush_paragraph(); flush_quote()
            i += 1
            continue

        paragraph.append(stripped)
        i += 1

    flush_paragraph(); flush_quote()
    return "\n".join(out)


def md_section(path: Path) -> str:
    """Rend un document source en HTML, sans son titre de niveau 1 (fourni par le dossier)."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^#\s+.*$", "", text, count=1, flags=re.M)
    return md_to_html(text)


# --------------------------------------------------------------------------- SVG

def svg(width: int, height: int, body: str, title: str, theme: str = "light") -> str:
    ink, muted, accent, surface, surface2, outline = (
        (D_TEXT, D_MUTED, D_ACCENT, D_SURFACE, D_SURFACE2, D_DIVIDER) if theme == "dark"
        else (INK, MUTED, ACCENT, SURFACE, SURFACE2, DIVIDER))
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="{FONT}">\n<title>{escape(title)}</title>\n'
        "<defs>"
        f'<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{ink}"/></marker>'
        f'<marker id="arrow-accent" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{accent}"/></marker>'
        "<style>"
        f".t{{fill:{ink};font-size:15px}} .s{{fill:{muted};font-size:13px}} .m{{fill:{ink};font-family:{MONO};font-size:12px}}"
        f".h{{fill:{ink};font-size:17px;font-weight:700}} .k{{fill:{accent};font-size:12px;font-weight:700;letter-spacing:1px}}"
        f".box{{fill:{surface};stroke:{outline};stroke-width:1.5}} .box2{{fill:{surface2};stroke:{outline};stroke-width:1.5}}"
        f".wire{{stroke:{ink};stroke-width:1.6;fill:none}} .dash{{stroke:{muted};stroke-width:1.4;stroke-dasharray:6 5;fill:none}}"
        f".accent{{stroke:{accent};stroke-width:1.6;fill:none}}"
        "</style></defs>\n" + body + "\n</svg>"
    )


def logo_inline(size: int, stroke: str, accent: str) -> str:
    """Logo FORTEX pret a poser dans du HTML (meme trace que l'application)."""
    return (f'<svg viewBox="0 0 32 32" width="{size}" height="{size}" role="img" aria-label="FORTEX">'
            f'{logo_svg(0, 0, 32, stroke, accent)}</svg>')


def _r(x, y, w, h, classes="box", rx=10) -> str:
    return f'<rect class="{classes}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>'


def _t(x, y, text, classes="t") -> str:
    return f'<text class="{classes}" x="{x}" y="{y}">{escape(text)}</text>'


def network_diagram() -> str:
    """Sous-reseau, flux et ports. Disposition etudiee pour qu'aucune liaison ne traverse une tuile :
    la rangee haute porte les services applicatifs (dans l'ordre des flux), la rangee basse les
    conteneurs de donnees ; le WebSocket emprunte le couloir libre entre les deux."""
    parts = [
        _r(30, 30, 1240, 700, "box", 18),
        _t(56, 66, "SOUS-RÉSEAU DE TABLE — 192.168.10.0/24 (isolé)", "k"),
        _t(56, 90, "Aucun routage vers les autres tables : point d'accès Wi-Fi dédié au PC serveur.", "s"),
        # Boitier
        _r(70, 140, 300, 470, "box2", 14),
        _t(92, 176, "Boîtier SENTINEL-X", "h"),
        _t(92, 200, "ESP8266 NodeMCU v2", "s"),
        _t(92, 222, "192.168.10.42", "m"),
        _t(92, 268, "DHT22 — température, humidité", "s"),
        _t(92, 292, "MQ-2 — gaz et fumées", "s"),
        _t(92, 316, "PIR HC-SR501 — présence", "s"),
        _t(92, 340, "Écran OLED I2C — statut", "s"),
        _t(92, 364, "Buzzer + LEDs — alarme locale", "s"),
        _t(92, 410, "Publie les mesures toutes les 2 s", "s"),
        _t(92, 434, "Alarme locale si gaz > 700 (ADC)", "s"),
        _t(92, 480, "Boîtier virtuel : scripts/virtual_esp.py", "s"),
        _t(92, 504, "mêmes topics, même compte MQTTS,", "s"),
        _t(92, 526, "mêmes commandes (matériel non distribué)", "s"),
        _t(92, 560, "Firmware C++ : firmware/sentinel-x", "s"),
        # PC serveur
        _r(500, 110, 740, 560, "box2", 14),
        _t(524, 148, "PC Serveur Local — Windows 11 + Docker Desktop", "h"),
        _t(524, 172, "192.168.10.1 — webcam USB branchée en direct", "s"),
    ]

    # Rangee haute, dans l'ordre des flux : broker, backend, vision, dashboard
    row1 = [
        (524, "Mosquitto 2", ["MQTTS 8883", "2 comptes, ACL", "anonyme refusé"]),
        (701, "Backend", ["FastAPI", "REST + WebSocket", "port 8080"]),
        (878, "Vision", ["YOLOv8n", "flux MJPEG", "port 8081"]),
        (1055, "Dashboard", ["React", "courbes, alarmes", "port 5173"]),
    ]
    for x, title, lines in row1:
        parts += [_r(x, 196, 160, 92, "box", 10), _t(x + 14, 222, title, "t")]
        for index, line in enumerate(lines):
            parts.append(_t(x + 14, 244 + index * 20, line, "s"))

    # Rangee basse : conteneurs de donnees et de supervision
    parts += [
        _r(524, 316, 692, 330, "box", 12),
        _t(548, 348, "DOCKER COMPOSE — infra/docker-compose.yml", "k"),
    ]
    row2 = [
        (548, "PostgreSQL 16", ["mesures, alertes,", "présence", "127.0.0.1:5433"]),
        (775, "Prometheus", ["collecte /metrics", "toutes les 5 s", "port 9090 (interne)"]),
        (1002, "Grafana", ["MCO : CPU, RAM,", "disque, journaux MQTT", "port 3001"]),
    ]
    for x, title, lines in row2:
        parts += [_r(x, 366, 205, 118, "box2", 10), _t(x + 16, 394, title, "t")]
        for index, line in enumerate(lines):
            parts.append(_t(x + 16, 418 + index * 22, line, "s"))

    # Flux : aucune liaison ne traverse une tuile
    parts += [
        # boitier -> broker
        '<path class="accent" marker-end="url(#arrow-accent)" d="M 370 250 L 520 240"/>',
        _t(392, 232, "MQTTS 8883", "m"),
        _t(392, 214, "TLS 1.2+, CA vérifiée", "s"),
        # broker -> boitier (commandes)
        '<path class="wire" marker-end="url(#arrow)" d="M 520 268 L 374 300"/>',
        _t(392, 320, "commandes", "m"),
        # broker -> backend : abonnement aux mesures
        '<path class="wire" marker-end="url(#arrow)" d="M 684 242 L 697 242"/>',
        # backend -> postgres : SQL (vertical, sous le backend)
        '<path class="accent" marker-end="url(#arrow-accent)" d="M 781 288 L 781 362"/>',
        _t(792, 330, "SQL", "m"),
        # vision -> dashboard : flux annote
        '<path class="wire" marker-end="url(#arrow)" d="M 1038 242 L 1051 242"/>',
        # backend -> dashboard : WebSocket, par le couloir libre sous la rangee haute
        '<path class="wire" marker-end="url(#arrow)" d="M 701 288 L 701 304 L 1135 304 L 1135 292"/>',
        _t(790, 300, "WebSocket /ws", "m"),
        # webcam -> serveur
        '<path class="dash" marker-end="url(#arrow)" d="M 380 770 L 520 620"/>',
        _r(70, 742, 480, 54, "dash", 10),
        _t(92, 776, "Webcam USB — branchée en direct sur le PC serveur", "s"),
        _r(760, 742, 480, 54, "dash", 10),
        _t(782, 776, "Autres tables du workshop — isolées (aucun routage)", "s"),
    ]
    return svg(1300, 820, "\n".join(parts), "Schéma réseau du système SENTINEL-X")


def wiring_diagram() -> str:
    """Cablage du boitier (ESP8266 NodeMCU v2)."""
    parts = [
        _r(30, 30, 1240, 760, "box", 18),
        _t(56, 68, "SCHÉMA DE CÂBLAGE — ESP8266 NodeMCU v2", "k"),
        _t(56, 92, "Boîtier SENTINEL-X : lecture toutes les 2 s, publication MQTTS, alarme locale.", "s"),
    ]

    # Alimentation
    parts += [
        '<path class="accent" d="M 150 150 L 1160 150"/>',
        _t(96, 156, "3V3", "k"),
        '<path class="wire" d="M 150 700 L 1160 700"/>',
        _t(96, 706, "GND", "k"),
    ]

    # ESP8266 central
    parts += [
        _r(430, 250, 300, 360, "box2", 14),
        _t(452, 286, "ESP8266 NodeMCU v2", "h"),
        _t(452, 310, "microcontrôleur unique", "s"),
        _t(452, 340, "D4    GPIO2   — DHT22 DATA", "m"),
        _t(452, 366, "A0    ADC     — MQ-2 AO", "m"),
        _t(452, 392, "D5    GPIO14  — PIR OUT", "m"),
        _t(452, 418, "D6    GPIO12  — buzzer", "m"),
        _t(452, 444, "D7    GPIO13  — LED verte", "m"),
        _t(452, 470, "D8    GPIO15  — LED rouge", "m"),
        _t(452, 496, "D2    GPIO4   — OLED SDA", "m"),
        _t(452, 522, "D1    GPIO5   — OLED SCL", "m"),
        _t(452, 560, "Wi-Fi 2,4 GHz vers 192.168.10.1", "s"),
        _t(452, 584, "MQTTS 8883, compte esp8266", "s"),
    ]

    # Composants
    parts += [
        _r(80, 210, 280, 120, "box", 10),
        _t(100, 240, "DHT22", "t"),
        _t(100, 264, "température et humidité", "s"),
        _t(100, 288, "DATA → D4 (résistance 10 kΩ vers 3V3)", "s"),
        _t(100, 310, "VCC → 3V3     GND → GND", "m"),
        _r(80, 360, 280, 150, "box", 10),
        _t(100, 390, "MQ-2", "t"),
        _t(100, 414, "gaz et fumées", "s"),
        _t(100, 438, "AO → pont diviseur → A0", "s"),
        _t(100, 462, "10 kΩ + 20 kΩ : A0 accepte 3,3 V max", "s"),
        _t(100, 486, "VCC → VIN 5 V     GND → GND", "m"),
        _r(80, 540, 280, 120, "box", 10),
        _t(100, 570, "PIR HC-SR501", "t"),
        _t(100, 594, "détection de présence", "s"),
        _t(100, 618, "OUT → D5", "s"),
        _t(100, 640, "VCC → VIN 5 V     GND → GND", "m"),
    ]

    parts += [
        _r(900, 210, 320, 120, "box", 10),
        _t(920, 240, "Écran OLED SSD1306 0,96\"", "t"),
        _t(920, 264, "I2C — statut IP, Wi-Fi, MQTT", "s"),
        _t(920, 288, "SDA → D2     SCL → D1", "m"),
        _t(920, 310, "VCC → 3V3     GND → GND", "m"),
        _r(900, 360, 320, 100, "box", 10),
        _t(920, 390, "Buzzer piézoélectrique", "t"),
        _t(920, 414, "+ → D6     − → GND", "m"),
        _t(920, 438, "alarme gaz : gaz > 700 (ADC)", "s"),
        _r(900, 490, 320, 170, "box", 10),
        _t(920, 520, "LEDs de statut", "t"),
        _t(920, 546, "verte : lien serveur OK (D7)", "s"),
        _t(920, 570, "rouge : commande du superviseur,", "s"),
        _t(920, 592, "alarme locale, ou lien coupé (D8)", "s"),
        _t(920, 620, "résistance 220 Ω en série", "s"),
        _t(920, 644, "anode → D7 / D8     cathode → GND", "m"),
    ]

    # Liaisons
    for y in (270, 420, 600):
        parts.append(f'<path class="wire" marker-end="url(#arrow)" d="M 360 {y} L 428 {y}"/>')
    for y in (270, 410, 560):
        parts.append(f'<path class="wire" marker-end="url(#arrow)" d="M 732 {y} L 898 {y}"/>')

    parts += [
        _t(56, 740, "Le MQ-2 exige environ 1 minute de préchauffage avant des valeurs stables.", "s"),
        _t(700, 740, "Ressources mesurées à la compilation : RAM 36,8 %, Flash 39,8 %.", "s"),
    ]
    return svg(1300, 820, "\n".join(parts), "Schéma de câblage du boîtier SENTINEL-X")


ASSETS = Path(__file__).resolve().parent / "assets"


def _asset(name: str) -> str:
    """Capture du projet en data URI : le poster reste un fichier autonome."""
    raw = (ASSETS / name).read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


def poster_svg(group: str) -> str:
    """Poster A3 portrait (297 x 420 mm) : le projet en un coup d'oeil, lisible a trois metres.

    Meme doctrine que la presentation : peu de texte, des visuels forts, une idee par bloc.
    """
    W, H, M = 1123, 1587, 64
    R = W - M

    def txt(x, y, content, size, fill, weight=400, anchor="start", spacing=0, family=None):
        attrs = f'x="{x}" y="{y}" font-size="{size}" fill="{fill}"'
        if weight != 400:
            attrs += f' font-weight="{weight}"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        if spacing:
            attrs += f' letter-spacing="{spacing}"'
        if family:
            attrs += f' font-family="{family}"'
        return f"<text {attrs}>{escape(content)}</text>"

    def shot(x, y, w, h, asset, cid):
        return (f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12"/></clipPath>'
                f'<image clip-path="url(#{cid})" x="{x}" y="{y}" width="{w}" height="{h}" '
                f'preserveAspectRatio="xMidYMid slice" href="{_asset(asset)}"/>')

    def flow(x, y, w, h, title, sub, accent=False):
        out = [_r(x, y, w, h, "box2", 12)]
        if accent:
            out.append(f'<rect x="{x + 18}" y="{y + 16}" width="26" height="4" rx="2" fill="{D_ACCENT}"/>')
        ty = y + (44 if accent else 40)
        out.append(txt(x + 18, ty, title, 22, D_TEXT, 700))
        out.append(txt(x + 18, ty + 28, sub, 15, D_MUTED))
        return out

    parts = [
        _r(0, 0, W, H, "box", 0),
        _r(0, 0, W, 252, "box2", 0),
        logo_svg(M, 54, 104, D_TEXT, D_ACCENT),
        txt(M + 128, 116, "SENTINEL-X", 62, D_TEXT, 800),
        txt(M + 132, 158, "L'avant-poste industriel du futur", 26, D_MUTED),
        txt(R, 104, "FORTEX", 26, D_ACCENT, 800, anchor="end", spacing=2),
        txt(R, 138, "Workshop national EPSI Bac+4 · octobre 2026", 18, D_MUTED, anchor="end"),
        f'<rect x="{M}" y="196" width="150" height="6" rx="3" fill="{D_ACCENT}"/>',
        txt(R, 199, "Boîtier virtuel : mêmes topics, même compte MQTTS, mêmes commandes.",
            18, D_MUTED, anchor="end"),
    ]

    # 1 — la chaine de surveillance
    parts += [
        txt(M, 316, "LA CHAÎNE DE SURVEILLANCE", 18, D_ACCENT, 700, spacing=2.4),
        f'<path class="dash" d="M {M} 330 L {R} 330"/>',
    ]
    bw, bh, gap = 215, 104, 45
    for index, (title, sub, accent) in enumerate([
            ("Boîtier", "ESP8266 · DHT22 · MQ-2 · PIR", False),
            ("MQTTS", "TLS 1.3 · comptes · ACL", True),
            ("Backend", "FastAPI · REST · WebSocket", False),
            ("Dashboard", "React · temps réel", False)]):
        x = M + index * (bw + gap)
        parts += flow(x, 352, bw, bh, title, sub, accent=accent)
        if index < 3:
            parts.append(f'<line x1="{x + bw + 8}" y1="404" x2="{x + bw + gap - 8}" y2="404" '
                         f'stroke="{D_ACCENT}" stroke-width="3" marker-end="url(#arrow-accent)"/>')
    for index, (title, sub) in enumerate([
            ("PostgreSQL", "Historique des mesures"),
            ("IA vision", "YOLOv8n · liste blanche · 20 s"),
            ("IA prédictive", "Isolation Forest · seuil appris")]):
        parts += flow(M + index * 339, 480, 317, 92, title, sub)
    parts.append(txt(M, 606, "Le compte du serveur ne peut pas publier de mesures : l'ACL le refuse.",
                     20, D_MUTED))

    # 2 — le systeme en fonctionnement
    parts += [
        txt(M, 668, "LE SYSTÈME EN FONCTIONNEMENT", 18, D_ACCENT, 700, spacing=2.4),
        f'<path class="dash" d="M {M} 682 L {R} 682"/>',
        shot(M, 706, 320, 240, "vision.jpg", "clip-vision"),
        txt(M, 970, "Vision — personne reconnue :", 17, D_MUTED),
        txt(M, 994, "nom à l'écran, aucune alarme.", 17, D_MUTED),
        txt(M, 1018, "Inconnu 20 s : buzzer et LED.", 17, D_MUTED),
        shot(404, 706, 655, 202, "dashboard-banner.jpg", "clip-dash"),
        txt(404, 930, "Supervision — alarmes à traiter, avec leur origine.", 17, D_MUTED),
        shot(404, 962, 655, 202, "grafana-banner.jpg", "clip-grafana"),
        txt(404, 1186, "Exploitation — lecture seule : capteurs et santé du serveur.", 17, D_MUTED),
        txt(M, 1092, "LES TROIS MENACES", 18, D_ACCENT, 700, spacing=2.4),
        f'<path class="dash" d="M {M} 1106 L {M + 320} 1106"/>',
        f'<rect x="{M}" y="1132" width="34" height="5" rx="2" fill="{D_CRITICAL}"/>',
        txt(M, 1168, "Intrusion", 22, D_CRITICAL, 700),
        f'<rect x="{M}" y="1192" width="34" height="5" rx="2" fill="{D_WARNING}"/>',
        txt(M, 1228, "Dérive", 22, D_WARNING, 700),
        f'<rect x="{M + 176}" y="1192" width="34" height="5" rx="2" fill="{D_STALE}"/>',
        txt(M + 176, 1228, "Cyberattaque", 22, D_STALE, 700),
    ]

    # 3 — les chiffres
    figures = [("114", "tests automatisés"), ("32 ms", "latence de la vision"),
               ("436 s", "d'avance sur le seuil"), ("7/7", "contrôles de sécurité")]
    parts += [_r(M, 1276, R - M, 168, "box2", 14),
              txt(M + 32, 1320, "CHIFFRES CLÉS — reproductibles depuis le dépôt", 18, D_ACCENT, 700,
                  spacing=2)]
    for index, (value, label) in enumerate(figures):
        x = M + 32 + index * 246
        fill = D_OK if value == "7/7" else (D_ACCENT if value == "436 s" else D_TEXT)
        parts += [txt(x, 1400, value, 44, fill, 800), txt(x, 1428, label, 16, D_MUTED)]

    parts += [
        f'<path class="dash" d="M {M} 1490 L {R} 1490"/>',
        txt(M, 1526, "Anticiper, pas constater — et le prouver par la mesure.", 24, D_TEXT, 700),
        txt(R, 1522, "github.com/Fortexworkshop/ia", 18, D_MUTED, anchor="end"),
        txt(R, 1548, "Consortium FORTEX" + (f" · Groupe {escape(group)}" if group else ""),
            18, D_MUTED, anchor="end"),
    ]
    return svg(W, H, "\n".join(parts), "Poster SENTINEL-X", theme="dark")


# --------------------------------------------------------------------------- HTML

CSS = f"""
@page {{ size: A4; margin: 17mm 15mm 16mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: {INK}; font-family: {FONT}; font-size: 10.5pt; line-height: 1.5; }}
h1, h2, h3, h4 {{ line-height: 1.25; break-after: avoid; }}
h2 {{ font-size: 17pt; margin: 0 0 10px; padding-bottom: 6px; border-bottom: 2px solid {ACCENT}; }}
h3 {{ font-size: 12.5pt; margin: 18px 0 6px; }}
h4 {{ font-size: 11pt; margin: 14px 0 4px; color: {MUTED}; }}
p {{ margin: 0 0 8px; }}
ul, ol {{ margin: 0 0 10px; padding-left: 20px; }}
li {{ margin-bottom: 3px; }}
a {{ color: {ACCENT}; }}
code {{ font-family: {MONO}; font-size: 9pt; background: {SURFACE2}; padding: 1px 3px; border-radius: 3px; }}
pre {{ font-family: {MONO}; font-size: 8.5pt; background: {SURFACE2}; border: 1px solid {DIVIDER};
       border-radius: 6px; padding: 8px 10px; overflow-wrap: anywhere; white-space: pre-wrap; break-inside: avoid; }}
blockquote {{ margin: 10px 0; padding: 8px 12px; background: {SURFACE2}; border-left: 3px solid {WARN}; break-inside: avoid; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0 14px; font-size: 9pt; break-inside: avoid; }}
th {{ text-align: left; background: {SURFACE2}; }}
th, td {{ border: 1px solid {DIVIDER}; padding: 4px 6px; vertical-align: top; }}
hr {{ border: none; border-top: 1px solid {DIVIDER}; margin: 16px 0; }}
figure {{ margin: 12px 0; break-inside: avoid; }}
figcaption {{ font-size: 8.5pt; color: {MUTED}; margin-top: 4px; }}
.sheet {{ break-after: page; }}
.cover {{ display: flex; flex-direction: column; justify-content: space-between; height: 250mm; }}
.cover .kicker {{ color: {ACCENT}; font-weight: 700; letter-spacing: 2px; font-size: 10pt; }}
.cover h1 {{ font-size: 40pt; margin: 12px 0 0; }}
.cover .sub {{ font-size: 14pt; color: {MUTED}; margin-top: 8px; }}
.cover .meta {{ font-size: 10pt; }}
.cover .meta div {{ margin-bottom: 4px; }}
.cover .rule {{ height: 6px; background: {ACCENT}; width: 180px; margin: 22px 0; }}
.brand {{ margin: 14px 0 0; }}
.brand svg {{ display: block; width: 54px; height: 54px; }}
.toc li {{ margin-bottom: 5px; }}
.toc .num {{ display: inline-block; width: 26px; color: {ACCENT}; font-weight: 700; }}
.note {{ font-size: 9pt; color: {MUTED}; }}
"""

POSTER_CSS = f"""
@page {{ size: A3 portrait; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: {D_BG}; }}
/* Le rapport du viewBox (1123 x 1587) est celui de l'A3 portrait : la hauteur suit. */
.poster svg {{ display: block; width: 297mm; height: auto; }}
"""


def build_html(group: str) -> str:
    ia = md_section(DOCS / "IA.md")
    securite = md_section(DOCS / "SECURITE.md")
    logo_mark = logo_inline(54, INK, ACCENT)
    group_line = f"Groupe {escape(group)}" if group else "Groupe à compléter"

    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8" />
<title>Dossier technique SENTINEL-X</title><style>{CSS}</style></head><body>

<section class="sheet cover">
  <div>
    <div class="kicker">WORKSHOP NATIONAL EPSI · BAC+4 · OCTOBRE 2026</div>
    <div class="brand">{logo_mark}</div>
    <h1>SENTINEL-X</h1>
    <div class="sub">L'avant-poste industriel du futur — dossier d'ingénierie technique</div>
    <div class="rule"></div>
  </div>
  <div class="meta">
    <div><strong>Consortium FORTEX</strong> — {group_line}</div>
    <div>Prototype cyber-physique : boîtier de surveillance autonome et PC serveur local</div>
    <div>Variante d'architecture retenue : <strong>option B</strong> — topologie distribuée
         « Edge-to-Server » sur le portable d'un apprenant</div>
    <div class="note" style="margin-top:14px">Sujet de référence : <em>Mission SENTINEL-X</em>,
         Direction Pédagogique Nationale EPSI, session octobre 2026.</div>
  </div>
</section>

<section class="sheet">
  <h2>Sommaire</h2>
  <ol class="toc">
    <li><span class="num">1</span> Contexte, périmètre et variante d'architecture</li>
    <li><span class="num">2</span> Schéma réseau : sous-réseau, flux et ports</li>
    <li><span class="num">3</span> Chaîne de collecte : firmware et schéma de câblage</li>
    <li><span class="num">4</span> Infrastructure et maintien en condition opérationnelle</li>
    <li><span class="num">5</span> Matrice de sécurité (chiffrement et durcissement)</li>
    <li><span class="num">6</span> Documentation de l'intelligence artificielle</li>
    <li><span class="num">7</span> Qualité, tests et reproductibilité</li>
    <li><span class="num">8</span> Limites connues et pistes d'amélioration</li>
  </ol>
  <h3>Ce que contient ce dossier</h3>
  <p>Les chapitres 5 et 6 reprennent les documents sources du dépôt
  (<code>docs/SECURITE.md</code> et <code>docs/IA.md</code>) ; les schémas des chapitres 2 et 3
  sont produits depuis le code (<code>infra/docker-compose.yml</code>,
  <code>firmware/sentinel-x/</code>). Le poster de présentation est livré à part, en A3 portrait
  (<code>Workshop2026-M1-G&lt;n&gt;-Poster.pdf</code>).</p>
</section>

<section class="sheet">
  <h2>1. Contexte, périmètre et variante d'architecture</h2>
  <p>AetherCorp Industrial Solutions exploite des micro-centrales énergétiques isolées, exposées à
  trois menaces simultanées : cyberattaques de déstabilisation, intrusions physiques d'espionnage
  industriel et risques environnementaux (fuite de gaz, surchauffe). Faute de pouvoir maintenir du
  personnel sur place, l'initiative <strong>SENTINEL-X</strong> confie la surveillance à un boîtier
  autonome (Edge Node) relié sans fil à un centre de commandement tactique matérialisé par un PC
  serveur local durci.</p>

  <h3>Variante d'architecture</h3>
  <p>Le sujet autorise deux options matérielles. Le consortium retient l'<strong>option B</strong> :
  le rôle de PC serveur local est tenu par l'ordinateur portable d'un apprenant, qui fait aussi
  point d'accès Wi-Fi de la table. La webcam USB y est branchée en direct, et l'intelligence
  artificielle profite de ses capacités de calcul. Le boîtier ne contient que le microcontrôleur et
  ses composants de captation, et transmet ses flux par Wi-Fi à l'adresse du serveur.</p>

  <h3>Périmètre livré</h3>
  <ul>
    <li><strong>Edge et IoT</strong> — micrologiciel C++ pour l'ESP8266 unique de table : lecture
        cadencée des capteurs, affichage OLED, alarme locale, publication MQTTS.</li>
    <li><strong>Serveur et API</strong> — API REST et WebSocket hébergée sur le PC serveur,
        centralisant les métriques et l'historique des événements.</li>
    <li><strong>Supervision</strong> — interface web : courbes environnementales temps réel, statut
        logique du boîtier, retour visuel de la webcam, panneau de commande des actionneurs.</li>
    <li><strong>Intelligence artificielle locale</strong> — vision par webcam et maintenance
        prédictive sur séries temporelles.</li>
    <li><strong>Infrastructure</strong> — orchestration des conteneurs serveurs et sécurisation des
        protocoles d'ingestion.</li>
    <li><strong>Cybersécurité</strong> — chiffrement des flux, durcissement des conteneurs, journal
        d'audit et contrôles reproductibles.</li>
  </ul>

  <h3>Périmètre adapté, validé en début de workshop</h3>
  <p>Trois éléments du sujet ont été adaptés, en accord avec l'encadrement :</p>
  <ul>
    <li><strong>Boîtier virtuel</strong> — aucun matériel n'étant distribué, le boîtier est simulé
        (<code>scripts/virtual_esp.py</code>) : mêmes topics, même compte MQTTS, mêmes commandes,
        même alarme locale que le firmware. Le firmware C++ est écrit et compile.</li>
    <li><strong>Coque non fabriquée</strong> — la modélisation CAO, l'impression 3D et la gravure
        laser n'ont pas été réalisées.</li>
    <li><strong>Pentest croisé du jeudi supprimé</strong> — il n'y a donc pas de rapport d'audit
        post-pentest ; le chapitre 5 fournit l'auto-audit reproductible.</li>
  </ul>
</section>

<section class="sheet">
  <h2>2. Schéma réseau : sous-réseau, flux et ports</h2>
  <figure>
    {network_diagram()}
    <figcaption>Figure 1 — Topologie de table : le boîtier, le PC serveur local et les flux
    chiffrés. Les conteneurs Docker sont isolés sur l'hôte.</figcaption>
  </figure>
  <h3>Plan d'adressage et isolation</h3>
  <p>La table utilise le sous-réseau <code>192.168.10.0/24</code>, desservi par le point d'accès
  Wi-Fi du PC serveur. Aucune route n'est établie vers les autres tables du workshop : les paquets
  du boîtier ne peuvent atteindre que le PC serveur, et réciproquement. Seuls les services
  nécessaires sont exposés.</p>
  <table>
    <thead><tr><th>Service</th><th>Port</th><th>Écoute sur</th><th>Protocole</th></tr></thead>
    <tbody>
      <tr><td>Mosquitto (conteneur)</td><td>8883</td><td>Réseau de table</td>
          <td>MQTTS — TLS 1.2 minimum, compte obligatoire</td></tr>
      <tr><td>Backend Fortex</td><td>8080</td><td>Réseau de table</td>
          <td>HTTP (REST) et WebSocket <code>/ws</code></td></tr>
      <tr><td>Flux vidéo (vision)</td><td>8081</td><td>Réseau de table</td>
          <td>MJPEG annoté et <code>/status</code></td></tr>
      <tr><td>Dashboard React</td><td>5173</td><td>Réseau de table</td><td>HTTP (build Vite)</td></tr>
      <tr><td>PostgreSQL (conteneur)</td><td>5433</td><td><strong>localhost uniquement</strong></td>
          <td>TCP — injoignable depuis le réseau</td></tr>
      <tr><td>Grafana (conteneur)</td><td>3001</td><td>Réseau de table</td><td>HTTP</td></tr>
      <tr><td>Prometheus (conteneur)</td><td>9090</td><td><strong>interne</strong></td>
          <td>Collecte de <code>/metrics</code> toutes les 5 s</td></tr>
    </tbody>
  </table>
  <p class="note">Le compte MQTT du serveur ne peut pas publier de mesures : l'injection de fausses
  données est refusée par l'ACL, volontairement. Le port 1883 en clair n'est plus publié.</p>
</section>

<section class="sheet">
  <h2>3. Chaîne de collecte : firmware et schéma de câblage</h2>
  <figure>
    {wiring_diagram()}
    <figcaption>Figure 2 — Câblage du boîtier : un seul microcontrôleur ESP8266, trois capteurs,
    un écran OLED et les organes d'alerte.</figcaption>
  </figure>
  <h3>Comportement du firmware</h3>
  <ul>
    <li>Lecture du DHT22, du MQ-2 et du PIR <strong>toutes les 2 secondes</strong>.</li>
    <li>Publication en <strong>MQTTS</strong> (TLS, port 8883, compte <code>esp8266</code>) sur
        <code>sentinel/&lt;id&gt;/sensors</code> :
        <code>{{node_id, temperature, humidity, gas, pir, ip, rssi}}</code>.</li>
    <li>Écoute de <code>sentinel/&lt;id&gt;/commands</code> :
        <code>{{actuator: buzzer|led, state: true|false}}</code>, déclenchée depuis le dashboard.</li>
    <li>Publication de <code>online</code> / <code>offline</code> sur
        <code>sentinel/&lt;id&gt;/status</code> ; le message <code>offline</code> est le testament
        MQTT, publié par le broker si le boîtier disparaît.</li>
    <li><strong>Garde-fou local</strong> — buzzer et LED rouge si le gaz dépasse 700 (ADC), même
        sans serveur joignable.</li>
  </ul>
  <p class="note">L'entrée A0 du NodeMCU accepte 3,3 V au maximum : la sortie 5 V du MQ-2 passe par
  un pont diviseur. Le MQ-2 demande environ une minute de préchauffage avant des valeurs stables.
  Comme l'ESP8266 s'appuie sur l'heure de compilation pour valider le certificat TLS, le module est
  flashé après la génération des certificats.</p>
</section>

<section class="sheet">
  <h2>4. Infrastructure et maintien en condition opérationnelle</h2>
  <p>La pile serveur est décrite dans <code>infra/docker-compose.yml</code> et se déploie en une
  commande. Les services sont isolés dans des conteneurs pérennes, redémarrés automatiquement et
  durcis.</p>
  <table>
    <thead><tr><th>Conteneur</th><th>Rôle</th><th>Durcissement appliqué</th></tr></thead>
    <tbody>
      <tr><td><code>mosquitto</code></td><td>Broker MQTTS des mesures et des commandes</td>
          <td>Comptes nominatifs, ACL, anonyme refusé, aucun port en clair</td></tr>
      <tr><td><code>postgres</code></td><td>Mesures, alertes, journal de présence</td>
          <td>Publié sur localhost seulement, volume dédié</td></tr>
      <tr><td><code>backend</code></td><td>API REST et WebSocket</td>
          <td><code>read_only</code>, <code>cap_drop</code>, <code>no-new-privileges</code></td></tr>
      <tr><td><code>prometheus</code></td><td>Collecte des métriques toutes les 5 s</td>
          <td>Profil dédié, données sur volume</td></tr>
      <tr><td><code>grafana</code></td><td>Tableaux de bord MCO</td>
          <td>Compte PostgreSQL en <strong>lecture seule</strong></td></tr>
      <tr><td><code>simulator</code></td><td>Simulateur IoT (profil <code>simulation</code>)</td>
          <td>Désactivé par défaut : jamais mélangé aux mesures réelles</td></tr>
    </tbody>
  </table>
  <h3>Surveillance du MCO</h3>
  <p>Le backend expose <code>GET /metrics</code>, collecté par Prometheus et affiché dans Grafana.
  Les indicateurs surveillés couvrent à la fois la disponibilité de la chaîne et la santé de la
  machine hôte, conformément à l'exigence de maintien en condition opérationnelle :</p>
  <ul>
    <li><strong>Chaîne</strong> — backend en fonctionnement, pont MQTTS connecté, base joignable,
        fraîcheur de la dernière mesure, dashboards connectés, vision en cours.</li>
    <li><strong>Volumétrie</strong> — nombre de mesures reçues, messages capteurs rejetés, alertes
        par type et par source, commandes envoyées, <strong>volume du journal Mosquitto</strong>.</li>
    <li><strong>Machine hôte</strong> — <strong>CPU</strong>, <strong>RAM</strong> utilisée et
        <strong>disque</strong>, pour anticiper la saturation face à l'afflux continu des messages.</li>
  </ul>
</section>

<section class="sheet">
  <h2>5. Matrice de sécurité (chiffrement et durcissement)</h2>
  {securite}
</section>

<section class="sheet">
  <h2>6. Documentation de l'intelligence artificielle</h2>
  {ia}
</section>

<section class="sheet">
  <h2>7. Qualité, tests et reproductibilité</h2>
  <h3>Tests automatisés</h3>
  <p>La suite compte <strong>114 tests</strong> (pytest), exécutables sans matériel :</p>
  <pre>python -m pytest -q                       # suite complète
python -m pytest tests/test_backend.py -q # un fichier</pre>
  <h3>Contrôles de sécurité et de performance</h3>
  <pre>python scripts/check_security.py   # 7 contrôles : TLS, comptes MQTT, ACL, jeton
python scripts/bench_vision.py     # latence de la vision (exigence &lt; 100 ms)</pre>
  <h3>Reproductibilité de l'installation</h3>
  <p>L'installation complète tient en deux commandes, sur le PC serveur Windows :
  <code>scripts\\setup.ps1 -ServerIp 192.168.10.1</code> puis <code>scripts\\start.ps1</code>.
  <code>scripts/configure.py</code> est idempotent : il génère les secrets, la CA TLS, les comptes
  MQTT, les fichiers <code>.env</code> et la configuration du firmware
  <strong>sans jamais écraser une valeur existante</strong>.</p>
  <h3>Hygiène du dépôt</h3>
  <ul>
    <li>Aucun secret versionné : les <code>.env</code>, certificats, mots de passe MQTT et
        configuration du firmware sont générés localement et exclus par <code>.gitignore</code> ;
        les fichiers <code>*.example</code> ne contiennent que des valeurs factices.</li>
    <li>Données personnelles hors du dépôt : empreintes faciales et journaux de présence restent
        sur le PC serveur.</li>
    <li>Documentation du dépôt en français, commits sémantiques (Conventional Commits).</li>
  </ul>
</section>

<section class="sheet">
  <h2>8. Limites connues et pistes d'amélioration</h2>
  <p>Ces points sont assumés et documentés : le jury les retrouvera dans le dépôt.</p>
  <table>
    <thead><tr><th>Limite</th><th>Impact</th><th>Piste</th></tr></thead>
    <tbody>
      <tr><td>Boîtier physique remplacé par un boîtier virtuel</td>
          <td>Aucune preuve matérielle : ni câblage, ni coque imprimée et gravée</td>
          <td>Flasher le firmware sur le matériel de table si du matériel est fourni</td></tr>
      <tr><td>Firmware jamais exécuté sur un ESP8266 réel</td>
          <td>Le fonctionnement sur silicium reste à confirmer</td>
          <td>Essai sur banc avec le vrai module, puis comparaison des mesures</td></tr>
      <tr><td>API, dashboard et flux vidéo en HTTP sur le réseau de table</td>
          <td>Le code opérateur circule en clair ; le sujet demande le chiffrement de bout en bout</td>
          <td>Reverse proxy TLS avec la même CA, ou pointer l'origine sur HTTPS</td></tr>
      <tr><td>Flux caméra (<code>:8081/video</code>) sans authentification</td>
          <td>Toute machine de la table voit la caméra</td>
          <td>Jeton ou diffusion du flux via l'API</td></tr>
      <tr><td>Durcissement du système d'exploitation non appliqué</td>
          <td>Pare-feu et accès SSH restent à régler sur le poste serveur</td>
          <td>Règles de pare-feu Windows, accès par clé, preuve conservée</td></tr>
      <tr><td>Aucun rapport de pentest croisé</td><td>Pas d'audit offensif externe</td>
          <td>Poursuivre l'auto-audit (<code>check_security.py</code>) et le rejouer sur la table</td></tr>
      <tr><td>Code opérateur partagé, non nominatif</td>
          <td>Le journal d'audit identifie un poste, pas une personne</td>
          <td>Comptes nominatifs et rôles distincts</td></tr>
      <tr><td>IA prédictive sans signal de vie</td>
          <td>Un arrêt du script n'est pas alarmé sur le serveur</td>
          <td>Exposer sa fraîcheur via <code>/metrics</code></td></tr>
    </tbody>
  </table>
  <h3>Réponse à une question probable du jury</h3>
  <p>Le sujet interdit les structures conditionnelles statiques pour la maintenance prédictive
  (<code>if temp &gt; 40</code>). Le modèle déployé est bien un <em>Isolation Forest</em> à seuil
  appris. Le backend conserve en parallèle un <strong>garde-fou de dernier recours</strong> à seuil
  fixe, hérité du rôle d'alarme locale : il ne participe pas à la prédiction, ne remplace pas le
  modèle et reste désactivable. Les deux mécanismes sont distincts et documentés comme tels.</p>
</section>
</body></html>
"""


def build_poster_html(group: str) -> str:
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8" />
<title>Poster SENTINEL-X</title><style>{POSTER_CSS}</style></head><body>
<div class="poster">{poster_svg(group)}</div>
</body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--group", default="", help="numero de groupe (<n> du nom de fichier)")
    parser.add_argument("--out", default=str(ROOT.parent / "rendus"), help="dossier de sortie")
    parser.add_argument("--html-only", action="store_true", help="n'ecrire que le HTML (mise au point)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    render = here / "render.js"
    tag = f"G{args.group}-" if args.group else ""

    jobs = [
        ("Dossier", here / "dossier.html", build_html(args.group), f"Workshop2026-M1-{tag}Dossier.pdf"),
        ("Poster", here / "poster.html", build_poster_html(args.group), f"Workshop2026-M1-{tag}Poster.pdf"),
    ]
    for label, html_path, html, pdf_name in jobs:
        html_path.write_text(html, encoding="utf-8")
        print(f"HTML {label} : {html_path} ({html_path.stat().st_size // 1024} Ko)")
        if args.html_only:
            continue
        pdf_path = out_dir / pdf_name
        result = subprocess.run(["node", str(render), str(html_path), str(pdf_path)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(result.stderr.strip() or f"rendu PDF impossible ({label})")
        print(result.stdout.strip())


if __name__ == "__main__":
    main()
