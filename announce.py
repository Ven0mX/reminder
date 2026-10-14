import os
import json
import urllib.request
import urllib.error
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
    try:
        r = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print(f"Erreur Discord {e.code} sur {method} {path} : {e.read().decode()}", flush=True)
        raise
    with r:
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

nouveaux = []
for ev in sorted(events, key=lambda e: int(e["id"])):
    url = f"https://discord.com/events/{GUILD}/{ev['id']}"
    if url in deja_annonces:
        print(f"Déjà annoncé, ignoré : {ev['name']}", flush=True)
        continue

    debut = int(datetime.fromisoformat(ev["scheduled_start_time"]).timestamp())
    lieu = (ev.get("entity_metadata") or {}).get("location") or (
        f"<#{ev['channel_id']}>" if ev.get("channel_id") else "—"
    )

    nouveaux.append({
        "title": ev["name"],
        "url": url,
        **({"description": ev["description"]} if ev.get("description") else {}),
        "color": 0x5865F2,
        "fields": [
            {"name": "Début", "value": f"<t:{debut}:F> (<t:{debut}:R>)"},
            {"name": "Lieu", "value": lieu},
        ],
    })

if not nouveaux:
    print("Rien de nouveau à annoncer.", flush=True)
    raise SystemExit(0)

# Un seul ping pour tout le lot (Discord limite à 10 embeds par message :
# au-delà, les messages suivants partent sans ping)
for i in range(0, len(nouveaux), 10):
    if i == 0:
        titre = "Nouvel événement" if len(nouveaux) == 1 else f"{len(nouveaux)} nouveaux événements"
        body = {"content": f"<@&{ROLE}> {titre} :", "allowed_mentions": {"roles": [ROLE]}}
    else:
        body = {"allowed_mentions": {"parse": []}}
    body["embeds"] = nouveaux[i:i + 10]
    api("POST", f"/channels/{CHANNEL}/messages", body)

for e in nouveaux:
    print(f"Annoncé : {e['title']}", flush=True)
import os
import json
import urllib.request
import urllib.error
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
    try:
        r = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print(f"Erreur Discord {e.code} sur {method} {path} : {e.read().decode()}", flush=True)
        raise
    with r:
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
            **({"description": ev["description"]} if ev.get("description") else {}),
            "color": 0x5865F2,
            "fields": [
                {"name": "Début", "value": f"<t:{debut}:F> (<t:{debut}:R>)"},
                {"name": "Lieu", "value": lieu},
            ],
        }],
    })
    print(f"Annoncé : {ev['name']}")
