import os
from flask import Flask, request, jsonify
import yt_dlp  # Import yt_dlp
from packaging import version

app = Flask(__name__)

# ✅ Minimum yt-dlp version required
MIN_YTDLP_VERSION = "2024.05.27"

# 🔍 Check yt-dlp version
try:
    # Check the yt-dlp version by getting it from utils module
    yt_dlp_version = yt_dlp.utils.Version()
except AttributeError:
    raise RuntimeError(
        f"❌ Could not determine yt-dlp version. Please make sure yt-dlp is correctly installed."
    )

# Compare the version
if version.parse(str(yt_dlp_version)) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(
        f"❌ yt-dlp version too old: {yt_dlp_version}. Please upgrade to {MIN_YTDLP_VERSION} or newer using:\n\n  yt-dlp -U"
    )

# ✅ Optional cookies file (for Instagram etc.)
COOKIES_FILE = "cookies.txt"

# 🔽 Extract video info using yt-dlp
def get_direct_video_url(link):
    try:
        # Set yt-dlp options to select best video and audio quality
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'bestvideo+bestaudio/best',  # Selects the best video and best audio streams
        }

        # If cookies file exists, use it
        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            return {
                "title": info.get("title", "Unknown"),
                "url": info.get("url"),
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

# 🚀 Start Flask server
if __name__ == '__main__':
    print(f"✅ yt-dlp version: {yt_dlp_version}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
