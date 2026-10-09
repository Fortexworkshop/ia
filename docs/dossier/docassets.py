"""Sources graphiques des rendus (dossier, poster, deck Bento, PowerPoint).

Le logo FORTEX n'existe qu'une fois, sous forme vectorielle (`assets/logo.svg`, meme trace que
`dev/dashboard/src/components/Icon.jsx`) ; les trois captures du projet sont en WebP. Ce module
evite de dupliquer la geometrie du logo et le chargement des images entre les trois generateurs
de rendus.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO_SVG = ASSETS / "logo.svg"

# Les couleurs du logo sont lues dans `assets/logo.svg` : le fichier peut porter la palette claire
# ou la sombre sans que les generateurs aient a le savoir (`logo_colors`).

# Le trace du logo n'utilise que ces commandes : pas de courbe, donc un parseur suffit.
_ARG_COUNT = {"M": 2, "L": 2, "H": 1, "V": 1}


def _logo_source() -> str:
    return LOGO_SVG.read_text(encoding="utf-8")


def logo_inner(stroke: str | None = None, accent: str | None = None) -> str:
    """Contenu du logo, recoloré, sans balise racine : a inserer dans un <svg> existant.

    Les couleurs de depart sont **lues dans le fichier**, pas supposees : recolorer le logo ne
    depend donc pas de la palette que `logo.svg` porte aujourd'hui. Sans argument, le logo est
    rendu tel quel.
    """
    source_stroke, source_accent = logo_colors()
    raw = _logo_source()
    inner = raw[raw.index(">", raw.index("<svg")) + 1 : raw.rindex("</svg>")].strip()
    inner = inner.replace(source_accent, accent or source_accent)
    return inner.replace(source_stroke, stroke or source_stroke)


def logo_markup(size: float, stroke: str | None = None, accent: str | None = None,
                x: float | None = None, y: float | None = None) -> str:
    """Element <svg> complet, autonome ou imbrique si x et y sont fournis."""
    pos = "" if x is None else f' x="{x}" y="{y}"'
    return (f'<svg{pos} viewBox="0 0 32 32" width="{size}" height="{size}" '
            f'role="img" aria-label="FORTEX">{logo_inner(stroke, accent)}</svg>')


def path_points(d: str) -> list[tuple[float, float]]:
    """Trace absolu d'un chemin compose de M, L, H, V (et de leurs formes relatives) et de z.

    Suffisant pour le logo, dont le trace ne comporte ni courbe ni arc.
    """
    tokens = re.findall(r"[MmLlHhVvZz]|-?\d*\.?\d+", d)
    points: list[tuple[float, float]] = []
    x = y = sx = sy = 0.0
    cmd = ""
    i = 0
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                if points[-1] != (sx, sy):  # z ne cree pas de segment nul
                    points.append((sx, sy))
                x, y = sx, sy
                continue
        relative, upper = cmd.islower(), cmd.upper()
        n = _ARG_COUNT[upper]
        args = [float(v) for v in tokens[i:i + n]]
        i += n
        if upper == "M":
            x, y = (x + args[0], y + args[1]) if relative else (args[0], args[1])
            sx, sy = x, y
            cmd = "l" if relative else "L"  # les paires suivantes sont des lineto
        elif upper == "L":
            x, y = (x + args[0], y + args[1]) if relative else (args[0], args[1])
        elif upper == "H":
            x = x + args[0] if relative else args[0]
        else:
            y = y + args[0] if relative else args[0]
        points.append((x, y))
    return points


def logo_parts() -> tuple[list[tuple[float, float]], list[tuple[float, float, float, bool]]]:
    """Trace et cercles du logo, dans le repere 32x32 de la source : rendu vectoriel natif."""
    raw = _logo_source()
    d = re.search(r'<path\s+d="([^"]+)"', raw)
    if not d:
        raise ValueError(f"trace introuvable dans {LOGO_SVG}")
    circles = []
    for tag in re.findall(r"<circle\b[^>]*/>", raw):
        values = {k: float(v) for k, v in re.findall(r'(\w+)="(-?[\d.]+)"', tag)}
        circles.append((values["cx"], values["cy"], values["r"], 'fill="none"' not in tag))
    return path_points(d.group(1)), circles


def logo_colors() -> tuple[str, str]:
    """Couleurs du trace et de l'accent, lues dans la source : elles peuvent changer."""
    raw = _logo_source()
    stroke = re.search(r'<path\b[^>]*stroke="([^"]+)"', raw)
    accent = re.search(r'<circle\b[^>]*fill="([^"]+)"', raw)
    if not (stroke and accent):
        raise ValueError(f"couleurs du logo introuvables dans {LOGO_SVG}")
    return stroke.group(1), accent.group(1)


def asset_uri(name: str, *, as_jpeg: bool = False) -> str:
    """Image des assets en data URI : les documents produits restent des fichiers autonomes.

    Chromium, qui produit les PDF, ne sait pas embarquer le WebP : il le redecompresse, et le
    poster quadruple de poids. Les documents destines a l'impression passent donc par `as_jpeg`,
    qui reencode la capture en JPEG le temps du rendu. Les fichiers de `assets/` restent, eux,
    en WebP et en SVG.
    """
    path = ASSETS / name
    suffix = path.suffix.lower()
    if as_jpeg:
        if suffix != ".webp":
            raise ValueError(f"seule une capture WebP peut etre reencodee : {name}")
        from io import BytesIO

        from PIL import Image

        buffer = BytesIO()
        Image.open(path).convert("RGB").save(buffer, "JPEG", quality=88, optimize=True)
        payload = buffer.getvalue()
        return "data:image/jpeg;base64," + base64.b64encode(payload).decode("ascii")
    mime = {".svg": "image/svg+xml", ".webp": "image/webp"}.get(suffix)
    if mime is None:
        raise ValueError(f"format non prevu pour un rendu : {name}")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")
