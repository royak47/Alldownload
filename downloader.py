import os
import requests
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
COOKIES_FILE = "cookies.txt"
MAX_FILE_SIZE = 150 * 1024 * 1024  # 150MB

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def is_supported(link):
    return any(site in link for site in [
        "youtube.com", "youtu.be", "instagram.com", "twitter.com", "x.com"
    ])


def download_video(link):
    ydl_opts = {
        "quiet": True,
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "merge_output_format": "mp4"
    }

    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            filepath = ydl.prepare_filename(info)
            filesize = os.path.getsize(filepath)

            if filesize > MAX_FILE_SIZE:
                os.remove(filepath)
                return {"error": "❌ File too large. Limit is 150MB."}

            return {
                "file_path": filepath,
                "title": info.get("title", "Video"),
                "filesize": filesize
            }

    except Exception as e:
        return {"error": f"Download error: {str(e)}"}


def upload_to_gofile(file_path):
    try:
        with open(file_path, 'rb') as f:
            res = requests.post("https://store1.gofile.io/uploadFile", files={"file": f})
        if res.ok:
            return res.json()["data"]["downloadPage"]
    except Exception:
        pass
    return None


@app.route("/download", methods=["POST"])
def handle_download():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    link = data.get("link")

    if not link or not is_supported(link):
        return jsonify({"error": "❌ Invalid or unsupported link."}), 400

    result = download_video(link)

    if "error" in result:
        return jsonify({"error": result["error"]})

    file_path = result["file_path"]
    download_url = upload_to_gofile(file_path)

    try:
        os.remove(file_path)
    except Exception:
        pass

    if not download_url:
        return jsonify({"error": "❌ Upload to gofile.io failed."})

    return jsonify({
        "video_url": download_url,
        "title": result["title"],
        "size": f"{round(result['filesize'] / 1024 / 1024, 2)} MB"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
