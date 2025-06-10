import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from yt_dlp.version import __version__ as ydl_version
from packaging import version

app = Flask(__name__)

MIN_YTDLP_VERSION = "2024.05.27"
if version.parse(ydl_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(f"❌ yt-dlp version too old: {ydl_version}. Please upgrade to {MIN_YTDLP_VERSION} or newer")

COOKIES_FILE = "cookies.txt"

def get_direct_video_url(link):
    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
            "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            "format": "bv*[ext=mp4]+ba[ext=m4a]/best[ext=mp4]/best",
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            formats = info.get("formats", [])
            
            # Try to get best combined video+audio with direct CDN-like URL
            best = None
            for f in sorted(formats, key=lambda x: x.get("tbr") or 0, reverse=True):
                if f.get("ext") in ["mp4", "m4a"] and f.get("url") and not f.get("acodec") == "none":
                    best = f
                    break

            # Fallback if main url is available
            final_url = best.get("url") if best else info.get("url")

            return {
                "title": info.get("title", "Unknown"),
                "url": final_url,
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown")
            }

    except Exception as e:
        return {"error": f"❌ Error: {str(e)}"}

@app.route('/getlink', methods=['POST'])
def get_link():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    return jsonify(get_direct_video_url(url))

# Gunicorn-compatible: backend:app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
