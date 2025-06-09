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

def download_video(url):
    try:
        ydl_opts = {
            'quiet': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4'
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            title = info.get("title", "Video")
            size = os.path.getsize(file_path)

            if size > MAX_FILE_SIZE:
                return {"error": "Video too large. Please use a link under 150MB."}

            return {
                "file_path": file_path,
                "title": title,
                "filesize": size
            }
    except Exception as e:
        return {"error": str(e)}

def upload_to_gofile(file_path):
    try:
        # Get Gofile server
        res = requests.get("https://api.gofile.io/getServer")
        server = res.json()["data"]["server"]

        # Upload file
        with open(file_path, "rb") as f:
            upload = requests.post(
                f"https://{server}.gofile.io/uploadFile",
                files={"file": f}
            )

        if not upload.ok:
            return None

        response = upload.json()
        file_data = response["data"]["downloadPage"]
        direct_link = response["data"]["directLink"]

        return {
            "page": file_data,
            "direct": direct_link
        }

    except Exception as e:
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

    try:
        os.remove(file_path)
    except:
        pass

    if not gofile_result:
        return jsonify({"error": "Upload to gofile.io failed."})

    return jsonify({
        "video_url": gofile_result["direct"],  # Direct .mp4 link
        "title": result["title"],
        "size": f"{round(result['filesize'] / 1024 / 1024, 2)}MB"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
