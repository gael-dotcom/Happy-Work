import os
import requests
from datetime import datetime, timezone
from pathlib import Path

API_KEY = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

def get_channel_stats():
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "statistics,snippet",
        "id": CHANNEL_ID,
        "key": API_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    if not items:
        raise RuntimeError("Aucun channel trouvé pour cet ID.")
    item = items[0]
    stats = item["statistics"]
    snippet = item["snippet"]
    return {
        "title": snippet.get("title"),
        "viewCount": int(stats.get("viewCount", 0)),
        "subscriberCount": int(stats.get("subscriberCount", 0)),
        "videoCount": int(stats.get("videoCount", 0)),
    }

def write_daily_report(stats: dict):
    # Date du jour (UTC) → on considère que c'est le bilan du jour
    today = datetime.now(timezone.utc).date()
    date_str = today.strftime("%Y-%m-%d")

    # Dossier des rapports
    reports_dir = Path("daily_reports")
    reports_dir.mkdir(exist_ok=True)

    filename = reports_dir / f"youtube-{date_str}.md"

    content = f"""# Bilan YouTube – {date_str}

Chaîne : {stats['title']}

- Vues totales (cumulées) : {stats['viewCount']}
- Abonnés : {stats['subscriberCount']}
- Nombre total de vidéos : {stats['videoCount']}

_(Ce premier rapport est un prototype basé sur les stats globales de la chaîne. On pourra ensuite ajouter les vidéos les plus vues des dernières 24h.)_
"""

    filename.write_text(content, encoding="utf-8")

def main():
    stats = get_channel_stats()
    write_daily_report(stats)

if __name__ == "__main__":
    main()
