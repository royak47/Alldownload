import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from yt_dlp.version import __version__ as ydl_version
from packaging import version

app = Flask(__name__)

# ✅ Minimum yt-dlp version required
MIN_YTDLP_VERSION = "2024.05.27"

# 🔍 Check yt-dlp version
if version.parse(ydl_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(
        f"❌ yt-dlp version too old: {ydl_version}. Please upgrade to {MIN_YTDLP_VERSION} or newer using:\n\n  yt-dlp -U"
    )

# ✅ Optional cookies file (for Instagram etc.)
COOKIES_FILE = "cookies.txt"

def get_direct_video_url(link):
    try:
        # Set yt-dlp options to select best video and audio quality
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'best[ext=mp4]/best',  # Fallback to best mp4 if available
            'noplaylist': True,
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)

            # Handle different platforms' format availability
            if 'formats' in info:
                formats = info.get("formats", [])
                best_format = next((f for f in formats if f.get("ext") == "mp4" and f.get("url")), None)

                # If no best mp4 found, check for other available formats
                if not best_format:
                    best_format = next((f for f in formats if f.get("url")), None)

                # If formats are not available, use the default URL
                direct_url = best_format["url"] if best_format else info.get("url")
            else:
                direct_url = info.get("url")

            # Return relevant video info
            return {
                "title": info.get("title", "Unknown"),
                "url": direct_url,
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
    print(f"✅ yt-dlp version: {ydl_version}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
