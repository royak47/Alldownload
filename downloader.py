import os
import requests
from yt_dlp import YoutubeDL
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 150 * 1024 * 1024  # 150MB
COOKIES_FILE = "cookies.txt"

YOUTUBE_SITES = ["youtube.com", "youtu.be"]
INSTAGRAM_SITES = ["instagram.com", "www.instagram.com"]
TWITTER_SITES = ["twitter.com", "x.com"]


def identify_platform(url):
    if any(site in url for site in YOUTUBE_SITES):
        return "youtube"
    elif any(site in url for site in INSTAGRAM_SITES):
        return "instagram"
    elif any(site in url for site in TWITTER_SITES):
        return "twitter"
    return "unsupported"


def download_video(url, platform):
    try:
        ydl_opts = {
            'quiet': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4'
        }

        if platform in ["youtube", "instagram"] and os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if not os.path.exists(filename):
            return None, "❌ File was not downloaded."

        if os.path.getsize(filename) > MAX_FILE_SIZE:
            return None, "❌ File too large (>150MB)."

        return filename, None
    except Exception as e:
        return None, f"❌ Download failed: {str(e)}"


def upload_to_gofile(filepath):
    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                "https://store1.gofile.io/uploadFile",
                files={"file": f}
            )

        res_json = response.json()

        if res_json.get("status") != "ok":
            return None, f"❌ GoFile error: {res_json.get('message', 'Unknown error')}"

        data = res_json.get("data", {})
        download_url = data.get("downloadPageUrl")

        if not download_url:
            return None, "❌ Missing downloadPageUrl in GoFile response"

        return download_url, None
    except Exception as e:
        return None, f"❌ Exception during GoFile upload: {str(e)}"


@app.route("/download", methods=["POST"])
def process_request():
    data = request.get_json()
    url = data.get("link")

    if not url:
        return jsonify({"error": "No link provided"}), 400

    platform = identify_platform(url)
    if platform == "unsupported":
        return jsonify({"error": "❌ Unsupported platform"}), 400

    filepath, error = download_video(url, platform)
    if error:
        return jsonify({"error": error}), 500

    gofile_url, gofile_error = upload_to_gofile(filepath)
    os.remove(filepath)

    if gofile_error:
        return jsonify({"error": gofile_error}), 500

    return jsonify({
        "download_url": gofile_url
    })


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
