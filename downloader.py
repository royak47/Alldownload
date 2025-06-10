import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from yt_dlp.version import __version__ as ydl_version
from packaging import version

app = Flask(__name__)

# Minimum yt-dlp version required
MIN_YTDLP_VERSION = "2024.05.27"
if version.parse(ydl_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(
        f"❌ yt-dlp version too old: {ydl_version}. Please upgrade to {MIN_YTDLP_VERSION} or newer using:\n\n  yt-dlp -U"
    )

# Optional cookies file (for Instagram etc.)
COOKIES_FILE = "cookies.txt"

# Extract video info using yt-dlp
def get_direct_video_url(link):
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'best[ext=mp4]/best',  # Ensure mp4 when available
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)

            # Instagram handling: if video and audio available, provide both
            if 'formats' in info and 'url' not in info:
                formats = [f for f in info['formats'] if f.get('ext') == 'mp4' and f.get('url')]
                if formats:
                    best = max(formats, key=lambda f: f.get('tbr') or 0)
                    return {
                        "title": info.get("title", "Unknown"),
                        "url": best.get("url"),
                        "duration": info.get("duration"),
                        "uploader": info.get("uploader", "Unknown")
                    }

            # Pinterest handling: Check if supported m3u8 format is available
            if "pinterest" in link:
                if 'formats' in info:
                    # Pick best mp4 format with direct URL
                    formats = [f for f in info['formats'] if f.get('ext') == 'mp4' and f.get('url')]
                    if formats:
                        best = max(formats, key=lambda f: f.get('tbr') or 0)
                        return {
                            "title": info.get("title", "Unknown"),
                            "url": best.get("url"),
                            "duration": info.get("duration"),
                            "uploader": info.get("uploader", "Unknown")
                        }

            # General case: return direct URL if found
            return {
                "title": info.get("title", "Unknown"),
                "url": info.get("url"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown")
            }
    except Exception as e:
        return {"error": str(e)}

# POST /getlink endpoint
@app.route('/getlink', methods=['POST'])
def get_link():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    result = get_direct_video_url(url)
    return jsonify(result)

# Start Flask server
if __name__ == '__main__':
    print(f"✅ yt-dlp version: {ydl_version}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
