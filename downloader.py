import os
import requests
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YOUTUBE_SITES = ["youtube.com", "youtu.be"]
TWITTER_SITES = ["twitter.com", "x.com"]
INSTAGRAM_SITES = ["instagram.com", "www.instagram.com"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube, Instagram, or Twitter link to download the video.")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏬ Downloading... Please wait.")

    if any(site in url for site in YOUTUBE_SITES):
        await download_youtube(update, url)
    elif any(site in url for site in INSTAGRAM_SITES + TWITTER_SITES):
        await download_generic(update, url)
    else:
        await update.message.reply_text("❌ Unsupported link. Please send a YouTube, Instagram, or Twitter video link.")


async def download_youtube(update: Update, url: str):
    try:
        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt',
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

        await send_video(update, filepath)

    except Exception as e:
        await update.message.reply_text(f"❌ YouTube download failed:\n{str(e)}")


async def download_generic(update: Update, url: str):
    try:
        ydl_opts = {
            'quiet': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

        await send_video(update, filepath)

    except Exception as e:
        await update.message.reply_text(f"❌ Download failed:\n{str(e)}")


async def send_video(update: Update, filepath: str):
    try:
        await update.message.reply_text("📤 Uploading to Gofile...")

        with open(filepath, 'rb') as f:
            res = requests.post("https://store1.gofile.io/uploadFile", files={"file": f})

        data = res.json()
        if res.ok and data.get("status") == "ok":
            file_id = data["data"]["fileId"]
            delete_token = data["data"]["deleteToken"]
            url = data["data"]["downloadPage"]

            await update.message.reply_text(f"✅ Uploaded:\n{url}\n\n⚠️ This link will auto-delete in 10 minutes.")

            asyncio.create_task(delete_gofile_later(file_id, delete_token, 600))
        else:
            await update.message.reply_text("❌ Failed to upload to Gofile.")
    except Exception as e:
        await update.message.reply_text(f"❌ Upload failed:\n{str(e)}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


async def delete_gofile_later(file_id: str, delete_token: str, delay: int):
    await asyncio.sleep(delay)
    try:
        response = requests.delete(
            "https://api.gofile.io/deleteUpload",
            params={"fileId": file_id, "token": delete_token}
        )
        if response.ok:
            print(f"✅ Deleted from Gofile: {file_id}")
        else:
            print(f"❌ Failed to delete: {file_id}")
    except Exception as e:
        print(f"❌ Error in auto-delete: {str(e)}")


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("🤖 Bot is running...")
    app.run_polling()
