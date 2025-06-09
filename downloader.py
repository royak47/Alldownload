import os
import time
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
            file_path = ydl.prepare_filename(info)
            title = info.get('title', 'Video')
            filesize = os.path.getsize(file_path)

            if filesize > MAX_FILE_SIZE:
                return {"error": "Video too large. Please use a link under 150MB."}

            return {
                "file_path": file_path,
                "title": title,
                "filesize": filesize
            }

    except Exception as e:
        return {"error": str(e)}

def upload_to_gofile(file_path):
    try:
        # Step 1: Get best server
        server_res = requests.get("https://api.gofile.io/getServer")
        server_res.raise_for_status()
        server = server_res.json()["data"]["server"]

        # Step 2: Upload file
        upload_url = f"https://{server}.gofile.io/uploadFile"
        with open(file_path, 'rb') as f:
            response = requests.post(upload_url, files={"file": f})
        response.raise_for_status()

        # Step 3: Get fileId
        upload_data = response.json()["data"]
        file_id = upload_data["fileId"]

        # Step 4: Wait for content to be available
        time.sleep(2)
        content_url = f"https://api.gofile.io/getContent?contentId={file_id}&cache=true"
        details = requests.get(content_url)
        details.raise_for_status()
        contents = details.json()["data"]["contents"]

        for item in contents.values():
            if item["directLink"].endswith(".mp4") or ".mp4" in item["directLink"]:
                return item["directLink"]

        # If no mp4, return first available file link
        first = next(iter(contents.values()))
        return first["directLink"]

    except Exception as e:
        print("Upload to Gofile failed:", e)
        return None

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
    video_url = upload_to_gofile(file_path)

    # Clean up
    try:
        os.remove(file_path)
    except:
        pass

    if not video_url:
        return jsonify({"error": "Upload to gofile.io failed."})

    return jsonify({
        "video_url": video_url,
        "title": result["title"],
        "size": f"{round(result['filesize'] / 1024 / 1024, 2)}MB"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
