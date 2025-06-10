import os
import re
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from yt_dlp.version import __version__ as ydl_version
from packaging import version

app = Flask(__name__)

MIN_YTDLP_VERSION = "2024.05.27"
if version.parse(ydl_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(f"yt-dlp version too old: {ydl_version}. Upgrade with: yt-dlp -U")

COOKIES_FILE = "cookies.txt"

def detect_platform(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "instagram.com" in url:
        return "instagram"
    elif "twitter.com" in url or "x.com" in url:
        return "x"
    elif "pinterest.com" in url:
        return "pinterest"
    else:
        return "unknown"

def get_format_for_platform(platform: str) -> str:
    if platform == "youtube":
        return 'bv*+ba/best[ext=mp4]/best'
    elif platform == "instagram":
        return 'bv*+ba/best[ext=mp4]/best'
    elif platform == "x":
        return 'bv*+ba/best[ext=mp4]/best'
    elif platform == "pinterest":
        return 'V_HLSV3_MOBILE-1296'
    else:
        return 'best[ext=mp4]/best'

def get_direct_video_url(link: str):
    platform = detect_platform(link)
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
        'format': get_format_for_platform(platform),
    }

    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)

            formats = info.get("formats", [])
            selected_url = None

            # Pinterest fallback logic
            if platform == "pinterest":
                fallback = next((f for f in formats if f.get("format_id") == "V_HLSV3_MOBILE-1296"), None)
                if not fallback:
                    fallback = max((f for f in formats if f.get("ext") == "mp4"), key=lambda x: x.get("tbr", 0), default=None)
                if fallback and fallback.get("url"):
                    selected_url = fallback["url"]
            else:
                selected_url = info.get("url")
                # Check if best format with both audio+video available
                if formats:
                    combo = [f for f in formats if f.get("ext") == "mp4" and f.get("url")]
                    best = max(combo, key=lambda f: f.get("tbr", 0), default=None)
                    if best:
                        selected_url = best["url"]

            return {
                "platform": platform,
                "title": info.get("title", "Unknown"),
                "url": selected_url,
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown"),
                "thumbnail": info.get("thumbnail")
            }
    except Exception as e:
        return {"error": f"❌ Error: {str(e)}"}

@app.route('/getlink', methods=['POST'])
def get_link():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    result = get_direct_video_url(url)
    return jsonify(result)

if __name__ == '__main__':
    print(f"✅ yt-dlp version: {ydl_version}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
