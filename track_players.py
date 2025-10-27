import json
import os
import datetime
from mcstatus import JavaServer
import requests
import time

# ---- CONFIGURATION ----
SERVER_ADDRESS = os.environ["MC_SERVER_ADDRESS"]
GIST_ID = os.environ["GIST_ID"]
GIST_FILE = os.environ["GIST_FILE"]
TOKEN = os.environ["GITHUB_TOKEN"]
RETRIES = 3
# ------------------------

def ping_server():
    server = JavaServer.lookup(SERVER_ADDRESS)
    for attempt in range(RETRIES):
        try:
            status = server.status()
            players = []
            if hasattr(status.players, "sample") and status.players.sample:
                for p in status.players.sample:
                    players.append({"name": p.name, "id": p.id})
            return {"online": status.players.online, "max": status.players.max, "players": players}
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            print(f"Ping attempt {attempt+1} failed: {e}")
            time.sleep(2)
        except Exception:
            raise
    return None

def load_gist():
    headers = {"Authorization": f"token {TOKEN}"}
    url = f"https://api.github.com/gists/{GIST_ID}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    gist = r.json()
    if GIST_FILE in gist["files"] and gist["files"][GIST_FILE]["content"] is not None:
        content = gist["files"][GIST_FILE]["content"]
        return json.loads(content)
    else:
        # File does not exist → start new log
        print(f"Gist file '{GIST_FILE}' does not exist. Starting new log.")
        return []

def update_gist(data):
    headers = {"Authorization": f"token {TOKEN}"}
    url = f"https://api.github.com/gists/{GIST_ID}"
    payload = {"files": {GIST_FILE: {"content": json.dumps(data, indent=2)}}}
    r = requests.patch(url, headers=headers, json=payload)
    r.raise_for_status()

def main():
    now = datetime.datetime.utcnow().isoformat()
    ping_result = ping_server()
    if ping_result is None:
        print("Server ping failed, skipping update")
        return

    # Load existing log from Gist
    try:
        data = load_gist()
    except Exception as e:
        print("Failed to load existing Gist, starting new log")
        data = []

    entry = {
        "time": now,
        "online": ping_result["online"],
        "max": ping_result["max"],
        "players": ping_result["players"]
    }

    data.append(entry)
    update_gist(data)

if __name__ == "__main__":
    main()

