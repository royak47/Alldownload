import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
import yt_dlp  # Import yt_dlp directly for version
from packaging import version

app = Flask(__name__)

# ✅ Minimum yt-dlp version required
MIN_YTDLP_VERSION = "2024.05.27"

# 🔍 Check yt-dlp version
if version.parse(yt_dlp.__version__) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(
        f"❌ yt-dlp version too old: {yt_dlp.__version__}. Please upgrade to {MIN_YTDLP_VERSION} or newer using:\n\n  yt-dlp -U"
    )

# ✅ Optional cookies file (for Instagram etc.)
COOKIES_FILE = "cookies.txt"

# 🔽 Extract video info using yt-dlp
def get_direct_video_url(link):
    try:
        # Set yt-dlp options to select best available stream (works for HLS, YouTube, Instagram, etc.)
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'best',  # ✅ This will pick the best available video/audio, including HLS streams (Pinterest, Instagram)
            # 'listformats': True,  # Use this for debugging (removable in production)
        }

        # If cookies file exists, use it (for Instagram, etc.)
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
    print(f"✅ yt-dlp version: {yt_dlp.__version__}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
