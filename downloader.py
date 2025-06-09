import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from yt_dlp import YoutubeDL
from moviepy.editor import VideoFileClip

# Load .env variables
load_dotenv()

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 150 * 1024 * 1024  # 150 MB
COOKIES_FILE = "cookies.txt"  # optional

# ✅ Check video duration
def is_valid_video(file_path):
    try:
        clip = VideoFileClip(file_path)
        duration = clip.duration
        clip.close()
        return duration > 2  # At least 2 seconds
    except Exception as e:
        print("Duration check error:", e)
        return False

# ✅ Download from YouTube or any supported site
def download_video(url):
    try:
        ydl_opts = {
            'quiet': True,
            'format': 'best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }]
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if not os.path.exists(filename):
            return {"error": "Downloaded file not found."}

        filesize = os.path.getsize(filename)
        if filesize > MAX_FILE_SIZE:
            os.remove(filename)
            return {"error": "File size exceeds 150MB limit."}

        if not is_valid_video(filename):
            os.remove(filename)
            return {"error": "Invalid or too short video."}

        return {
            "file_path": filename,
            "title": info.get("title", "Unknown Title"),
            "filesize": filesize
        }

    except Exception as e:
        return {"error": str(e)}

# ✅ Upload to GoFile.io (latest API)
def upload_to_gofile(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                "https://api.gofile.io/uploadFile",
                files={"file": f}
            )
        if response.ok:
            data = response.json()
            return data.get("data", {}).get("downloadPage")
        return None
    except Exception as e:
        print("GoFile upload error:", e)
        return None

# ✅ Flask route to handle POST requests
@app.route("/download", methods=["POST"])
def download_handler():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    link = data.get("link")
    if not link:
        return jsonify({"error": "Missing 'link' in request."}), 400

    result = download_video(link)
    if "error" in result:
        return jsonify({"error": result["error"]})

    file_path = result["file_path"]
    uploaded_url = upload_to_gofile(file_path)

    try:
        os.remove(file_path)
    except Exception as e:
        print("Cleanup error:", e)

    if not uploaded_url:
        return jsonify({"error": "Upload to gofile.io failed."})

    return jsonify({
        "video_url": uploaded_url,
        "title": result["title"],
        "size": f"{round(result['filesize'] / 1024 / 1024, 2)}MB"
    })

# ✅ App entry point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
