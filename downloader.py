import os
import requests
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from yt_dlp.version import __version__ as ydl_version
from packaging import version

app = Flask(__name__)
MIN_YTDLP_VERSION = "2024.05.27"

if version.parse(ydl_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(f"yt-dlp >= {MIN_YTDLP_VERSION} required, found {ydl_version}")

COOKIES_DIR = "cookies"  # Folder containing multiple .txt cookie files

def get_platform(url: str) -> str:
    if "instagram.com" in url:
        return "instagram"
    elif "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "pinterest.com" in url or "pin.it" in url:
        return "pinterest"
    elif "x.com" in url or "twitter.com" in url:
        return "x"
    return "generic"

def expand_pinterest_short_link(link):
    if "pin.it" in link:
        try:
            r = requests.get(link, allow_redirects=True, timeout=5)
            if r.status_code == 200:
                return r.url.split("?")[0]
        except Exception as e:
            print(f"[Pinterest Redirect Error] {e}")
    return link

def get_direct_video_url(link):
    platform = get_platform(link)

    if platform == "pinterest":
        link = expand_pinterest_short_link(link)
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'V_HLSV3_MOBILE-1296/V_HLSV3_MOBILE-1026/V_HLSV3_MOBILE-735/best',
            'force_generic_extractor': False,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                formats = info.get("formats", [])
                best = next(
                    (
                        f for f in formats
                        if f.get("url") and f.get("ext") == "mp4" and f.get("vcodec") != "none"
                    ),
                    None,
                )

                if not best and info.get("url"):
                    best = {"url": info["url"]}

                if not best:
                    return {"error": "❌ No valid Pinterest video format found."}

                return {
                    "title": info.get("title", "Unknown"),
                    "url": best["url"],
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader", "Unknown"),
                    "platform": platform
                }

        except Exception as e:
            return {"error": f"❌ Pinterest download failed: {str(e)}"}

    # For Instagram and YouTube: use cookie rotation
    base_opts = {
        'quiet': True,
        'skip_download': True,
        'format': 'bestvideo[ext=mp4][vcodec!=none]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'noplaylist': True
    }

    cookie_files = []
    if os.path.exists(COOKIES_DIR):
        cookie_files = [
            os.path.join(COOKIES_DIR, f)
            for f in os.listdir(COOKIES_DIR)
            if f.endswith(".txt")
        ]

    for cookie_file in cookie_files + [None]:
        ydl_opts = base_opts.copy()
        if cookie_file:
            ydl_opts["cookiefile"] = cookie_file

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                formats = info.get("formats", [])
                best_format = None

                for f in formats:
                    if (
                        f.get("ext") == "mp4"
                        and f.get("acodec") != "none"
                        and f.get("vcodec") != "none"
                        and f.get("url")
                    ):
                        if best_format is None or (f.get("tbr") or 0) > (best_format.get("tbr") or 0):
                            best_format = f

                final_url = best_format["url"] if best_format else info.get("url")

                if not final_url:
                    continue

                return {
                    "title": info.get("title", "Unknown"),
                    "url": final_url,
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader", "Unknown"),
                    "platform": platform
                }

        except Exception as e:
            print(f"❌ Failed with cookie: {cookie_file}, error: {e}")
            continue

    return {"error": "❌ Error: Failed using all cookie files."}

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
