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

We zoeken elke run opnieuw de teamcode op (stabieler dan poulecode, die
halverwege het seizoen wisselt als de KNVB een nieuwe competitiefase
indeelt) en halen daarmee het per-team programma op. Dat bevat naast
datum/tijd ook de officiele verzameltijd, scheidsrechter en veld -- dus
we zetten per wedstrijd twee losse agenda-items: "Verzamelen" en de
wedstrijd zelf. Alles wordt bijgehouden in matches.json zodat
wedstrijden niet verdwijnen zodra een fase/poule wisselt. Daarna wordt
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


def find_teamcode() -> int:
    teams = api_get("teams")
    matches = [t for t in teams if t.get("teamnaam") == TEAM_NAME and t.get("teamsoort") == "bond"]
    if not matches:
        raise RuntimeError(f"Team '{TEAM_NAME}' niet gevonden in teams-lijst.")
    return matches[0]["teamcode"]


def fetch_schedule(teamcode: int) -> list[dict]:
    return api_get("programma", teamcode=teamcode, aantaldagen=365, aantalregels=200, eigenwedstrijden="JA")


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
                "veld": m.get("veld") or "",
                "plaats": m.get("plaats") or "",
                "status": m.get("status") or "",
                "wedstrijdnummer": m.get("wedstrijdnummer") or "",
                "verzameltijd": m.get("verzameltijd") or "",
                "scheidsrechter": m.get("scheidsrechter") or "",
            }
        )
        entry["last_seen"] = now_iso
        entry.setdefault("first_seen", now_iso)
        state[uid] = entry
    return state


def ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def vevent(uid: str, dtstamp: str, start: datetime, end: datetime, summary: str, location: str = "", description: str = "", cancelled: bool = False) -> list[str]:
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{start.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{end.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"SUMMARY:{ics_escape(summary)}",
    ]
    if location:
        lines.append(f"LOCATION:{ics_escape(location)}")
    if description:
        lines.append(f"DESCRIPTION:{ics_escape(description)}")
    if cancelled:
        lines.append("STATUS:CANCELLED")
    lines.append("END:VEVENT")
    return lines


def build_ics(state: dict, now: datetime) -> str:
    cutoff = (now - timedelta(days=60)).date()
    dtstamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//vvz49-jo14-6-agenda//NL",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:ST SO Soest/VVZ'49 O14-6",
    ]
    for uid, entry in sorted(state.items(), key=lambda kv: kv[1]["wedstrijddatum"]):
        kickoff = datetime.fromisoformat(entry["wedstrijddatum"]).astimezone(TZ_AMS)
        if kickoff.date() < cutoff:
            continue

        cancelled = bool(entry["status"]) and "afgelast" in entry["status"].lower()
        location = ", ".join(p for p in [entry["accommodatie"], entry["veld"], entry["plaats"]] if p)
        summary = f"{entry['thuisteam']} - {entry['uitteam']}"
        if cancelled:
            summary = f"AFGELAST: {summary}"

        desc_parts = [
            f"Status: {entry['status']}" if entry["status"] else "",
            f"Scheidsrechter: {entry['scheidsrechter']}" if entry["scheidsrechter"] else "",
            f"Wedstrijdnummer: {entry['wedstrijdnummer']}" if entry["wedstrijdnummer"] else "",
        ]
        description = "\n".join(p for p in desc_parts if p)

        # Verzamelen: van verzameltijd tot aanvangstijd (alleen als bekend en voor kickoff ligt).
        if entry["verzameltijd"] and not cancelled:
            vh, vm = (int(x) for x in entry["verzameltijd"].split(":"))
            gather_start = kickoff.replace(hour=vh, minute=vm, second=0, microsecond=0)
            if gather_start < kickoff:
                lines += vevent(
                    uid=f"{uid}-verzamelen@vvz49-jo14-6",
                    dtstamp=dtstamp,
                    start=gather_start,
                    end=kickoff,
                    summary=f"Verzamelen: {entry['thuisteam']} - {entry['uitteam']}",
                    location=location,
                )

        lines += vevent(
            uid=f"{uid}@vvz49-jo14-6",
            dtstamp=dtstamp,
            start=kickoff,
            end=kickoff + timedelta(minutes=90),
            summary=summary,
            location=location,
            description=description,
            cancelled=cancelled,
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> int:
    now = datetime.now(TZ_AMS)
    try:
        teamcode = find_teamcode()
        matches = fetch_schedule(teamcode)
    except (urllib.error.URLError, RuntimeError) as exc:
        print(f"Kon programma niet ophalen: {exc}", file=sys.stderr)
        return 0  # laat matches.json/matches.ics ongewijzigd staan

    print(f"Teamcode {teamcode}: {len(matches)} wedstrijd(en) opgehaald.")

    state = load_state()
    state = merge(state, matches, now.isoformat())
    save_state(state)

    ics = build_ics(state, now)
    ICS_PATH.write_text(ics)
    print(f"matches.ics geschreven met {ics.count('BEGIN:VEVENT')} agenda-item(en) totaal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
