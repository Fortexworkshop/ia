"""Affiche la feuille de presence d'un jour et l'exporte en CSV.

python scripts/report.py                 # aujourd'hui
python scripts/report.py --day 2026-10-05 --csv data/presence_2026-10-05.csv
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from presence import config  # noqa: E402
from presence.attendance import AttendanceRegister  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--day", type=date.fromisoformat, default=date.today())
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()

    register = AttendanceRegister(config.ATTENDANCE_DB)
    students = register.students_for(args.day)
    print(f"Presence du {args.day.isoformat()} : {len(students)} eleve(s)")
    print(f"{'Eleve':<20}{'Arrivee':<10}{'Fin':<10}{'Pauses':<8}{'Min pause':<11}{'Min presence':<14}Statut")
    for student in students:
        s = register.summary(student, args.day)
        print(f"{s.student:<20}"
              f"{s.arrival.strftime('%H:%M') if s.arrival else '-':<10}"
              f"{s.departure.strftime('%H:%M') if s.departure else '-':<10}"
              f"{s.pauses:<8}{s.pause_minutes:<11}"
              f"{s.presence_minutes if s.presence_minutes is not None else '-':<14}{s.status.value}")
    if args.csv:
        print(f"CSV : {register.export_csv(args.day, args.csv)}")
    register.close()


if __name__ == "__main__":
    main()
