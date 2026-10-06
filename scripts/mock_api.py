"""Fausse API pour tester l'envoi des alertes sans le backend de l'equipe DEV.

python scripts/mock_api.py              # ecoute sur http://localhost:8000/api/v1/alerts
puis dans un autre terminal :
$env:SENTINEL_API_URL="http://localhost:8000"; python scripts/sentinel_anomaly.py --simulate
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if self.path != "/api/v1/alerts":
            self.send_error(404)
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            alert = json.loads(body)
        except ValueError:
            self.send_error(400, "JSON invalide")
            return
        auth = "avec token" if self.headers.get("Authorization") else "sans token"
        print(f"<- alerte recue ({auth}) :\n{json.dumps(alert, indent=2, ensure_ascii=False)}")
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"created"}')

    def log_message(self, *args):
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Fausse API sur http://localhost:{args.port}/api/v1/alerts (Ctrl+C pour arreter)")
    try:
        HTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
