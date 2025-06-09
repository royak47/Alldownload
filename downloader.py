import os
import requests
from yt_dlp import YoutubeDL
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 150 * 1024 * 1024  # 150MB
COOKIES_FILE = "cookies.txt"  # Optional

def upload_to_gofile(filepath):
    with open(filepath, 'rb') as f:
        files = {'file': f}
        response = requests.post("https://store1.gofile.io/uploadFile", files=files)
        data = response.json()
        if data.get("status") == "ok":
            return data["data"]["downloadPage"]
        return None

def download_video(url):
    try:
        ydl_opts = {
            'quiet': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4'
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # Check file size
        if os.path.getsize(filename) > MAX_FILE_SIZE:
            os.remove(filename)
            return None, "❌ Video too large (limit is 150MB)."

        return filename, None
    except Exception as e:
        return None, f"❌ Download error: {str(e)}"

@app.route("/download", methods=["POST"])
def handle_download():
    data = request.get_json()
    url = data.get("link")

    if not url:
        return jsonify({"error": "No link provided"}), 400

    filepath, error = download_video(url)
    if error:
        return jsonify({"error": error}), 400

    gofile_url = upload_to_gofile(filepath)
    os.remove(filepath)  # Auto-delete temp file after upload

    if gofile_url:
        return jsonify({
            "video_url": gofile_url,
            "title": os.path.basename(filepath),
            "size": os.path.getsize(filepath)
        })
    else:
        return jsonify({"error": "❌ Upload to GoFile failed."}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
