import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from yt_dlp.version import __version__ as ydl_version
from packaging import version

app = Flask(__name__)
MIN_YTDLP_VERSION = "2024.05.27"

if version.parse(ydl_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(f"yt-dlp >= {MIN_YTDLP_VERSION} required, found {ydl_version}")

COOKIES_FILE = "cookies/cookies.txt"  # Adjust this path if needed

def get_platform(url: str) -> str:
    if "instagram.com" in url:
        return "instagram"
    elif "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "pinterest.com" in url:
        return "pinterest"
    elif "x.com" in url or "twitter.com" in url:
        return "x"
    return "generic"

def get_direct_video_url(link):
    platform = get_platform(link)

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    }

    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)

            formats = info.get('formats', [])
            best_format = None
            for f in formats:
                if (
                    f.get('ext') == 'mp4'
                    and f.get('acodec') != 'none'
                    and f.get('vcodec') != 'none'
                    and f.get('url')
                ):
                    if best_format is None or (f.get("tbr") or 0) > (best_format.get("tbr") or 0):
                        best_format = f

            final_url = best_format["url"] if best_format else info.get("url")

            return {
                "title": info.get("title", "Unknown"),
                "url": final_url,
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown"),
                "platform": platform
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
