import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from packaging import version

app = Flask(__name__)

# ✅ Minimum yt-dlp version
MIN_YTDLP_VERSION = "2024.05.27"

# Check yt-dlp version safely
try:
    from yt_dlp.version import __version__ as ytdlp_version
except ImportError:
    ytdlp_version = "0.0.0"

if version.parse(ytdlp_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(
        f"❌ yt-dlp version too old: {ytdlp_version}. Please upgrade to {MIN_YTDLP_VERSION} or newer using:\n\n  yt-dlp -U"
    )

COOKIES_FILE = "cookies.txt"

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

            # Use direct video URL from best format if available
            if 'formats' in info:
                best_format = max(info['formats'], key=lambda f: f.get("tbr", 0))
                return {
                    "title": info.get("title", "Unknown"),
                    "url": best_format.get("url"),
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader", "Unknown")
                }

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
    print(f"✅ yt-dlp version: {ytdlp_version}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
