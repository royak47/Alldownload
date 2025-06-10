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

# Function to extract direct video URL
def get_direct_video_url(link):
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'best[ext=mp4]/best',  # Try to get best video quality (mp4 preferred)
            'noplaylist': True,  # Skip playlist
        }

        # If cookies file exists, use it for sites like Instagram
        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        # Extract video information using yt-dlp
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)

            formats = info.get("formats", [])
            best_format = None

            # Look for mp4 formats first
            for f in formats:
                if f.get("ext") == "mp4" and f.get("url"):
                    best_format = f
                    break

            # If no mp4 found, fallback to any available format with URL
            if not best_format:
                best_format = next((f for f in formats if f.get("url")), None)

            # Use the URL from the best format found, or fall back to the general URL
            direct_url = best_format["url"] if best_format else info.get("url")

            return {
                "title": info.get("title", "Unknown"),
                "url": direct_url,
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
