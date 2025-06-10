# backend.py

import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL, __version__ as ydl_version
from packaging import version

app = Flask(__name__)

# ✅ Minimum yt-dlp version required
MIN_YTDLP_VERSION = "2024.05.27"

# 🔍 Check yt-dlp version on app startup
if version.parse(ydl_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(
        f"❌ yt-dlp version too old: {ydl_version}. Please upgrade to {MIN_YTDLP_VERSION} or newer using:\n\n  yt-dlp -U"
    )

# ✅ Optional cookies file (if Instagram login is needed)
COOKIES_FILE = "cookies.txt"

def get_direct_video_url(link):
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'best[ext=mp4]/best'
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            return {
                "title": info.get("title", "Unknown"),
                "url": info.get("url"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown")
            }
    except Exception as e:
        return {"error": str(e)}


@app.route('/getlink', methods=['POST'])
def get_link():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing URL"}), 400

    result = get_direct_video_url(url)
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
