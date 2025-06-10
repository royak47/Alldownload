import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from yt_dlp.version import __version__ as ydl_version
from packaging import version

app = Flask(__name__)
MIN_YTDLP_VERSION = "2024.05.27"
COOKIES_FILE = "cookies.txt"

if version.parse(ydl_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(f"yt-dlp too old: {ydl_version}, upgrade with: yt-dlp -U")

def get_format_by_url(url):
    url = url.lower()
    if 'pinterest' in url:
        return 'V_HLSV3_MOBILE-1296'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'bv*+ba/best[ext=mp4]/best'
    elif 'instagram.com' in url:
        return 'best[ext=mp4]/best'
    elif 'x.com' in url or 'twitter.com' in url:
        return 'best[ext=mp4]/best'
    else:
        return 'best'

def get_direct_video_url(link):
    try:
        format_selector = get_format_by_url(link)
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'noplaylist': True,
            'format': format_selector
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            formats = info.get("formats", [])
            best = next((f for f in formats if f.get("url") and f.get("ext") == "mp4"), None)
            url = best["url"] if best else info.get("url")

            return {
                "title": info.get("title", "Unknown"),
                "url": url,
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
    result = get_direct_video_url(url)
    return jsonify(result)

if __name__ == '__main__':
    print(f"✅ yt-dlp version: {ydl_version}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
