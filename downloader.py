import os
import requests
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 150 * 1024 * 1024  # 150 MB
COOKIES_FILE = "cookies.txt"

YOUTUBE_SITES = ["youtube.com", "youtu.be"]
INSTAGRAM_SITES = ["instagram.com", "www.instagram.com"]
TWITTER_SITES = ["twitter.com", "x.com"]

def detect_platform(url):
    url = url.lower()
    if any(site in url for site in YOUTUBE_SITES):
        return "youtube"
    elif any(site in url for site in INSTAGRAM_SITES):
        return "instagram"
    elif any(site in url for site in TWITTER_SITES):
        return "twitter"
    else:
        return "unknown"

def download_video(url, platform):
    try:
        ydl_opts = {
            'quiet': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
        }

        if platform in ["youtube", "instagram"] and os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename, info.get("title", "Untitled")

    except Exception as e:
        return None, f"❌ Download failed: {str(e)}"

def upload_to_gofile(filepath):
    try:
        with open(filepath, 'rb') as f:
            response = requests.post("https://store1.gofile.io/uploadFile", files={"file": f})

        if response.status_code != 200:
            return None, "❌ Failed to reach GoFile"

        json_resp = response.json()

        # Debug: Check exact structure
        data = json_resp.get("data", {})
        download_page = data.get("downloadPage") or data.get("downloadPageUrl")

        if not download_page:
            return None, "❌ Missing downloadPageUrl in GoFile response"

        return download_page, None

    except Exception as e:
        return None, f"❌ Exception during GoFile upload: {str(e)}"

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get("link")

    if not url:
        return jsonify({ "error": "❌ No link provided" }), 400

    platform = detect_platform(url)
    if platform == "unknown":
        return jsonify({ "error": "❌ Unsupported platform" }), 400

    filepath, title_or_error = download_video(url, platform)
    if not filepath:
        return jsonify({ "error": title_or_error }), 500

    # Check file size before upload
    if os.path.getsize(filepath) > MAX_FILE_SIZE:
        os.remove(filepath)
        return jsonify({ "error": "❌ File too large (limit 150MB)" }), 400

    gofile_url, gofile_error = upload_to_gofile(filepath)
    os.remove(filepath)  # Auto delete after upload

    if gofile_error:
        return jsonify({ "error": gofile_error }), 500

    return jsonify({
        "video_url": gofile_url,
        "title": title_or_error,
        "size": os.path.getsize(filepath)
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
