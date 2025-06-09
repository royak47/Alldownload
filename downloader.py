import os
import requests
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 150 * 1024 * 1024  # 150MB
COOKIES_FILE = "cookies.txt"  # Use same for YouTube & Instagram

# Platform indicators
YOUTUBE_SITES = ["youtube.com", "youtu.be"]
INSTAGRAM_SITES = ["instagram.com", "www.instagram.com"]
TWITTER_SITES = ["twitter.com", "x.com"]

def detect_platform(url: str):
    if any(site in url for site in YOUTUBE_SITES):
        return "youtube"
    if any(site in url for site in INSTAGRAM_SITES):
        return "instagram"
    if any(site in url for site in TWITTER_SITES):
        return "twitter"
    return None

def download_video(url, platform):
    try:
        ydl_opts = {
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "merge_output_format": "mp4",
            "quiet": True
        }

        if platform in ["youtube", "instagram"] and os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if not os.path.exists(filename):
            return None, "❌ Error: File not found after download"

        if os.path.getsize(filename) > MAX_FILE_SIZE:
            return None, "❌ Error: File exceeds 150MB limit"

        return filename, None

    except Exception as e:
        return None, f"❌ Error during download: {str(e)}"

def upload_to_gofile(filepath):
    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                "https://store1.gofile.io/uploadFile",
                files={"file": f}
            )

        res_json = response.json()

        if not res_json.get("status") == "ok":
            return None, f"❌ GoFile API error: {res_json}"

        return res_json["data"]["downloadPageUrl"], None

    except Exception as e:
        return None, f"❌ Exception during GoFile upload: {str(e)}"

@app.route("/download", methods=["POST"])
def handle_download():
    try:
        data = request.get_json(force=True)
        url = data.get("link")

        if not url:
            return jsonify({"error": "❌ Error: No 'link' provided in request"}), 400

        platform = detect_platform(url)
        if not platform:
            return jsonify({"error": "❌ Error: Unsupported platform"}), 400

        filepath, error = download_video(url, platform)
        if error:
            return jsonify({"error": error}), 500

        gofile_url, gofile_error = upload_to_gofile(filepath)
if gofile_error:
    return jsonify({"error": gofile_error}), 500
        result = {
            "video_url": gofile_url,
            "title": os.path.basename(filepath),
            "size": os.path.getsize(filepath)
        }

        os.remove(filepath)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"❌ Error in backend: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
