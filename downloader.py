import os
import requests
import json
from yt_dlp import YoutubeDL
from flask import Flask, request, jsonify

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


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
            title = info.get('title', 'Video')
            return {
                "file_path": file_path,
                "title": title,
                "filesize": os.path.getsize(file_path)
            }

    except Exception as e:
        return {"error": str(e)}


def upload_to_transfer_sh(file_path):
    try:
        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            response = requests.put(f'https://transfer.sh/{filename}', data=f)
        if response.ok:
            return response.text.strip()
        return None
    except Exception as e:
        return None


@app.route("/download", methods=["POST"])
def download_handler():
    data = request.json
    link = data.get("link")
    if not link:
        return jsonify({"error": "Missing 'link' in request."}), 400

    result = download_video(link)
    if "error" in result:
        return jsonify({"error": result["error"]})

    file_path = result["file_path"]
    uploaded_url = upload_to_transfer_sh(file_path)

    if not uploaded_url:
        return jsonify({"error": "Upload to transfer.sh failed."})

    os.remove(file_path)

    return jsonify({
        "video_url": uploaded_url,
        "title": result["title"],
        "size": f"{round(result['filesize'] / 1024 / 1024, 2)}MB"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
