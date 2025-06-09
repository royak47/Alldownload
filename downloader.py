import os
import threading
import requests
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))
DOWNLOAD_DIR = "downloads"
COOKIES_FILE = "cookies.txt"

app = Flask(__name__)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Downloader Logic ---
def is_supported_link(url):
    return any(x in url for x in ["youtube.com", "youtu.be", "instagram.com", "twitter.com", "x.com"])

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
            size = os.path.getsize(file_path)
            return file_path, info.get("title", "Video"), size
    except Exception as e:
        return None, str(e), 0

def upload_to_gofile(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = requests.post("https://store1.gofile.io/uploadFile", files={"file": f})
        return response.json()["data"]["downloadPage"] if response.ok else None
    except:
        return None

# --- Flask API ---
@app.route("/download", methods=["POST"])
def download_handler():
    data = request.get_json()
    link = data.get("link")
    if not link or not is_supported_link(link):
        return jsonify({"error": "Unsupported or missing link."}), 400

    file_path, title_or_error, size = download_video(link)
    if not file_path:
        return jsonify({"error": title_or_error}), 400

    gofile_link = upload_to_gofile(file_path)
    os.remove(file_path)

    if not gofile_link:
        return jsonify({"error": "Failed to upload to GoFile."}), 500

    return jsonify({
        "video_url": gofile_link,
        "title": title_or_error,
        "size": f"{round(size / 1024 / 1024, 2)}MB"
    })

# --- Telegram Bot Logic ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube, Instagram, or Twitter link to download.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not is_supported_link(url):
        await update.message.reply_text("❌ Unsupported link.")
        return

    await update.message.reply_text("⏳ Downloading... Please wait.")
    file_path, title_or_error, size = download_video(url)
    if not file_path:
        await update.message.reply_text(f"❌ Failed: {title_or_error}")
        return

    gofile_link = upload_to_gofile(file_path)
    os.remove(file_path)

    if gofile_link:
        await update.message.reply_text(f"✅ [Download]({gofile_link})\n📝 {title_or_error}\n📦 {round(size/1024/1024, 2)} MB", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Upload failed. Try again later.")

# --- Start Flask and Bot in Parallel ---
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

def run_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app_bot.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
