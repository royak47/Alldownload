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
        # Step 1: Get Gofile upload server
        server_res = requests.get("https://api.gofile.io/getServer")
        server_data = server_res.json()
        if server_data["status"] != "ok":
            return None

        server = server_data["data"]["server"]

        # Step 2: Upload file
        with open(file_path, "rb") as f:
            upload_res = requests.post(
                f"https://{server}.gofile.io/uploadFile",
                files={"file": f},
                headers={"User-Agent": "Mozilla/5.0"}
            )

        upload_data = upload_res.json()
        if upload_data.get("status") != "ok":
            return None

        return {
            "page": upload_data["data"]["downloadPage"],
            "direct": upload_data["data"]["directLink"]
        }

    except Exception as e:
        print("Gofile upload error:", e)
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
    gofile_result = upload_to_gofile(file_path)

    # Clean up the file
    try:
        os.remove(file_path)
    except:
        pass

    if not gofile_result:
        return jsonify({"error": "Upload to gofile.io failed."})

    return jsonify({
        "video_url": gofile_result["direct"],
        "page_url": gofile_result["page"],
        "title": result["title"],
        "size": f"{round(result['filesize'] / 1024 / 1024, 2)}MB"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
