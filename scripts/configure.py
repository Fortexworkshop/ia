"""Configure tout le projet en une fois (secrets, TLS, comptes MQTT, .env, firmware).

python scripts/configure.py                              # IP du PC serveur : 192.168.10.1
python scripts/configure.py --server-ip 192.168.10.1 --wifi-ssid FORTEX-TABLE --wifi-password xxx

Idempotent : un secret ou un fichier deja present n'est jamais regenere.
Prerequis : Git Bash (scripts de certificats) et Docker demarre (comptes MQTT).

Produit (tous ignores par git) :
  infra/.env, infra/certs/, infra/mosquitto/config/passwd, infra/mqtt-users.env
  .env (IA), dev/dashboard/.env, firmware/sentinel-x/include/sentinel_config.h
"""

import argparse
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INFRA = ROOT / "infra"
DASHBOARD = ROOT / "dev" / "dashboard"
FIRMWARE = ROOT / "firmware" / "sentinel-x" / "include"


def step(text: str) -> None:
    print(f"\n==> {text}")


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines()
                if "=" in line and not line.lstrip().startswith("#"))


def set_env(path: Path, values: dict[str, str], overwrite: bool = False) -> None:
    """Ecrit les valeurs ; sans overwrite, ne remplace que les valeurs vides ou CHANGE_ME."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    done = set()
    for i, line in enumerate(lines):
        key, sep, current = line.partition("=")
        if sep and not line.lstrip().startswith("#") and key in values:
            done.add(key)
            if overwrite or current.strip() in ("", "CHANGE_ME"):
                lines[i] = f"{key}={values[key]}"
    lines += [f"{k}={v}" for k, v in values.items() if k not in done]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_bash() -> str | None:
    # Git Bash en priorite : sous Windows, "bash" peut designer WSL, sans acces a ce dossier
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


def run_bash(script: Path, *args: str) -> bool:
    bash = find_bash()
    if not bash:
        print("[!] Git Bash introuvable : installer Git for Windows, puis relancer")
        return False
    return subprocess.run([bash, script.relative_to(INFRA).as_posix(), *args], cwd=INFRA).returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server-ip", default="192.168.10.1", help="IP du PC serveur sur le reseau de la table")
    parser.add_argument("--wifi-ssid", default="", help="Wi-Fi de la table (firmware)")
    parser.add_argument("--wifi-password", default="")
    args = parser.parse_args()
    ok = True

    step("Secrets de l'infra (infra/.env)")
    infra_env = INFRA / ".env"
    if not infra_env.exists():
        shutil.copy(INFRA / ".env.example", infra_env)
    set_env(infra_env, {"POSTGRES_PASSWORD": secrets.token_urlsafe(18),
                        "API_TOKEN": secrets.token_urlsafe(24), "IA_DIR": "..",
                        "DASHBOARD_TOKEN": secrets.token_urlsafe(24),
                        "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(12),
                        "GRAFANA_DB_PASSWORD": secrets.token_urlsafe(18)})
    print("ok")

    step(f"Certificats TLS (CA FORTEX + broker pour {args.server_ip})")
    if (INFRA / "certs" / "ca.crt").exists():
        print("deja presents (supprimer infra/certs/ pour les regenerer)")
    else:
        ok &= run_bash(INFRA / "scripts" / "gen-certs.sh", args.server_ip)

    step("Comptes MQTT (esp8266, serveur)")
    if (INFRA / "mosquitto" / "config" / "passwd").exists() and (INFRA / "mqtt-users.env").exists():
        print("deja presents")
    else:
        ok &= run_bash(INFRA / "scripts" / "gen-mqtt-users.sh")
    users = read_env(INFRA / "mqtt-users.env")
    infra = read_env(infra_env)
    if users:
        set_env(infra_env, {"SERVEUR_MQTT_PASSWORD": users["SENTINEL_MQTT_PASSWORD"],
                            "ESP_MQTT_PASSWORD": users["ESP_MQTT_PASSWORD"]}, overwrite=True)

    step("Configuration IA / backend (.env)")
    ia_env = ROOT / ".env"
    if not ia_env.exists():
        shutil.copy(ROOT / ".env.example", ia_env)
    values = {"SENTINEL_API_URL": "http://localhost:8080", "SENTINEL_API_TOKEN": infra.get("API_TOKEN", ""),
              "FORTEX_DASHBOARD_TOKEN": infra.get("DASHBOARD_TOKEN", ""),
              "SENTINEL_MQTT_HOST": "localhost", "SENTINEL_MQTT_PORT": "8883",
              "SENTINEL_MQTT_CA_CERT": "infra/certs/ca.crt", "SENTINEL_MQTT_USER": "serveur",
              "ESP_MQTT_USER": "esp8266"}
    if users:
        values |= {"SENTINEL_MQTT_PASSWORD": users["SENTINEL_MQTT_PASSWORD"],
                   "ESP_MQTT_PASSWORD": users["ESP_MQTT_PASSWORD"]}
    set_env(ia_env, values, overwrite=True)
    print("ok")

    step("Dashboard (dev/dashboard/.env)")
    dash_env = DASHBOARD / ".env"
    if DASHBOARD.exists():
        set_env(dash_env, {"VITE_API_URL": "http://localhost:8080",
                           "VITE_CAMERA_URL": "http://localhost:8081/video"})
        # Le code operateur n'est PAS ecrit ici : une variable VITE_* est compilee dans le JavaScript,
        # donc lisible par quiconque ouvre la page (OWASP A07). L'operateur le saisit a la connexion.
        set_env(dash_env, {"VITE_DASHBOARD_TOKEN": ""}, overwrite=True)
    print("ok")
    print(f"Code operateur du dashboard (a saisir a la connexion) : DASHBOARD_TOKEN dans {INFRA / '.env'}")

    step("Firmware ESP8266 (include/sentinel_config.h)")
    config_h = FIRMWARE / "sentinel_config.h"
    ca = INFRA / "certs" / "ca.crt"
    if config_h.exists():
        print("deja present (le modifier a la main si besoin)")
    elif users and ca.exists():
        text = (FIRMWARE / "sentinel_config.example.h").read_text(encoding="utf-8")
        text = text.replace('"192.168.10.1"', f'"{args.server_ip}"')
        text = text.replace('#define MQTT_PASSWORD "change-moi"', f'#define MQTT_PASSWORD "{users["ESP_MQTT_PASSWORD"]}"')
        text = text.replace("-----BEGIN CERTIFICATE-----\nREMPLACER_PAR_LE_CONTENU_DE_ca.crt\n-----END CERTIFICATE-----",
                            ca.read_text(encoding="utf-8").strip())
        if args.wifi_ssid:
            text = text.replace('#define WIFI_SSID "FORTEX-TABLE"', f'#define WIFI_SSID "{args.wifi_ssid}"')
            text = text.replace('#define WIFI_PASSWORD "change-moi"', f'#define WIFI_PASSWORD "{args.wifi_password}"')
        config_h.write_text(text, encoding="utf-8")
        print("cree" + ("" if args.wifi_ssid else " (renseigner WIFI_SSID / WIFI_PASSWORD)"))
    else:
        print("[!] certificats ou comptes MQTT manquants : relancer apres les avoir generes")
        ok = False

    print("\nConfiguration terminee." if ok else "\nConfiguration incomplete : voir les messages [!] ci-dessus.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
