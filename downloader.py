import os
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

def get_direct_video_url(link):
    platform = get_platform(link)

    if platform == "youtube":
        base_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'bv*+ba/best[ext=mp4]/best',
            'noplaylist': True
        }

    elif platform == "instagram":
        base_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        }

    elif platform == "pinterest":
        import requests

        if "pin.it" in link:
            try:
                r = requests.get(link, allow_redirects=True, timeout=5)
                if r.status_code == 200:
                    link = r.url.split("?")[0]
                else:
                    return {"error": "❌ Failed to expand Pinterest short link."}
            except Exception as e:
                return {"error": f"❌ Pinterest redirect failed: {str(e)}"}

        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'best',
            'merge_output_format': 'mp4',
            'force_generic_extractor': True,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)

                formats = info.get("formats") or []
                preferred_format = None

                for f in formats:
                    tbr = f.get("tbr")
                    if (
                        f.get("url")
                        and f.get("ext") in ["mp4", "m4a"]
                        and f.get("vcodec") != "none"
                        and isinstance(tbr, (int, float))
                    ):
                        if not preferred_format or tbr > preferred_format.get("tbr", 0):
                            preferred_format = f

                return {
                    "title": info.get("title", "Unknown"),
                    "url": preferred_format.get("url") if preferred_format else None,
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader", "Unknown"),
                    "platform": platform
                }

        except Exception as e:
            return {"error": f"❌ Pinterest download failed: {str(e)}"}

    # Collect cookie files
    cookie_files = []
    cookies_folder = COOKIES_DIR
    if os.path.exists(cookies_folder):
        cookie_files = [
            os.path.join(cookies_folder, f)
            for f in os.listdir(cookies_folder)
            if f.endswith(".txt")
        ]

    for cookie_file in cookie_files + [None]:
        ydl_opts = base_opts.copy()
        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)

                formats = info.get('formats', [])
                best_format = None
                for f in formats:
                    if f.get('ext') == 'mp4' and f.get('acodec') != 'none' and f.get('vcodec') != 'none' and f.get('url'):
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
            print(f"[{cookie_file}] failed: {e}")
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
