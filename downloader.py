import os
import requests
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
COOKIES_FILE = "cookies.txt"
MAX_FILE_SIZE = 150 * 1024 * 1024  # 150 MB

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def is_youtube(url):
    return "youtube.com" in url or "youtu.be" in url

def is_instagram(url):
    return "instagram.com" in url

def is_terabox(url):
    return "terabox" in url or "4funbox" in url  # Add more domains if needed

def download_video(url):
    try:
        ydl_opts = {
            "quiet": True,
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "merge_output_format": "mp4"
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            filesize = os.path.getsize(file_path)

            if filesize > MAX_FILE_SIZE:
                return {"error": "Video too large. Please use a link under 150MB."}

            return {
                "file_path": file_path,
                "title": info.get("title", "Video"),
                "filesize": filesize
            }

    except Exception as e:
        return {"error": str(e)}

def upload_to_gofile(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = requests.post("https://store1.gofile.io/uploadFile", files={"file": f})
        if response.ok:
            return response.json()["data"]["downloadPage"]
        return None
    except:
        return None

@app.route("/download", methods=["POST"])
def download_handler():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    link = data.get("link")

    if not link:
        return jsonify({"error": "Missing 'link' in request."}), 400

    if is_terabox(link):
        return jsonify({"error": "TeraBox support must be handled by separate backend."}), 400

    result = download_video(link)
    if "error" in result:
        return jsonify({"error": result["error"]})

    file_path = result["file_path"]
    uploaded_url = upload_to_gofile(file_path)

    try:
        os.remove(file_path)
    except:
        pass

    if not uploaded_url:
        return jsonify({"error": "Upload to gofile.io failed."})

    return jsonify({
        "video_url": uploaded_url,
        "title": result["title"],
        "size": f"{round(result['filesize'] / 1024 / 1024, 2)}MB"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
