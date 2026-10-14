import os
import json
import urllib.request
from datetime import datetime

API = "https://discord.com/api/v10"
TOKEN = os.environ["DISCORD_TOKEN"]
GUILD = os.environ["GUILD_ID"]
CHANNEL = os.environ["ANNOUNCE_CHANNEL_ID"]
ROLE = os.environ["TEAM_ROLE_ID"]

# Lancé à 10h et 11h UTC (heure d'été/hiver) : on ne continue que s'il est midi à Paris
from zoneinfo import ZoneInfo
if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and datetime.now(ZoneInfo("Europe/Paris")).hour != 12: raise SystemExit(0)


def api(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body else None,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (event-announcer, 1.0)",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = r.read()
        return json.loads(data) if data else None


# Événements à venir / en cours du serveur
events = api("GET", f"/guilds/{GUILD}/scheduled-events")
guild = api("GET", f"/guilds/{GUILD}")
print(f"Serveur : {guild['name']} — {len(events)} événement(s) trouvé(s)", flush=True)
for ev in events:
    print(f"  - {ev['name']} (statut {ev['status']}, début {ev['scheduled_start_time']})", flush=True)

# Messages récents du salon d'annonces, pour ne pas annoncer deux fois le même événement
messages = api("GET", f"/channels/{CHANNEL}/messages?limit=100")
deja_annonces = " ".join(
    m["content"] + " " + " ".join(e.get("url") or "" for e in m.get("embeds", []))
    for m in messages
)

for ev in sorted(events, key=lambda e: int(e["id"])):
    url = f"https://discord.com/events/{GUILD}/{ev['id']}"
    if url in deja_annonces:
        print(f"Déjà annoncé, ignoré : {ev['name']}", flush=True)
        continue

    debut = int(datetime.fromisoformat(ev["scheduled_start_time"]).timestamp())
    lieu = (ev.get("entity_metadata") or {}).get("location") or (
        f"<#{ev['channel_id']}>" if ev.get("channel_id") else "—"
    )

    api("POST", f"/channels/{CHANNEL}/messages", {
        "content": f"<@&{ROLE}> Nouvel événement : **{ev['name']}**",
        "allowed_mentions": {"roles": [ROLE]},
        "embeds": [{
            "title": ev["name"],
            "url": url,
            "description": ev.get("description") or "",
            "color": 0x5865F2,
            "fields": [
                {"name": "Début", "value": f"<t:{debut}:F> (<t:{debut}:R>)"},
                {"name": "Lieu", "value": lieu},
            ],
        }],
    })
    print(f"Annoncé : {ev['name']}")
