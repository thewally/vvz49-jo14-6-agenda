#!/usr/bin/env python3
"""
Agenda-feed voor ST SO Soest/VVZ'49 O14-6 (JO14-6).

Dit team is een combinatieteam (samenwerkingsteam) tussen SO Soest en
VVZ'49, administratief ondergebracht bij SO Soest. SO Soest's eigen
website (so-soest.nl) gebruikt een publieke "Sportlink Club" widget-API
(data.sportlink.com) om standen/programma te tonen -- geen account of
betaalde Voetbal.nl-app nodig. De bijbehorende client_id staat in de
GitHub Actions repository secret SPORTLINK_CLIENT_ID (lokaal: zet 'm
in de omgevingsvariabele met dezelfde naam) in plaats van in de code.

We zoeken elke run opnieuw de teamcode op (stabieler dan poulecode, die
halverwege het seizoen wisselt als de KNVB een nieuwe competitiefase
indeelt) en halen daarmee het per-team programma op. Dat bevat naast
datum/tijd ook de officiele verzameltijd, scheidsrechter en veld -- dus
we zetten per wedstrijd twee losse agenda-items: "Verzamelen" en de
wedstrijd zelf. Per wedstrijd wordt ook het adres van de accommodatie
opgehaald (wedstrijd-informatie) zodat de LOCATION een kant-en-klare
Google Maps-link krijgt, in plaats van te gokken op basis van de
sportparknaam. Alles wordt bijgehouden in matches.json zodat wedstrijden
niet verdwijnen zodra een fase/poule wisselt.

Daarnaast worden handmatig bijgehouden activiteiten (trainingen,
toernooien, teamuitjes, ...) uit overige-activiteiten.json toegevoegd.
Zie README.md voor het formaat. Daarna wordt matches.ics gegenereerd voor
abonnement in Google Calendar.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

API_BASE = "https://data.sportlink.com"
CLIENT_ID = os.environ.get("SPORTLINK_CLIENT_ID")
TEAM_NAME = "ST SO Soest/VVZ'49 O14-6"
UID_NAMESPACE = "vvz49-jo14-6"

# Label achter de wedstrijdtitel, bv. "[UIT] Kampong O14-5 (JO14-6)".
AGENDA_LABEL = "JO14-6"

# VVZ'49's eigen accommodatie (Sportpark Zonnegloren) -- vast vertrekpunt
# voor het carpoolen bij uitwedstrijden. De KNVB noemt de accommodatie zelf
# "Sportpark Zonnegloren", maar Google Maps/Calendar herkent de plek -- met
# foto en kaartje -- pas onder de officiele clubnaam.
THUIS_ACCOMMODATIE_KNVB = "Sportpark Zonnegloren"
THUIS_CLUBNAAM = "Sportvereniging Vrienden van Zonnegloren"
THUIS_STRAAT = "Eemweg 1"
THUIS_PLAATS = "3764DG SOEST"
UIT_VERZAMELPLEK = f"{THUIS_CLUBNAAM} (parkeerplaats), {THUIS_STRAAT}, {THUIS_PLAATS}"


def display_accommodatie(naam: str) -> str:
    """Vervangt de KNVB-naam van VVZ'49's eigen accommodatie door de naam
    zoals Google Maps 'm herkent, zodat Google Calendar er een kaartje met
    foto bij toont. Voor andere sportparken (uitwedstrijden) blijft de
    KNVB-naam staan -- daar is geen betrouwbare 1-op-1 vertaling van bekend."""
    return THUIS_CLUBNAAM if naam == THUIS_ACCOMMODATIE_KNVB else naam

TZ_AMS = ZoneInfo("Europe/Amsterdam")

STATE_PATH = Path(__file__).parent / "matches.json"
ICS_PATH = Path(__file__).parent / "matches.ics"
ACTIVITEITEN_PATH = Path(__file__).parent / "overige-activiteiten.json"


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


def fetch_accommodatie(wedstrijdcode: int) -> dict:
    """Haalt het exacte adres + kant-en-klare routeplanner-link op voor een
    wedstrijd. Betrouwbaarder dan zelf raden op basis van de sportparknaam."""
    try:
        info = api_get("wedstrijd-informatie", wedstrijdcode=wedstrijdcode)
        return info.get("accommodatie") or {}
    except (urllib.error.URLError, KeyError, ValueError):
        return {}


def maps_url(naam: str, straat: str, plaats: str) -> str:
    # Bij voorkeur het exacte adres (straat + postcode/plaats); zonder dat
    # valt terug op de sportparknaam -- dan is het inderdaad een beetje
    # gissen, maar beter dan geen link.
    query = ", ".join(p for p in [straat, plaats] if p) or naam
    if not query:
        return ""
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query)


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True))


def merge(state: dict, matches: list[dict], now_iso: str) -> dict:
    for m in matches:
        uid = str(m["wedstrijdcode"])
        accommodatie = fetch_accommodatie(m["wedstrijdcode"])
        entry = state.get(uid, {})
        entry.update(
            {
                "wedstrijddatum": m["wedstrijddatum"],
                "thuisteam": m["thuisteam"],
                "uitteam": m["uitteam"],
                "accommodatie": m.get("accommodatie") or "",
                "veld": m.get("veld") or "",
                "plaats": m.get("plaats") or "",
                "straat": accommodatie.get("straat") or "",
                "adresplaats": accommodatie.get("plaats") or "",
                "status": m.get("status") or "",
                "wedstrijdnummer": m.get("wedstrijdnummer") or "",
                "verzameltijd": m.get("verzameltijd") or "",
                "vertrektijd": m.get("vertrektijd") or "",
                "scheidsrechter": m.get("scheidsrechter") or "",
            }
        )
        entry["last_seen"] = now_iso
        entry.setdefault("first_seen", now_iso)
        state[uid] = entry
    return state


# ---------------------------------------------------------------------------
# Overige activiteiten (handmatig, uit overige-activiteiten.json)
# ---------------------------------------------------------------------------

def fout(msg: str) -> SystemExit:
    return SystemExit(f"{ACTIVITEITEN_PATH.name}: {msg}")


def load_activiteiten() -> list[dict]:
    if not ACTIVITEITEN_PATH.exists():
        return []
    try:
        data = json.loads(ACTIVITEITEN_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise fout(f"geen geldige JSON ({exc})")
    if not isinstance(data, list):
        raise fout("moet een lijst [ ... ] met activiteiten zijn")
    gezien = set()
    for act in data:
        if not isinstance(act, dict):
            raise fout("elke activiteit moet een object { ... } zijn")
        act_id = act.get("id")
        if not act_id or not re.fullmatch(r"[A-Za-z0-9_-]+", str(act_id)):
            raise fout(f"ongeldig of ontbrekend 'id' bij {act!r} (alleen letters, cijfers, - en _)")
        if act_id in gezien:
            raise fout(f"id '{act_id}' komt meerdere keren voor")
        gezien.add(act_id)
        if not act.get("titel") or not act.get("datum"):
            raise fout(f"activiteit '{act_id}' mist 'titel' of 'datum'")
    return data


def activiteit_events(act: dict, dtstamp: str, cutoff: date, horizon: date) -> list[str]:
    act_id = act["id"]
    try:
        eerste = date.fromisoformat(act["datum"])
        einddatum = date.fromisoformat(act["einddatum"]) if act.get("einddatum") else eerste
        tot_str = act.get("herhalen_tot") or act.get("wekelijks_tot")  # wekelijks_tot = oude naam
        tot = date.fromisoformat(tot_str) if tot_str else None
        behalve = {date.fromisoformat(d) for d in act.get("behalve", [])}
        begintijd = time.fromisoformat(act["begintijd"]) if act.get("begintijd") else None
        eindtijd = time.fromisoformat(act["eindtijd"]) if act.get("eindtijd") else None
    except (ValueError, TypeError) as exc:
        raise fout(f"activiteit '{act_id}': ongeldige datum/tijd ({exc}); gebruik JJJJ-MM-DD en UU:MM")

    duur_dagen = (einddatum - eerste).days
    if duur_dagen < 0:
        raise fout(f"activiteit '{act_id}': 'einddatum' ligt voor 'datum'")
    elke_weken = act.get("elke_weken", 1)
    if not isinstance(elke_weken, int) or isinstance(elke_weken, bool) or elke_weken < 1:
        raise fout(f"activiteit '{act_id}': 'elke_weken' moet een heel getal >= 1 zijn")
    # Herhalend zodra er een einddatum voor de reeks of een interval is opgegeven.
    # Zonder 'herhalen_tot' loopt de reeks door tot 'horizon' (ca. een jaar
    # vooruit); omdat de feed elke dag opnieuw wordt opgebouwd schuift dat mee.
    herhalend = tot is not None or "elke_weken" in act
    if tot is None:
        tot = horizon if herhalend else eerste
    elif tot < eerste:
        raise fout(f"activiteit '{act_id}': 'herhalen_tot' ligt voor 'datum'")

    afgelast = bool(act.get("afgelast"))
    summary = f"AFGELAST: {act['titel']}" if afgelast else act["titel"]
    adres = act.get("adres") or ""
    locatie = ", ".join(p for p in [act.get("locatie") or "", adres] if p)
    url = act.get("url") or maps_url(act.get("locatie") or "", adres, "")
    description = "\n".join(p for p in [act.get("omschrijving") or "", f"Route: {url}" if url else ""] if p)

    lines: list[str] = []
    dag = eerste
    while dag <= tot:
        if dag not in behalve and dag + timedelta(days=duur_dagen) >= cutoff:
            uid = f"activiteit-{act_id}-{dag:%Y%m%d}" if herhalend else f"activiteit-{act_id}"
            if begintijd:
                start = datetime.combine(dag, begintijd, TZ_AMS)
                eind = (datetime.combine(dag + timedelta(days=duur_dagen), eindtijd, TZ_AMS)
                        if eindtijd else start + timedelta(hours=1))
                if eind <= start:
                    raise fout(f"activiteit '{act_id}': eindtijd ligt niet na begintijd")
            else:
                # Hele dag; DTEND is bij VALUE=DATE exclusief (dag erna).
                start = dag
                eind = dag + timedelta(days=duur_dagen + 1)
            lines += vevent(
                uid=f"{uid}@{UID_NAMESPACE}",
                dtstamp=dtstamp,
                start=start,
                end=eind,
                summary=summary,
                location=locatie,
                description=description,
                url=url,
                cancelled=afgelast,
            )
        dag += timedelta(weeks=elke_weken)
    return lines


# ---------------------------------------------------------------------------
# ICS
# ---------------------------------------------------------------------------

def ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def ics_moment(prop: str, value: date) -> str:
    # Let op: datetime is een subklasse van date, dus eerst op datetime testen.
    if isinstance(value, datetime):
        return f"{prop}:{value.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    return f"{prop};VALUE=DATE:{value.strftime('%Y%m%d')}"


def vevent(uid: str, dtstamp: str, start: date, end: date, summary: str, location: str = "", description: str = "", url: str = "", cancelled: bool = False) -> list[str]:
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        ics_moment("DTSTART", start),
        ics_moment("DTEND", end),
        f"SUMMARY:{ics_escape(summary)}",
    ]
    if location:
        lines.append(f"LOCATION:{ics_escape(location)}")
    if description:
        lines.append(f"DESCRIPTION:{ics_escape(description)}")
    if url:
        lines.append(f"URL:{url}")
    if cancelled:
        lines.append("STATUS:CANCELLED")
    lines.append("END:VEVENT")
    return lines


UIT_MAPS_URL = maps_url(THUIS_CLUBNAAM, THUIS_STRAAT, THUIS_PLAATS)


def build_ics(state: dict, activiteiten: list[dict], now: datetime) -> str:
    cutoff = (now - timedelta(days=60)).date()
    horizon = (now + timedelta(days=365)).date()
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
        accommodatie_display = display_accommodatie(entry["accommodatie"])
        location = accommodatie_display
        match_maps_url = maps_url(accommodatie_display, entry["straat"], entry["adresplaats"])

        # Titel toont alleen richting + tegenstander, bv. "[UIT] Kampong O14-5
        # (JO14-6)" -- de eigen teamnaam staat al in de agenda-titel zelf.
        is_thuis = entry["thuisteam"] == TEAM_NAME
        richting = "THUIS" if is_thuis else "UIT"
        tegenstander = entry["uitteam"] if is_thuis else entry["thuisteam"]
        summary = f"[{richting}] {tegenstander} ({AGENDA_LABEL})"
        if cancelled:
            summary = f"AFGELAST: {summary}"

        desc_parts = [
            f"Status: {entry['status']}" if entry["status"] else "",
            f"Veld: {entry['veld']}" if entry["veld"] else "",
            f"Plaats: {entry['plaats']}" if entry["plaats"] else "",
            f"Scheidsrechter: {entry['scheidsrechter']}" if entry["scheidsrechter"] else "",
            f"Wedstrijdnummer: {entry['wedstrijdnummer']}" if entry["wedstrijdnummer"] else "",
            f"Route: {match_maps_url}" if match_maps_url else "",
        ]
        description = "\n".join(p for p in desc_parts if p)

        # Verzamelen: bij thuiswedstrijden is dat "verzameltijd" (verzamelen in de
        # kleedkamer op de eigen accommodatie); bij uitwedstrijden publiceert de
        # KNVB in plaats daarvan een "vertrektijd" (vertrek vanaf de parkeerplaats
        # van VVZ'49, het vertrekpunt om samen naartoe te rijden).
        gather_time = entry["verzameltijd"] if is_thuis else entry["vertrektijd"]
        if gather_time and not cancelled:
            vh, vm = (int(x) for x in gather_time.split(":"))
            gather_start = kickoff.replace(hour=vh, minute=vm, second=0, microsecond=0)
            if gather_start < kickoff:
                gather_location = f"Kleedkamer, {location}" if is_thuis else UIT_VERZAMELPLEK
                gather_url = match_maps_url if is_thuis else UIT_MAPS_URL
                lines += vevent(
                    uid=f"{uid}-verzamelen@{UID_NAMESPACE}",
                    dtstamp=dtstamp,
                    start=gather_start,
                    end=kickoff,
                    summary=f"Verzamelen: [{richting}] {tegenstander} ({AGENDA_LABEL})",
                    location=gather_location,
                    url=gather_url,
                )

        lines += vevent(
            uid=f"{uid}@{UID_NAMESPACE}",
            dtstamp=dtstamp,
            start=kickoff,
            end=kickoff + timedelta(minutes=90),
            summary=summary,
            location=location,
            description=description,
            url=match_maps_url,
            cancelled=cancelled,
        )

    for act in activiteiten:
        lines += activiteit_events(act, dtstamp, cutoff, horizon)

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> int:
    if not CLIENT_ID:
        print("SPORTLINK_CLIENT_ID ontbreekt (zet 'm als env var of repository secret).", file=sys.stderr)
        return 1

    # Eerst de activiteiten valideren: een tikfout moet de run duidelijk laten
    # falen (GitHub stuurt dan een mail) in plaats van stilletjes items te missen.
    activiteiten = load_activiteiten()

    now = datetime.now(TZ_AMS)
    state = load_state()
    try:
        teamcode = find_teamcode()
        matches = fetch_schedule(teamcode)
        print(f"Teamcode {teamcode}: {len(matches)} wedstrijd(en) opgehaald.")
        state = merge(state, matches, now.isoformat())
        save_state(state)
    except (urllib.error.URLError, RuntimeError) as exc:
        # Sportlink onbereikbaar: bestaande wedstrijden uit matches.json houden,
        # maar de agenda wel opnieuw opbouwen zodat gewijzigde activiteiten
        # toch doorkomen.
        print(f"Kon programma niet ophalen: {exc} -- bestaande wedstrijden worden gebruikt.", file=sys.stderr)

    ics = build_ics(state, activiteiten, now)
    ICS_PATH.write_text(ics)
    print(f"matches.ics geschreven met {ics.count('BEGIN:VEVENT')} agenda-item(en) totaal "
          f"({len(activiteiten)} overige activiteit(en) in {ACTIVITEITEN_PATH.name}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
