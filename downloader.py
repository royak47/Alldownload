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
TWITTER_SITES = ["x.com", "twitter.com"]

def get_platform(url):
    if any(site in url for site in YOUTUBE_SITES):
        return "youtube"
    elif any(site in url for site in INSTAGRAM_SITES):
        return "instagram"
    elif any(site in url for site in TWITTER_SITES):
        return "twitter"
    return "unknown"

def download_video(url):
    try:
        platform = get_platform(url)

        ydl_opts = {
            "quiet": True,
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
            "merge_output_format": "mp4",
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"
        }

        if platform in ["youtube", "instagram"] and os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if not os.path.exists(filename):
            return None, None, "❌ Download failed: File not found."

        file_size = os.path.getsize(filename)
        if file_size > MAX_FILE_SIZE:
            os.remove(filename)
            return None, None, f"❌ File too large ({round(file_size/1024/1024)}MB). Max allowed: 150MB"

        return filename, info.get("title", "Untitled"), None

    except Exception as e:
        return None, None, f"❌ Download error: {str(e)}"

def upload_to_gofile(filepath):
    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                "https://store1.gofile.io/uploadFile",
                files={"file": f}
            )
        res_json = response.json()

        if res_json.get("status") != "ok":
            return None, f"❌ GoFile error: {res_json}"

        return res_json["data"]["downloadPageUrl"], None
    except Exception as e:
        return None, f"❌ Exception during GoFile upload: {str(e)}"

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    if not data or "link" not in data:
        return jsonify({"error": "❌ No link provided"}), 400

    url = data["link"].strip()
    platform = get_platform(url)
    if platform == "unknown":
        return jsonify({"error": "❌ Unsupported platform"}), 400

    filepath, title, download_error = download_video(url)
    if download_error:
        return jsonify({"error": download_error}), 500

    gofile_url, gofile_error = upload_to_gofile(filepath)
    if gofile_error:
        return jsonify({"error": gofile_error}), 500

    os.remove(filepath)

    return jsonify({
        "video_url": gofile_url,
        "title": title,
        "size": os.path.getsize(filepath)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
