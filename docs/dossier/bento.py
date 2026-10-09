"""Genere la presentation SENTINEL-X au format Bento (SENTINEL-X-G20.bento.html).

Le deck applique la **charte graphique du projet** (`dev/dashboard/src/tokens.css`) : theme sombre
de l'application, accent bleu acier reserve a l'emphase, couleurs d'etat (rouge, ambre, vert,
violet) employees uniquement pour signaler un ecart, et le logo FORTEX
(`dev/dashboard/src/components/Icon.jsx`) porte sur chaque slide.

Le contenu vient du depot (README.md, docs/IA.md, docs/SECURITE.md, infra/docker-compose.yml) et
les captures d'ecran sont celles du projet, stockees dans `docs/dossier/assets/`.

Le document est ecrit dans le bloc `#bento-doc` d'une copie de l'application Bento : le reste du
fichier n'est jamais regenere, seul le bloc JSON est remplace.

Usage :
    python docs/dossier/bento.py [--out ../../rendus/neuf] [--group 20] [--json-only]

Produit dans le dossier de sortie :
    SENTINEL-X-G<n>.bento.html   (application + document)
    SENTINEL-X-G<n>.bento.json   (document seul, pour « Save > Replace from JSON »)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # docassets.py, voisin de ce script
import docassets  # noqa: E402  (apres l'ajout du dossier au chemin d'import)

ROOT = Path(__file__).resolve().parent.parent.parent      # Fortex/
ASSETS = docassets.ASSETS
APP_URL = "https://bento.page/releases/slides/Bento_Slides.bento.html"

FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans', sans-serif"
MONO = "ui-monospace, 'SF Mono', 'Cascadia Mono', 'Segoe UI Mono', Consolas, monospace"

# --- Charte graphique FORTEX (dev/dashboard/src/tokens.css, theme sombre) -------------------
BG = "#0d1117"             # --bg
SURFACE = "#151b23"        # --surface
SURFACE2 = "#1b222c"       # --surface-2
DIVIDER = "#2a323e"        # --divider    (separateurs non porteurs d'information)
TEXT = "#e6e9ee"           # --text
MUTED = "#a4adba"          # --text-muted
FAINT = "#8a94a3"          # --text-faint
ACCENT = "#79aaf7"         # --accent     (interaction et emphase — jamais un etat)
ACCENT_STRONG = "#a8c8fb"  # --accent-strong
CRITICAL = "#ff6b66"       # --critical
WARNING = "#f2b440"        # --warning
OK = "#5fcf95"             # --ok
STALE = "#c3a6ff"          # --stale

MARGIN, RIGHT = 96, 1184
WIDTH, HEIGHT = 1280, 720


# --------------------------------------------------------------------------- Fabriques

def logo(eid, x, y, size, stroke=TEXT, accent=ACCENT, morph="logo"):
    """Le logo FORTEX — bastion en plan autour d'un capteur (ni degrade, ni ombre).

    Le trace vient de `assets/logo.svg` (`docassets`), meme source que le dossier et le poster.
    """
    markup = (f'<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">'
              f'{docassets.logo_inner(stroke, accent)}</svg>')
    return {"id": eid, "type": "svg", "x": x, "y": y, "w": size, "h": size, "rotation": 0,
            "opacity": 1, "markup": markup, "morphId": morph}


def text(eid, x, y, w, h, html, size, color=TEXT, weight=400, align="left", valign="top",
         line_height=1.3, letter_spacing=0, font=FONT, morph=None, fx=None, link=None):
    el = {"id": eid, "type": "text", "x": x, "y": y, "w": w, "h": h, "rotation": 0, "opacity": 1,
          "html": html, "fontSize": size, "fontFamily": font, "fontWeight": weight, "color": color,
          "align": align, "valign": valign, "lineHeight": line_height}
    if letter_spacing:
        el["letterSpacing"] = letter_spacing
    if morph:
        el["morphId"] = morph
    if fx:
        el["fx"] = fx
    if link:
        el["link"] = link
    return el


def rect(eid, x, y, w, h, fill, stroke="none", stroke_width=0, radius=0, morph=None,
         stroke_style=None, fx=None, link=None):
    el = {"id": eid, "type": "shape", "shape": "rect", "x": x, "y": y, "w": w, "h": h,
          "rotation": 0, "opacity": 1, "fill": fill, "stroke": stroke, "strokeWidth": stroke_width,
          "radius": radius}
    if stroke_style:
        el["strokeStyle"] = stroke_style
    if morph:
        el["morphId"] = morph
    if fx:
        el["fx"] = fx
    if link:
        el["link"] = link
    return el


def image(eid, x, y, w, h, asset, fit="cover", radius=10, morph=None, fx=None):
    el = {"id": eid, "type": "image", "x": x, "y": y, "w": w, "h": h, "rotation": 0, "opacity": 1,
          "src": f"asset:{asset}", "fit": fit, "radius": radius}
    if morph:
        el["morphId"] = morph
    if fx:
        el["fx"] = fx
    return el


def chart(eid, x, y, w, h, option, fx=None):
    el = {"id": eid, "type": "chart", "x": x, "y": y, "w": w, "h": h, "rotation": 0, "opacity": 1,
          "preset": option.pop("_preset", "bar"), "option": option}
    if fx:
        el["fx"] = fx
    return el


def table(eid, x, y, w, h, columns, rows, font_size=17, pad_x=14, pad_y=10, morph=None):
    el = {"id": eid, "type": "table", "x": x, "y": y, "w": w, "h": h, "rotation": 0, "opacity": 1,
          "header": True, "columns": [{"w": c} for c in columns],
          "rows": [{"cells": [{"html": c} for c in row]} for row in rows],
          "style": {"headerBg": SURFACE2, "headerColor": TEXT,
                    "zebra": "rgba(255,255,255,0.035)", "borderColor": DIVIDER,
                    "borderWidth": 1, "cellPadX": pad_x, "cellPadY": pad_y,
                    "fontSize": font_size, "color": TEXT, "radius": 10}}
    if morph:
        el["morphId"] = morph
    return el


def head(kicker, headline, size=52):
    """En-tete commun. Les ids sont stables : ils se transforment d'un slide a l'autre (morph)."""
    return [
        logo("logo-head", RIGHT - 44, 66, 44),
        text("kicker", MARGIN, 72, 780, 26, kicker, 17, ACCENT, 700, letter_spacing=2.4),
        text("headline", MARGIN, 106, RIGHT - MARGIN, 124, headline, size, TEXT, 800, line_height=1.15),
        rect("bar", MARGIN, 246, 96, 6, ACCENT),
    ]


def card(eid, x, y, w, h, title, body, title_size=21, body_size=17, accent=None):
    return [
        rect(eid, x, y, w, h, SURFACE, DIVIDER, 1, 14),
        rect(eid + "-rule", x + 24, y + 24, 28, 4, accent or ACCENT, radius=2),
        text(eid + "-t", x + 24, y + 38, w - 48, 72, title, title_size, TEXT, 700),
        text(eid + "-b", x + 24, y + 118, w - 48, h - 144, body, body_size, MUTED, 400,
             line_height=1.45),
    ]


# --------------------------------------------------------------------------- Document
#
# Conception du support, en amont (formation IPSSI « Ameliorer ses competences en presentation ») :
#   - objectifs fixes AVANT la construction (voir les notes de la slide de titre) ;
#   - une idee par diapositive, peu de texte, des visuels forts ;
#   - police lisible et taille suffisante : aucun corps de texte sous 24 px ;
#   - titres de parties coherents et repetes (kicker + titre, portes en morph) ;
#   - pas d'effet decoratif : seul le morph (structure) et le compteur des chiffres cles ;
#   - le minutage de chaque partie est ecrit dans les notes, avec le script a dire.

TIMING = {
    "cover": "0:30", "probleme": "1:00", "chaine": "1:15", "vision": "0:45",
    "predictif": "1:00", "preuves": "0:45", "supervision": "0:45", "exploitation": "0:45",
    "securite": "0:45", "equipe": "0:30", "limites": "0:45", "suite": "0:30", "merci": "0:15",
}


def notes(slide_id: str, text: str) -> str:
    """Le script de la slide : duree cible, puis ce qui se dit (jamais lu a l'ecran)."""
    return f"[{TIMING.get(slide_id, '—')}]  {text}"


def block(eid, x, y, w, h, title, sub, title_size=26, sub_size=18, accent=None, fill=SURFACE):
    """Bloc du schema : un rectangle, un intitule, une precision."""
    parts = [rect(eid, x, y, w, h, fill, DIVIDER, 1, 12)]
    if accent:
        parts.append(rect(eid + "-rule", x + 20, y + 18, 24, 4, accent, radius=2))
        top = y + 34
    else:
        top = y + 24
    parts.append(text(eid + "-t", x + 20, top, w - 40, 40, title, title_size, TEXT, 700))
    if sub:
        parts.append(text(eid + "-s", x + 20, top + 40, w - 40, h - (top - y) - 20, sub, sub_size,
                          MUTED, 400, line_height=1.35))
    return parts


def arrow(eid, x, y, w, color=ACCENT):
    """Fleche horizontale : une `line` se trace sur toute sa boite, la pointe se pose au bout."""
    return {"id": eid, "type": "shape", "shape": "line", "x": x, "y": y, "w": w, "h": 3,
            "rotation": 0, "opacity": 1, "fill": color, "stroke": color, "strokeWidth": 3,
            "lineEnd": "arrow"}


def build_doc(group: str, assets: dict[str, str]) -> dict:
    tag = f"G{group}" if group else "G?"

    s_cover = {
        "id": "cover", "background": BG, "transition": "none",
        "notes": notes("cover",
                       "OBJECTIFS DU SUPPORT (fixes avant construction) — principal : faire comprendre "
                       "que la chaîne surveille et anticipe toute seule ; secondaires : montrer la "
                       "conformité au sujet, rassurer sur la sécurité, assumer les limites. Public : "
                       "jury EPSI, technique, qui connaît le sujet. Message à retenir : « anticiper, "
                       "pas constater ». Fil rouge : « le prouver par la mesure ». "
                       "SCRIPT — Bonjour, nous sommes le groupe 20, l'équipe FORTEX. Sentinel-X, "
                       "c'est un avant-poste de surveillance autonome : un boîtier qui veille sur une "
                       "micro-centrale isolée et son PC serveur local."),
        "elements": [
            logo("logo", MARGIN, 84, 64),
            text("kicker", MARGIN, 176, 800, 26, "WORKSHOP NATIONAL EPSI · BAC+4 · OCTOBRE 2026",
                 18, ACCENT, 700, letter_spacing=2.4),
            text("headline", MARGIN, 216, RIGHT - MARGIN, 170, "SENTINEL-X", 128, TEXT, 900,
                 line_height=1.0),
            text("cover-sub", MARGIN, 396, 900, 60, "L'avant-poste industriel du futur", 40, MUTED),
            rect("bar", MARGIN, 484, 240, 8, ACCENT),
            text("cover-meta", MARGIN, 528, RIGHT - MARGIN, 90,
                 f"Consortium FORTEX — {tag} · Option B, PC serveur local<br>"
                 "github.com/Fortexworkshop/ia", 22, FAINT, 400, line_height=1.5),
        ],
    }

    s_problem = {
        "id": "probleme", "background": BG, "transition": "morph",
        "notes": notes("probleme",
                       "SCRIPT — Le contexte : des micro-centrales isolées, et personne sur place. "
                       "Trois menaces, en même temps. Et pour la dérive, le mot important c'est "
                       "« lentement » : elle s'installe bien avant d'atteindre une valeur critique. "
                       "On ne veut donc pas constater l'incident, on veut l'anticiper. "
                       "Ne pas lire la diapositive : les trois mots sont des repères, le détail est "
                       "à l'oral."),
        "elements": head("LE PROBLÈME", "Aucun personnel sur place") + [
            rect("p1-rule", MARGIN, 306, 40, 6, CRITICAL, radius=3),
            text("p1", MARGIN, 326, 336, 48, "Intrusion", 34, CRITICAL, 700),
            text("p1-s", MARGIN, 380, 336, 100,
                 "Espionnage industriel : quelqu'un s'approche sans être reconnu.", 22, MUTED,
                 line_height=1.4),
            rect("p2-rule", 472, 306, 40, 6, WARNING, radius=3),
            text("p2", 472, 326, 336, 48, "Dérive", 34, WARNING, 700),
            text("p2-s", 472, 380, 336, 100,
                 "Surchauffe ou fuite de gaz : une évolution lente, largement avant le seuil.",
                 22, MUTED, line_height=1.4),
            rect("p3-rule", 848, 306, 40, 6, STALE, radius=3),
            text("p3", 848, 326, 336, 48, "Cyberattaque", 34, STALE, 700),
            text("p3-s", 848, 380, 336, 100,
                 "Déstabilisation, interception, injection de fausses mesures.", 22, MUTED,
                 line_height=1.4),
            text("p-note", MARGIN, 566, RIGHT - MARGIN, 70,
                 "Surveiller sans personne : la chaîne doit décider seule, et le prouver.",
                 30, TEXT, 600, line_height=1.3),
        ],
    }

    s_chain = {
        "id": "chaine", "background": BG, "transition": "morph",
        "notes": notes("chaine",
                       "SCRIPT — Notre réponse, en une ligne : le boîtier mesure, il publie en MQTTS "
                       "chiffré, le backend centralise et rediffuse, le dashboard conduit. À côté, "
                       "deux briques d'IA : la vision et la maintenance prédictive. Le point à "
                       "retenir : tout circule chiffré, et le compte du serveur ne peut pas fabriquer "
                       "de fausses mesures. Suivre les flèches avec la main, sans tourner le dos au "
                       "public."),
        "elements": head("LA RÉPONSE", "De la mesure à l'alarme, chiffré") + [
            *block("b1", MARGIN, 282, 236, 120, "Boîtier", "ESP8266 · DHT22 · MQ-2 · PIR", 26, 17),
            *block("b2", 380, 282, 236, 120, "MQTTS", "TLS 1.3 · comptes · ACL", 26, 17, accent=ACCENT),
            *block("b3", 664, 282, 236, 120, "Backend", "FastAPI · REST · WebSocket", 26, 17),
            *block("b4", 948, 282, 236, 120, "Dashboard", "React · temps réel", 26, 17),
            arrow("a1", 336, 340, 42),
            arrow("a2", 620, 340, 42),
            arrow("a3", 904, 340, 42),
            rect("sub-box", MARGIN, 436, RIGHT - MARGIN, 152, SURFACE, DIVIDER, 1, 12),
            text("sub-label", 116, 448, 700, 30, "Alimenté par le backend", 20, MUTED),
            *block("c1", 112, 482, 338, 94, "PostgreSQL", "Historique des mesures", 24, 17,
                   fill=SURFACE2),
            *block("c2", 470, 482, 338, 94, "IA vision", "YOLOv8n · liste blanche · 20 s", 24, 17,
                   fill=SURFACE2),
            *block("c3", 828, 482, 338, 94, "IA prédictive", "Isolation Forest · seuil appris", 24, 17,
                   fill=SURFACE2),
            text("chain-note", MARGIN, 606, RIGHT - MARGIN, 60,
                 "Le compte du serveur ne peut pas publier de mesures : l'ACL le refuse.",
                 26, MUTED, 400),
        ],
    }

    s_vision = {
        "id": "vision", "background": BG, "transition": "morph",
        "notes": notes("vision",
                       "SCRIPT — La vision ne se contente pas de détecter une forme : elle reconnaît "
                       "la personne, affiche son nom, et laisse passer le personnel autorisé. Une "
                       "personne inconnue pendant vingt secondes, et l'alarme part — avec le buzzer "
                       "et la LED sur le boîtier. Vingt secondes, c'est le temps de traverser le "
                       "site : assez pour ne pas sonner sur un passage, trop court pour laisser "
                       "quelqu'un s'installer."),
        "elements": head("IA — VISION", "Reconnaître, pas seulement détecter") + [
            image("shot-vision", MARGIN, 292, 400, 300, "vision", fit="cover"),
            text("v-big", 536, 300, 648, 140, "20 s", 108, TEXT, 900, line_height=1.0),
            text("v-big-s", 536, 446, 648, 60, "avant que l'alarme ne part", 26, MUTED),
            text("v-note", 536, 516, 648, 100,
                 "Liste blanche : le personnel autorisé ne déclenche rien.", 24, MUTED,
                 line_height=1.4),
        ],
    }

    s_pred = {
        "id": "predictif", "background": BG, "transition": "morph",
        "notes": notes("predictif",
                       "SCRIPT — La maintenance prédictive, c'est le cœur technique, et c'est aussi "
                       "une exigence du sujet : aucune condition statique du type « si la température "
                       "dépasse 40 ». Nous découpons le flux en fenêtres de 30 mesures, nous en "
                       "tirons neuf indicateurs — dont la pente et la corrélation température/gaz — "
                       "et un Isolation Forest, dont le seuil est appris, décide. Résultat : "
                       "cinquante incidents sur cinquante détectés, une seule fausse alerte sur "
                       "cinquante, et 436 secondes d'avance. Sur le boîtier virtuel, l'alerte part "
                       "vers 25 °C. Cliquer sur « seuil appris » ouvre le détail des neuf "
                       "indicateurs — c'est la question la plus probable du jury."),
        "elements": head("IA — PRÉDICTIVE", "Alerter avant le seuil, pas après") + [
            chart("pred-chart", MARGIN, 292, 620, 300, {
                "_preset": "bar",
                "grid": {"left": 84, "right": 24, "top": 24, "bottom": 56},
                "xAxis": {"type": "category", "data": ["Avance moyenne", "Avance minimum"],
                          "axisLabel": {"fontSize": 16, "color": MUTED},
                          "axisLine": {"lineStyle": {"color": DIVIDER}}},
                "yAxis": {"type": "value", "max": 500,
                          "axisLabel": {"formatter": "{value} s", "fontSize": 15, "color": MUTED},
                          "splitLine": {"lineStyle": {"color": DIVIDER}}},
                "series": [{"type": "bar", "data": [436, 388], "barWidth": 104,
                            "itemStyle": {"color": ACCENT, "borderRadius": [6, 6, 0, 0]}}],
                "tooltip": {"trigger": "item", "formatter": "{b} : {c} s"},
            }),
            text("pred-big", 742, 300, 442, 120, "436 s", 88, ACCENT, 900, line_height=1.0),
            text("pred-big-s", 742, 410, 442, 70, "d'avance sur le seuil critique", 24, MUTED,
                 line_height=1.35),
            text("pred-link", 742, 496, 442, 110,
                 "<b><u><a>Seuil appris</a></u></b> : 30 mesures, 9 indicateurs, "
                 "10 fenêtres anormales avant l'alerte.", 24, MUTED, line_height=1.4,
                 link="state-modele"),
            text("pred-note", MARGIN, 608, 620, 60,
                 "Alerte vers 25 °C, pour un seuil critique à 40 °C.", 24, MUTED),
        ],
    }

    s_proof = {
        "id": "preuves", "background": BG, "transition": "morph",
        "notes": notes("preuves",
                       "SCRIPT — Trois chiffres, et ils sont reproductibles : la commande est écrite "
                       "sous la diapositive. Cent quatorze tests passent hors matériel ; la vision "
                       "tourne en 32 millisecondes, largement sous les 100 demandées ; et sept "
                       "contrôles de sécurité sur sept réussissent sur la pile réelle. Ce n'est pas "
                       "une capture d'écran, c'est ce que les scripts du dépôt affichent."),
        "elements": [
            logo("logo-head", RIGHT - 44, 66, 44),
            text("kicker", MARGIN, 72, 780, 26, "CE QUI EST MESURÉ", 18, ACCENT, 700,
                 letter_spacing=2.4),
            text("headline", MARGIN, 106, RIGHT - MARGIN, 100, "Trois chiffres, reproductibles",
                 50, TEXT, 800, line_height=1.15),
            rect("bar", MARGIN, 246, 96, 6, ACCENT),
            text("n1", MARGIN, 312, 340, 130, "114", 104, TEXT, 900, line_height=1.0,
                 fx={"countUp": True}),
            text("n1-l", MARGIN, 448, 340, 60, "tests automatisés", 24, MUTED),
            text("n2", 472, 312, 340, 130, "32 ms", 104, TEXT, 900, line_height=1.0,
                 fx={"countUp": True}),
            text("n2-l", 472, 448, 340, 60, "latence de la vision", 24, MUTED),
            text("n3", 848, 312, 336, 130, "7/7", 104, OK, 900, line_height=1.0,
                 fx={"countUp": True}),
            text("n3-l", 848, 448, 336, 60, "contrôles de sécurité", 24, MUTED),
            text("proof-cmd", MARGIN, 576, RIGHT - MARGIN, 60,
                 "pytest -q  ·  scripts/bench_vision.py  ·  scripts/check_security.py",
                 22, FAINT, 400, font=MONO),
        ],
    }

    s_supervision = {
        "id": "supervision", "background": BG, "transition": "morph",
        "notes": notes("supervision",
                       "SCRIPT — Le poste de conduite : les courbes en temps réel, les alarmes à "
                       "traiter avec leur origine, et les commandes buzzer et LED. Un point de "
                       "conception : une seule connexion temps réel alimente toutes les pages, donc "
                       "aucun écran ne peut afficher autre chose qu'un autre. Et au-delà de dix "
                       "secondes sans mesure, l'interface l'annonce au lieu de figer une valeur."),
        "elements": head("SUPERVISION", "Le poste de conduite") + [
            image("shot-dash", MARGIN, 286, 1088, 336, "dashboard-banner", fit="cover"),
            text("sup-note", MARGIN, 640, RIGHT - MARGIN, 60,
                 "Une seule connexion temps réel ; au-delà de 10 s sans mesure, le site le dit.",
                 24, MUTED),
        ],
    }

    s_mco = {
        "id": "exploitation", "background": BG, "transition": "morph",
        "notes": notes("exploitation",
                       "SCRIPT — Deuxième écran, deuxième usage : Grafana. Il lit la même base, en "
                       "lecture seule, et il sert à comprendre et à se souvenir — l'historique des "
                       "capteurs et des alertes. Il porte aussi le maintien en condition "
                       "opérationnelle : CPU, RAM, disque, débit MQTT, journaux. Si le serveur qui "
                       "surveille tombe, plus personne ne surveille : c'est pour ça qu'on le "
                       "surveille lui aussi."),
        "elements": head("EXPLOITATION", "Comprendre et surveiller le serveur") + [
            image("shot-grafana", MARGIN, 286, 1088, 336, "grafana-banner", fit="cover"),
            text("mco-note", MARGIN, 640, RIGHT - MARGIN, 60,
                 "Lectures en lecture seule : historique des capteurs et santé du serveur.",
                 24, MUTED),
        ],
    }

    s_security = {
        "id": "securite", "background": BG, "transition": "morph",
        "notes": notes("securite",
                       "SCRIPT — Quatre repères. Le transport est chiffré en TLS 1.3, et le port en "
                       "clair est fermé. Les comptes sont séparés, et l'anonyme est refusé. Les "
                       "jetons sont distincts : celui de l'IA ne permet pas d'agir, et le code "
                       "opérateur, qui vit dans le navigateur, ne permet pas de fabriquer une fausse "
                       "alerte. Enfin, les conteneurs sont durcis. Le score n'est pas une opinion : "
                       "sept contrôles sur sept passent sur la pile réelle."),
        "elements": head("SÉCURITÉ", "Chiffré, authentifié, cloisonné") + [
            *card("s1", MARGIN, 292, 254, 240, "MQTTS", "TLS 1.3, port en clair fermé.", 26, 20),
            *card("s2", 374, 292, 254, 240, "Comptes et ACL", "Anonyme refusé ; le serveur ne peut "
                  "pas injecter de mesures.", 26, 20),
            *card("s3", 652, 292, 254, 240, "Jetons séparés", "L'IA alerte, l'opérateur agit. Jamais "
                  "les deux.", 26, 20),
            *card("s4", 930, 292, 254, 240, "Conteneurs durcis", "Non-root, lecture seule, base non "
                  "exposée.", 26, 20),
            text("sec-score", MARGIN, 566, RIGHT - MARGIN, 70,
                 "7 / 7 contrôles réussis sur la stack réelle", 30, OK, 700),
        ],
    }

    s_team = {
        "id": "equipe", "background": BG, "transition": "morph",
        "notes": notes("equipe",
                       "SCRIPT — Nous étions cinq, sur quatre filières : le développement, "
                       "l'intelligence artificielle, l'infrastructure et la cybersécurité. Chacun "
                       "possédait une brique, et la difficulté a été de faire tenir l'ensemble : "
                       "c'est le contrat d'interface — les topics MQTT et les messages de l'API — "
                       "qui nous a servi de frontière commune."),
        "elements": head("L'ÉQUIPE", "Cinq personnes, quatre filières") + [
            rect("e-rule1", MARGIN, 314, 6, 34, ACCENT, radius=3),
            text("e1", 122, 310, 430, 44, "Kephren BIBANG", 28, TEXT, 700),
            text("e1-p", 572, 314, 180, 40, "DEV", 24, ACCENT, 600),
            text("e1-d", 768, 314, 416, 64, "Dashboard React, API, firmware", 22, MUTED),
            rect("e-rule2", MARGIN, 382, 6, 34, ACCENT, radius=3),
            text("e2", 122, 378, 430, 44, "Mamadou SECK", 28, TEXT, 700),
            text("e2-p", 572, 382, 180, 40, "IA & Vision", 24, ACCENT, 600),
            text("e2-d", 768, 382, 416, 64, "YOLOv8n, maintenance prédictive", 22, MUTED),
            rect("e-rule3", MARGIN, 450, 6, 34, ACCENT, radius=3),
            text("e3", 122, 446, 430, 44, "Arsene ARAYI MBENGUE", 28, TEXT, 700),
            text("e3-p", 572, 450, 180, 40, "IA & Données", 24, ACCENT, 600),
            text("e3-d", 768, 450, 416, 64, "Intelligence artificielle et données", 22, MUTED),
            rect("e-rule4", MARGIN, 518, 6, 34, ACCENT, radius=3),
            text("e4", 122, 514, 430, 44, "Toure Ismahel O. L.", 28, TEXT, 700),
            text("e4-p", 572, 518, 180, 40, "INFRA", 24, ACCENT, 600),
            text("e4-d", 768, 518, 416, 64, "Docker, MQTTS, PostgreSQL, réseau", 22, MUTED),
            rect("e-rule5", MARGIN, 586, 6, 34, ACCENT, radius=3),
            text("e5", 122, 582, 430, 44, "Raoly KOUMOU", 28, TEXT, 700),
            text("e5-p", 572, 586, 180, 40, "CYBER", 24, ACCENT, 600),
            text("e5-d", 768, 586, 416, 64, "TLS, durcissement, audit", 22, MUTED),
        ],
    }

    s_limits = {
        "id": "limites", "background": BG, "transition": "morph",
        "notes": notes("limites",
                       "SCRIPT — Ce que nous n'avons pas fait, sans le cacher. Pas de capteurs "
                       "physiques : le boîtier est virtuel, mais il parle exactement le même "
                       "protocole. La vision tient l'exigence seule, et la dépasse dès qu'on ajoute "
                       "les visages. La webcam ne rentre pas dans Docker sous Windows. Et nous "
                       "partions de trois dépôts qu'il a fallu unifier."),
        "elements": head("LIMITES ASSUMÉES", "Ce qui n'est pas fait, et pourquoi") + [
            rect("l1-rule", MARGIN, 300, 40, 6, WARNING, radius=3),
            text("l1", MARGIN, 318, 400, 44, "Boîtier virtuel", 28, TEXT, 700),
            text("l1-d", 528, 318, 656, 64, "Même protocole que le firmware ; modèle validé sur données simulées.",
                 22, MUTED, line_height=1.35),
            rect("l2-rule", MARGIN, 394, 40, 6, WARNING, radius=3),
            text("l2", MARGIN, 412, 400, 44, "Latence", 28, TEXT, 700),
            text("l2-d", 528, 412, 656, 64, "Sous 100 ms avec YOLO seul ; au-delà avec les visages sur un PC chargé.",
                 22, MUTED, line_height=1.35),
            rect("l3-rule", MARGIN, 488, 40, 6, WARNING, radius=3),
            text("l3", MARGIN, 506, 400, 44, "Webcam hors Docker", 28, TEXT, 700),
            text("l3-d", 528, 506, 656, 64, "Docker Desktop n'accède pas à l'USB : vision et backend sur le PC.",
                 22, MUTED, line_height=1.35),
            rect("l4-rule", MARGIN, 582, 40, 6, WARNING, radius=3),
            text("l4", MARGIN, 600, 400, 44, "Trois dépôts", 28, TEXT, 700),
            text("l4-d", 528, 600, 656, 64, "Formats et topics différents, regroupés ensuite en un seul dépôt.",
                 22, MUTED, line_height=1.35),
        ],
    }

    s_next = {
        "id": "suite", "background": BG, "transition": "morph",
        "notes": notes("suite",
                       "SCRIPT — Chaque limite devient une piste. Le boîtier réel, d'abord : flasher "
                       "le firmware et réentraîner l'IA sur les mesures de la salle. La vision "
                       "ensuite : reconnaître une image sur deux, ou un modèle quantifié. Et le "
                       "chiffrement de bout en bout, avec un reverse proxy devant l'API. "
                       "Puis conclure : « anticiper, pas constater »."),
        "elements": head("AMÉLIORATIONS", "Ce que nous ferions ensuite") + [
            *card("n1", MARGIN, 300, 336, 250, "Boîtier réel", "Flasher le firmware et réentraîner "
                  "l'IA sur les mesures de la salle.", 28, 20),
            *card("n2", 472, 300, 336, 250, "Vision accélérée", "Une image sur deux, ou un modèle "
                  "quantifié.", 28, 20),
            *card("n3", 848, 300, 336, 250, "HTTPS de bout en bout", "Reverse proxy TLS devant "
                  "l'API et le dashboard.", 28, 20),
            text("next-note", MARGIN, 586, RIGHT - MARGIN, 70,
                 "Anticiper, pas constater — et le prouver par la mesure.", 30, TEXT, 600),
        ],
    }

    s_end = {
        "id": "merci", "background": BG, "transition": "morph",
        "notes": notes("merci",
                       "SCRIPT — Merci. Le dépôt est public, les commandes de vérification sont "
                       "dans le dossier. Nous prenons vos questions. Laisser le support affiché : "
                       "il sert de repère pendant les échanges."),
        "elements": [
            logo("logo", MARGIN, 96, 64),
            text("kicker", MARGIN, 188, 800, 26, "MERCI", 18, ACCENT, 700, letter_spacing=2.4),
            text("headline", MARGIN, 226, RIGHT - MARGIN, 150,
                 "Sentinel-X — la sécurité à la bordure", 60, TEXT, 800, line_height=1.1),
            rect("bar", MARGIN, 400, 240, 8, ACCENT),
            text("end-meta", MARGIN, 456, RIGHT - MARGIN, 120,
                 f"Consortium FORTEX — {tag}<br>github.com/Fortexworkshop/ia<br>"
                 "Workshop national EPSI Bac+4 · octobre 2026", 24, FAINT, 400, line_height=1.6),
            text("end-q", MARGIN, 600, RIGHT - MARGIN, 60, "Questions du jury", 30, ACCENT_STRONG, 600),
        ],
    }

    state = {
        "id": "state-modele", "stateOf": "predictif", "transition": "morph", "name": "SEUIL APPRIS",
        "background": BG,
        "notes": "Detail affiche a la demande (la fleche retourne au slide precedent). A dire : les "
                 "neuf indicateurs sont le niveau, la variabilite, la pente et la correlation "
                 "temperature/gaz. Le seuil n'est pas choisi : il est deduit des donnees normales. "
                 "Et l'alerte attend dix fenetres anormales consecutives pour ne pas sonner sur une "
                 "mesure isolee.",
        "elements": [
            logo("logo-head", RIGHT - 44, 66, 44),
            text("kicker", MARGIN, 72, 780, 26, "DÉTAIL — SEUIL APPRIS", 18, ACCENT, 700,
                 letter_spacing=2.4),
            text("headline", MARGIN, 106, RIGHT - MARGIN, 100,
                 "9 indicateurs par fenêtre de 30 mesures", 46, TEXT, 800, line_height=1.15),
            rect("bar", MARGIN, 246, 96, 6, ACCENT),
            text("state-body", MARGIN, 292, 640, 330,
                 "<b>Niveau</b> — température, humidité, gaz<br><br>"
                 "<b>Variabilité</b> — écart-type<br><br>"
                 "<b>Dynamique</b> — pentes<br><br>"
                 "<b>Couplage</b> — corrélation température / gaz",
                 26, MUTED, 400, line_height=1.5),
            text("state-right", 800, 292, RIGHT - 800, 330,
                 "<b>Le seuil est appris.</b><br><br>"
                 "Le sujet interdit les conditions statiques : il est déduit des données normales."
                 "<br><br>"
                 "L'alerte attend <b>10 fenêtres anormales consécutives</b>.",
                 24, MUTED, 400, line_height=1.45),
            rect("dismiss", 0, 0, WIDTH, HEIGHT, "rgba(0,0,0,0)", "none", 0, 0, link="predictif"),
        ],
    }

    return {
        "format": "bento/slides", "version": 1,
        "title": f"SENTINEL-X — FORTEX {tag}",
        "size": {"width": WIDTH, "height": HEIGHT},
        "theme": {"background": BG, "color": TEXT, "accent": ACCENT, "fontFamily": FONT},
        "assets": assets,
        "slides": [s_cover, s_problem, s_chain, s_vision, s_pred, s_proof, s_supervision,
                   s_mco, s_security, s_team, s_limits, s_next, s_end, state],
    }


# --------------------------------------------------------------------------- Ecriture

BLOCK = re.compile(
    r'(<script type="application/bento\+json" id="bento-doc">)(.*?)(</script>)', re.S)


def load_assets() -> dict[str, str]:
    """Captures du projet (WebP), embarquees en data URI : le deck reste autonome."""
    names = {"dashboard-banner": "dashboard-banner.webp", "vision": "vision.webp",
             "grafana-banner": "grafana-banner.webp"}
    for name in names.values():
        if not (ASSETS / name).exists():
            raise SystemExit(f"capture manquante : {ASSETS / name}")
    return {key: docassets.asset_uri(name) for key, name in names.items()}


def render_json(doc: dict) -> str:
    """JSON pret a inserer dans le bloc : tout `<` echappe en \\u003c."""
    return json.dumps(doc, ensure_ascii=True, indent=1).replace("<", "\\u003c")


def ensure_app(path: Path) -> None:
    if path.exists():
        return
    result = subprocess.run(["curl", "-fsSL", APP_URL, "-o", str(path)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"telechargement de l'application Bento impossible : {result.stderr.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--group", default="20", help="numero de groupe (<n> du nom de fichier)")
    parser.add_argument("--out", default=str(ROOT.parent / "rendus"), help="dossier de sortie")
    parser.add_argument("--json-only", action="store_true", help="n'ecrire que le JSON du document")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = build_doc(args.group, load_assets())
    payload = render_json(doc)

    stem = f"SENTINEL-X-G{args.group}" if args.group else "SENTINEL-X"
    json_path = out_dir / f"{stem}.bento.json"
    json_path.write_text(payload, encoding="utf-8")
    print(f"JSON : {json_path} ({json_path.stat().st_size // 1024} Ko, "
          f"{len(doc['slides'])} slides)")
    if args.json_only:
        return

    html_path = out_dir / f"{stem}.bento.html"
    ensure_app(html_path)
    source = html_path.read_text(encoding="utf-8")
    if not BLOCK.search(source):
        raise SystemExit(f"bloc #bento-doc introuvable dans {html_path}")
    html_path.write_text(BLOCK.sub(lambda m: m.group(1) + payload + m.group(3), source, count=1),
                         encoding="utf-8")
    print(f"DECK : {html_path} ({html_path.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
