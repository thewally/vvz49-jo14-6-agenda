#!/usr/bin/env python3
"""
Agenda-feed voor ST SO Soest/VVZ'49 O14-6 (JO14-6).

Dit team is een combinatieteam (samenwerkingsteam) tussen SO Soest en
VVZ'49, administratief ondergebracht bij SO Soest. SO Soest's eigen
website (so-soest.nl) gebruikt een publieke "Sportlink Club" widget-API
(data.sportlink.com) om standen/programma te tonen. Die API is vrij
toegankelijk met de client_id die gewoon in hun publieke JS-bestand
staat (assets/js/global.js) -- geen account of betaalde Voetbal.nl-app
nodig.

We zoeken elke run opnieuw de teamcode/poulecode op (die wisselt
halverwege het seizoen als de KNVB een nieuwe competitiefase indeelt),
halen daarmee het programma op, en houden alles bij in matches.json
zodat wedstrijden uit afgelopen fases niet verdwijnen. Daarna wordt
matches.ics gegenereerd voor abonnement in Google Calendar.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

API_BASE = "https://data.sportlink.com"
CLIENT_ID = "***REMOVED***"  # publiek, uit so-soest.nl/assets/js/global.js
TEAM_NAME = "ST SO Soest/VVZ'49 O14-6"

TZ_AMS = ZoneInfo("Europe/Amsterdam")

STATE_PATH = Path(__file__).parent / "matches.json"
ICS_PATH = Path(__file__).parent / "matches.ics"


def api_get(article: str, **params) -> object:
    params["client_id"] = CLIENT_ID
    url = f"{API_BASE}/{article}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; jo14-6-agenda/1.0)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_poulecode() -> int:
    teams = api_get("teams")
    matches = [t for t in teams if t.get("teamnaam") == TEAM_NAME and t.get("poulecode")]
    if not matches:
        raise RuntimeError(f"Team '{TEAM_NAME}' niet gevonden in teams-lijst (competitiefase-overgang?).")
    # Er kunnen meerdere regels zijn (competitie + beker); neem de regulier-competitie.
    for t in matches:
        if t.get("competitiesoort") == "regulier":
            return t["poulecode"]
    return matches[0]["poulecode"]


def fetch_schedule(poulecode: int) -> list[dict]:
    return api_get("poule-programma", poulecode=poulecode, aantaldagen=365, eigenwedstrijden="ja")


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True))


def merge(state: dict, matches: list[dict], now_iso: str) -> dict:
    for m in matches:
        uid = str(m["wedstrijdcode"])
        entry = state.get(uid, {})
        entry.update(
            {
                "wedstrijddatum": m["wedstrijddatum"],
                "thuisteam": m["thuisteam"],
                "uitteam": m["uitteam"],
                "accommodatie": m.get("accommodatie") or "",
                "plaats": m.get("plaats") or "",
                "status": m.get("status") or "",
                "wedstrijdnummer": m.get("wedstrijdnummer") or "",
            }
        )
        entry["last_seen"] = now_iso
        entry.setdefault("first_seen", now_iso)
        state[uid] = entry
    return state


def ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def build_ics(state: dict, now: datetime) -> str:
    cutoff = (now - timedelta(days=60)).date()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//vvz49-jo14-6-agenda//NL",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:ST SO Soest/VVZ'49 O14-6",
    ]
    for uid, entry in sorted(state.items(), key=lambda kv: kv[1]["wedstrijddatum"]):
        start_local = datetime.fromisoformat(entry["wedstrijddatum"]).astimezone(TZ_AMS)
        if start_local.date() < cutoff:
            continue
        end_local = start_local + timedelta(minutes=90)
        start_utc = start_local.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        end_utc = end_local.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        summary = f"{entry['thuisteam']} - {entry['uitteam']}"
        status = entry["status"]
        if status and "afgelast" in status.lower():
            summary = f"AFGELAST: {summary}"

        location = ", ".join(p for p in [entry["accommodatie"], entry["plaats"]] if p)
        desc_parts = [p for p in [f"Status: {status}" if status else "", f"Wedstrijdnummer: {entry['wedstrijdnummer']}" if entry["wedstrijdnummer"] else ""] if p]

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}@vvz49-jo14-6",
            f"DTSTAMP:{now.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start_utc}",
            f"DTEND:{end_utc}",
            f"SUMMARY:{ics_escape(summary)}",
        ]
        if location:
            lines.append(f"LOCATION:{ics_escape(location)}")
        if desc_parts:
            lines.append(f"DESCRIPTION:{ics_escape(chr(10).join(desc_parts))}")
        if status and "afgelast" in status.lower():
            lines.append("STATUS:CANCELLED")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> int:
    now = datetime.now(TZ_AMS)
    try:
        poulecode = find_poulecode()
        matches = fetch_schedule(poulecode)
    except (urllib.error.URLError, RuntimeError) as exc:
        print(f"Kon programma niet ophalen: {exc}", file=sys.stderr)
        return 0  # laat matches.json/matches.ics ongewijzigd staan

    print(f"Poulecode {poulecode}: {len(matches)} wedstrijd(en) opgehaald.")

    state = load_state()
    state = merge(state, matches, now.isoformat())
    save_state(state)

    ics = build_ics(state, now)
    ICS_PATH.write_text(ics)
    print(f"matches.ics geschreven met {ics.count('BEGIN:VEVENT')} wedstrijd(en) totaal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
