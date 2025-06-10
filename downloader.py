import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from packaging import version

app = Flask(__name__)

# ✅ Minimum yt-dlp version
MIN_YTDLP_VERSION = "2024.05.27"

# ✅ Safe yt-dlp version check
try:
    import yt_dlp
    ytdlp_version = getattr(yt_dlp, "__version__", "0.0.0")
    if version.parse(ytdlp_version) < version.parse(MIN_YTDLP_VERSION):
        print(f"⚠️ yt-dlp version is outdated: {ytdlp_version}. Recommended: {MIN_YTDLP_VERSION} or higher.")
    else:
        print(f"✅ yt-dlp version: {ytdlp_version}")
except Exception as e:
    print("⚠️ Could not determine yt-dlp version. Proceeding anyway.")

# ✅ Optional cookies file (for Instagram etc.)
COOKIES_FILE = "cookies.txt"

# 🔽 Extract video info using yt-dlp
def get_direct_video_url(link):
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'bestvideo+bestaudio/best',
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)

            formats = [
                f for f in info.get("formats", [])
                if f.get("url") and isinstance(f.get("tbr"), (int, float))
            ]

            if not formats:
                return {"error": "No downloadable video formats found."}

            best_format = max(formats, key=lambda f: f.get("tbr") or 0)

            return {
                "title": info.get("title", "Unknown"),
                "url": best_format["url"],
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown")
            }

    except Exception as e:
        return {"error": str(e)}

# 🔗 POST /getlink endpoint
@app.route('/getlink', methods=['POST'])
def get_link():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing URL"}), 400

    result = get_direct_video_url(url)
    return jsonify(result)

# 🚀 Start Flask server (use gunicorn in prod)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
