import os
import requests
import json
from yt_dlp import YoutubeDL
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables (Render uses .env support)
load_dotenv()

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Optional: Limit file size to 150 MB
MAX_FILE_SIZE = 150 * 1024 * 1024  # 150MB

COOKIES_FILE = "cookies.txt"  # Place cookies.txt in the same directory

def download_video(url):
    try:
        ydl_opts = {
            'quiet': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4'
        }

        # Add cookies if file exists
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

def upload_to_transfer_sh(file_path):
    try:
        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            response = requests.put(f'https://transfer.sh/{filename}', data=f)
        if response.ok:
            return response.text.strip()
        else:
            print("Upload failed:", response.status_code, response.text)
        return None
    except Exception as e:
        print("Exception during upload:", str(e))
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
    uploaded_url = upload_to_transfer_sh(file_path)

    # Clean up
    try:
        os.remove(file_path)
    except:
        pass

    if not uploaded_url:
        return jsonify({"error": "Upload to transfer.sh failed."})

    return jsonify({
        "video_url": uploaded_url,
        "title": result["title"],
        "size": f"{round(result['filesize'] / 1024 / 1024, 2)}MB"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
