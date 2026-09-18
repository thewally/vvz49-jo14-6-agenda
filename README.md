# Speelagenda VVZ'49 JO14-6

Automatisch bijgewerkte agenda-feed (.ics) voor **ST SO Soest/VVZ'49 O14-6**
(de combinatie tussen SO Soest en VVZ'49), voor gebruik als abonnement in
Google Calendar (of Apple/Outlook).

## Wat staat er in de agenda

- **Verzamelen: …** — van verzameltijd tot aanvangstijd
- **Speeltijden**
- **Thuisteam - Uitteam** — de wedstrijd zelf, incl. scheidsrechter en veld
- **Overige activiteiten** — trainingen, toernooien, teamuitjes

## Hoe te gebruiken in Google Calendar

1. Ga naar https://calendar.google.com/calendar/r/settings/addbyurl
2. Plak de URL: `https://thewally.github.io/vvz49-jo14-6-agenda/matches.ics`
3. Klik op **Agenda toevoegen**

De agenda wordt elke ochtend en avond automatisch bijgewerkt. Google
Calendar ververst de feed vervolgens op zijn eigen tempo (meestal binnen
12-24 uur).

## Hoe te gebruiken in Outlook

**Outlook.com (web)**

1. Ga naar https://outlook.live.com/calendar/ en klik op **Agenda toevoegen**
2. Kies **Abonneren vanaf internet**
3. Plak de URL: `https://thewally.github.io/vvz49-jo14-6-agenda/matches.ics`
4. Geef de agenda een naam (bv. "JO14-6") en klik op **Importeren**

**Outlook desktop-app (Windows)**

1. Open het tabblad **Agenda**
2. Klik op **Agenda openen** → **Van internet…**
3. Plak de URL en klik op **OK**

Outlook ververst geabonneerde agenda's doorgaans eens per dag.

## Hoe te gebruiken in Apple Calendar

**Mac**

1. Open de app **Agenda**
2. Kies in het menu **Archief** → **Nieuw agenda-abonnement…**
3. Plak de URL: `https://thewally.github.io/vvz49-jo14-6-agenda/matches.ics`
4. Klik op **Abonneren**, stel eventueel het ververs-interval in (bv. elk uur) en klik op **OK**

**iPhone/iPad**

1. Ga naar **Instellingen** → **Agenda** → **Accounts** → **Account toevoegen** → **Overige**
2. Kies **Voeg agenda-abonnement toe**
3. Vul bij **Server** de URL in en tik op **Volgende**, dan op **Bewaar**

## Overige activiteiten toevoegen

Naast de wedstrijden uit Sportlink kun je zelf activiteiten (trainingen,
toernooien, teamuitjes, borrels) in `overige-activiteiten.json` zetten.
Pas het bestand aan (bv. direct op GitHub via het potlood-icoon); de agenda
wordt dan meteen opnieuw opgebouwd.

```json
[
  {
    "id": "training-woensdag",
    "titel": "Training",
    "datum": "2026-09-22",
    "begintijd": "18:30",
    "eindtijd": "19:15",
    "elke_weken": 2,
    "herhalen_tot": "2026-12-15",
    "behalve": ["2026-10-20"],
    "locatie": "Sportvereniging Vrienden van Zonnegloren",
    "adres": "Eemweg 1, 3764DG SOEST",
    "omschrijving": "Neem je bidon mee."
  }
]
```

| Veld | Verplicht | Uitleg |
|---|---|---|
| `id` | ja | Unieke, vaste naam (letters, cijfers, `-`, `_`). Niet meer wijzigen na publiceren. |
| `titel` | ja | Titel in de agenda. |
| `datum` | ja | `JJJJ-MM-DD`. Bij herhaling: de eerste keer. |
| `begintijd` / `eindtijd` | nee | `UU:MM`. Zonder begintijd wordt het een hele-dag-item; zonder eindtijd duurt het 1 uur. |
| `einddatum` | nee | Voor meerdaagse activiteiten (bv. toernooiweekend). |
| `elke_weken` | nee | Herhaal om de N weken (1 = wekelijks, 2 = om de week). Zonder `herhalen_tot` loopt de reeks door; de feed toont steeds een jaar vooruit. |
| `herhalen_tot` | nee | Laatste datum van de reeks (zonder `elke_weken`: wekelijks). Oude naam `wekelijks_tot` werkt ook nog. |
| `behalve` | nee | Lijst met datums die overgeslagen worden (vakanties). |
| `locatie` / `adres` | nee | Adres wordt een Google Maps-routelink. |
| `url` | nee | Eigen link in plaats van de Maps-link. |
| `omschrijving` | nee | Extra tekst. |
| `afgelast` | nee | `true` → "AFGELAST:" in de titel. |

Een item verwijderen uit het bestand haalt het ook uit de agenda. Bij een
tikfout in het bestand faalt de GitHub Action (je krijgt een mail) en blijft
de huidige agenda staan.
