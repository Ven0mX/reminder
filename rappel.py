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
