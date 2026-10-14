import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

API = "https://discord.com/api/v10"
TOKEN = os.environ["DISCORD_TOKEN"]
GUILD = os.environ["GUILD_ID"]
CHANNEL = os.environ["ANNOUNCE_CHANNEL_ID"]
ROLE = os.environ["TEAM_ROLE_ID"]
PARIS = ZoneInfo("Europe/Paris")

# GitHub planifie en UTC : on lance à 10h et 11h UTC, et on ne poste
# que si c'est midi à Paris (gère automatiquement heure d'été / d'hiver).
# Un lancement manuel poste toujours.
maintenant = datetime.now(PARIS)
if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch" and maintenant.hour != 12:
    print(f"Il est {maintenant:%H:%M} à Paris, pas de rappel.")
    sys.exit(0)

def api(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body else None,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (event-reminder, 1.0)",
        },
    )
    try:
        r = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print(f"Erreur Discord {e.code} sur {method} {path} : {e.read().decode()}", flush=True)
        raise
    with r:
        data = r.read()
    return json.loads(data) if data else None

aujourdhui = maintenant.date()

# Événements programmés (status 1) qui ont lieu AUJOURD'HUI (heure de Paris)
# et n'ont pas encore commencé. Un event demain ou plus tard : rien ne part.
# Pour un event récurrent, Discord renvoie la date de la prochaine occurrence.
events = api("GET", f"/guilds/{GUILD}/scheduled-events")
du_jour = []
for ev in events:
    debut = datetime.fromisoformat(ev["scheduled_start_time"]).astimezone(PARIS)
    if ev.get("status") == 1 and debut.date() == aujourdhui and debut > maintenant:
        du_jour.append((debut, ev))
du_jour.sort(key=lambda x: x[0])

if not du_jour:
    print("Aucun événement aujourd'hui, pas de rappel.")
    sys.exit(0)

# Anti-doublon : un rappel par event et par jour (clé = id de l'event + date),
# notée dans le pied de chaque carte déjà envoyée.
messages = api("GET", f"/channels/{CHANNEL}/messages?limit=100")
deja = " ".join(
    (e.get("footer") or {}).get("text", "")
    for m in messages
    for e in m.get("embeds", [])
)

embeds = []
for debut, ev in du_jour:
    cle = f"Rappel du {aujourdhui.isoformat()} · id {ev['id']}"
    if cle in deja:
        print(f"Rappel déjà envoyé aujourd'hui : {ev['name']}")
        continue
    ts = int(debut.timestamp())
    lieu = (ev.get("entity_metadata") or {}).get("location") or (
        f"<#{ev['channel_id']}>" if ev.get("channel_id") else "—"
    )
    embeds.append({
        "title": ev["name"],
        "url": f"https://discord.com/events/{GUILD}/{ev['id']}",
        **({"description": ev["description"]} if ev.get("description") else {}),
        "color": 0x5865F2,
        "fields": [
            {"name": "Début", "value": f"<t:{ts}:t> (<t:{ts}:R>)"},
            {"name": "Lieu", "value": lieu},
        ],
        "footer": {"text": cle},
    })

if not embeds:
    sys.exit(0)

# Un seul message et un seul ping pour tous les events du jour
titre = "un événement aujourd'hui" if len(embeds) == 1 else f"{len(embeds)} événements aujourd'hui"
api("POST", f"/channels/{CHANNEL}/messages", {
    "content": f"<@&{ROLE}> Rappel : {titre}",
    "allowed_mentions": {"roles": [ROLE]},
    "embeds": embeds[:10],
})
for e in embeds[:10]:
    print(f"Rappel envoyé : {e['title']}")
import os
import sys
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://discord.com/api/v10"
TOKEN = os.environ["DISCORD_TOKEN"]
GUILD = os.environ["GUILD_ID"]
CHANNEL = os.environ["ANNOUNCE_CHANNEL_ID"]
ROLE = os.environ["TEAM_ROLE_ID"]

# GitHub planifie en UTC : on lance à 10h et 11h UTC, et on ne poste
# que si c'est midi à Paris (gère automatiquement heure d'été / d'hiver).
# Un lancement manuel poste toujours.
maintenant_paris = datetime.now(ZoneInfo("Europe/Paris"))
if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch" and maintenant_paris.hour != 12:
    print(f"Il est {maintenant_paris:%H:%M} à Paris, pas de rappel.")
    sys.exit(0)


def api(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body else None,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (event-reminder, 1.0)",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = r.read()
        return json.loads(data) if data else None


maintenant = datetime.now(timezone.utc)

events = api("GET", f"/guilds/{GUILD}/scheduled-events")
# Seulement les événements programmés (status 1) qui n'ont pas encore commencé
a_venir = sorted(
    (
        (datetime.fromisoformat(ev["scheduled_start_time"]), ev)
        for ev in events
        if ev.get("status") == 1
    ),
    key=lambda x: x[0],
)
a_venir = [(d, ev) for d, ev in a_venir if d > maintenant]

if not a_venir:
    print("Aucun événement à venir, pas de rappel.")
    sys.exit(0)

debut, ev = a_venir[0]  # le prochain
ts = int(debut.timestamp())
url = f"https://discord.com/events/{GUILD}/{ev['id']}"
lieu = (ev.get("entity_metadata") or {}).get("location") or (
    f"<#{ev['channel_id']}>" if ev.get("channel_id") else "—"
)

api("POST", f"/channels/{CHANNEL}/messages", {
    "content": f"<@&{ROLE}> Rappel : prochain événement **{ev['name']}**",
    "allowed_mentions": {"roles": [ROLE]},
    "embeds": [{
        "title": ev["name"],
        "url": url,
        "description": ev.get("description") or "",
        "color": 0x5865F2,
        "fields": [
            {"name": "Début", "value": f"<t:{ts}:F> (<t:{ts}:R>)"},
            {"name": "Lieu", "value": lieu},
        ],
    }],
})
print(f"Rappel envoyé : {ev['name']}")
