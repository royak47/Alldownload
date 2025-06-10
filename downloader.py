import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from yt_dlp.version import __version__ as ydl_version
from packaging import version

app = Flask(__name__)

# Minimum yt-dlp version required
MIN_YTDLP_VERSION = "2024.05.27"
if version.parse(ydl_version) < version.parse(MIN_YTDLP_VERSION):
    raise RuntimeError(f"❌ yt-dlp version too old: {ydl_version}. Please upgrade to {MIN_YTDLP_VERSION} or newer.")

# Optional cookies file (for Instagram etc.)
COOKIES_FILE = "cookies.txt"

# Extract video info using yt-dlp
def get_direct_video_url(link):
    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
            "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            "format": "bv*[ext=mp4]+ba[ext=m4a]/best[ext=mp4]/best",
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            formats = info.get("formats", [])

            # Instagram Handling (ensure audio and video are both included)
            if "instagram" in link:
                formats = [f for f in formats if f.get("ext") == "mp4" and f.get("url")]
                if formats:
                    best = max(formats, key=lambda f: f.get("tbr") or 0)
                    return {
                        "title": info.get("title", "Unknown"),
                        "url": best.get("url"),
                        "duration": info.get("duration"),
                        "uploader": info.get("uploader", "Unknown"),
                    }
                else:
                    # Fallback: If only audio found, return it
                    audio = next((f for f in formats if f.get("ext") == "m4a" and f.get("url")), None)
                    return {
                        "title": info.get("title", "Unknown"),
                        "url": audio["url"] if audio else info.get("url"),
                        "duration": info.get("duration"),
                        "uploader": info.get("uploader", "Unknown"),
                    }

            # Pinterest Handling: Handle unavailable format gracefully
            elif "pinterest" in link:
                if "formats" in info and not info.get("url"):
                    formats = [f for f in info['formats'] if f.get('ext') == 'mp4' and f.get('url')]
                    if formats:
                        best = max(formats, key=lambda f: f.get('tbr') or 0)
                        return {
                            "title": info.get("title", "Unknown"),
                            "url": best.get("url"),
                            "duration": info.get("duration"),
                            "uploader": info.get("uploader", "Unknown"),
                        }
                    else:
                        return {"error": "❌ No video format available for this Pinterest URL."}

            # YouTube: Ensure correct audio and video extraction
            elif "youtube" in link:
                best = None
                for f in sorted(formats, key=lambda x: x.get("tbr") or 0, reverse=True):
                    if f.get("ext") == "mp4" and f.get("url"):
                        best = f
                        break
                final_url = best.get("url") if best else info.get("url")

                return {
                    "title": info.get("title", "Unknown"),
                    "url": final_url,
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader", "Unknown"),
                }

            # Default handling: Provide best available format
            best = None
            for f in sorted(formats, key=lambda x: x.get("tbr") or 0, reverse=True):
                if f.get("ext") in ["mp4", "m4a"] and f.get("url"):
                    best = f
                    break

            final_url = best.get("url") if best else info.get("url")

            return {
                "title": info.get("title", "Unknown"),
                "url": final_url,
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown")
            }

    except Exception as e:
        return {"error": f"❌ Error: {str(e)}"}

@app.route('/getlink', methods=['POST'])
def get_link():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    return jsonify(get_direct_video_url(url))

# Gunicorn-compatible: backend:app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
