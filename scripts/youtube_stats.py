import os
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

API_KEY = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def get_channel_stats() -> Dict:
    url = f"{YOUTUBE_API_BASE}/channels"
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


def get_recent_video_ids(max_results: int = 20) -> List[str]:
    """
    Récupère les dernières vidéos de la chaîne.
    On utilise search.list pour lister les vidéos récentes.
    """
    url = f"{YOUTUBE_API_BASE}/search"
    params = {
        "part": "id",
        "channelId": CHANNEL_ID,
        "maxResults": max_results,
        "order": "date",
        "type": "video",
        "key": API_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    video_ids = []
    for item in items:
        vid = item.get("id", {}).get("videoId")
        if vid:
            video_ids.append(vid)
    return video_ids


def parse_iso8601_duration(duration: str) -> int:
    """
    Convertit une durée ISO8601 (PTxMxS) en secondes.
    Exemple : PT45S → 45, PT3M10S → 190
    On reste simple pour ton usage.
    """
    if not duration.startswith("PT"):
        return 0
    duration = duration[2:]  # remove "PT"
    minutes = 0
    seconds = 0
    current = ""
    for char in duration:
        if char.isdigit():
            current += char
        else:
            if char == "M":
                minutes = int(current or "0")
            elif char == "S":
                seconds = int(current or "0")
            current = ""
    return minutes * 60 + seconds


def get_videos_details(video_ids: List[str]) -> List[Dict]:
    if not video_ids:
        return []
    url = f"{YOUTUBE_API_BASE}/videos"
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(video_ids),
        "key": API_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    videos = []
    for item in items:
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        content_details = item.get("contentDetails", {})
        duration_iso = content_details.get("duration", "PT0S")
        duration_seconds = parse_iso8601_duration(duration_iso)
        is_short = duration_seconds <= 60

        videos.append(
            {
                "id": item["id"],
                "title": snippet.get("title", ""),
                "publishedAt": snippet.get("publishedAt", ""),
                "viewCount": int(stats.get("viewCount", 0)),
                "likeCount": int(stats.get("likeCount", 0)),
                "commentCount": int(stats.get("commentCount", 0)),
                "durationSeconds": duration_seconds,
                "isShort": is_short,
            }
        )
    # Tri par vues décroissantes
    videos.sort(key=lambda v: v["viewCount"], reverse=True)
    return videos


def format_video_line(video: Dict) -> str:
    kind = "Short" if video["isShort"] else "Long"
    minutes = video["durationSeconds"] // 60
    seconds = video["durationSeconds"] % 60
    if minutes > 0:
        duration_str = f"{minutes}m{seconds:02d}s"
    else:
        duration_str = f"{seconds}s"
    return (
        f"- [{kind}] {video['title']} — {video['viewCount']} vues, "
        f"{video['likeCount']} likes, {video['commentCount']} commentaires, "
        f"durée {duration_str}"
    )


def write_daily_report(channel_stats: Dict, videos: List[Dict]) -> None:
    today = datetime.now(timezone.utc).date()
    date_str = today.strftime("%Y-%m-%d")

    reports_dir = Path("daily_reports")
    reports_dir.mkdir(exist_ok=True)

    filename = reports_dir / f"youtube-{date_str}.md"

    shorts = [v for v in videos if v["isShort"]]
    longs = [v for v in videos if not v["isShort"]]

    top_shorts = shorts[:3]
    top_longs = longs[:3]

    lines = []
    lines.append(f"# Bilan YouTube – {date_str}\n")
    lines.append(f"Chaîne : {channel_stats['title']}\n")
    lines.append("## Stats globales")
    lines.append(f"- Vues totales (cumulées) : {channel_stats['viewCount']}")
    lines.append(f"- Abonnés : {channel_stats['subscriberCount']}")
    lines.append(f"- Nombre total de vidéos : {channel_stats['videoCount']}\n")

    if top_shorts:
        lines.append("## Top 3 Shorts (par vues)")
        for v in top_shorts:
            lines.append(format_video_line(v))
        lines.append("")
    else:
        lines.append("## Top 3 Shorts (par vues)")
        lines.append("_Aucun Short trouvé dans les dernières vidéos._\n")

    if top_longs:
        lines.append("## Top 3 vidéos longues (par vues)")
        for v in top_longs:
            lines.append(format_video_line(v))
        lines.append("")
    else:
        lines.append("## Top 3 vidéos longues (par vues)")
        lines.append("_Aucune vidéo longue trouvée dans les dernières vidéos._\n")

    lines.append("## Dernières vidéos analysées")
    if videos:
        for v in videos:
            lines.append(format_video_line(v))
    else:
        lines.append("_Aucune vidéo trouvée._")

    content = "\n".join(lines) + "\n"

    filename.write_text(content, encoding="utf-8")


def main():
    channel_stats = get_channel_stats()
    video_ids = get_recent_video_ids(max_results=20)
    videos = get_videos_details(video_ids)
    write_daily_report(channel_stats, videos)


if __name__ == "__main__":
    main()

