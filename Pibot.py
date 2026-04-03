import os
import yt_dlp
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

import os
TOKEN = os.environ.get("TOKEN")

MAX_SIZE_MB = 50  # الحد الأقصى لحجم الملف

# ==================== رسالة الترحيب ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً! أنا بوت تنزيل Pinterest\n\n"
        "📌 أرسل لي رابط أي بوست من Pinterest\n"
        "🎬 وسأرسل لك الفيديو أو الصورة مباشرة!\n\n"
        "✅ يدعم روابط pinterest.com و pin.it"
    )

# ==================== دالة التحقق من الحجم ====================
def check_size(filename):
    size_mb = os.path.getsize(filename) / (1024 * 1024)
    return size_mb <= MAX_SIZE_MB, size_mb

# ==================== دالة تنزيل الصورة ====================
async def handle_image(url, update, msg):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        # جلب رابط الصورة
        thumb = info.get("thumbnail") or info.get("url")
        if not thumb:
            await msg.edit_text("❌ ما قدرت أجيب الصورة")
            return
        
        response = requests.get(thumb, headers=headers, timeout=15)
        filename = "/tmp/image.jpg"
        with open(filename, "wb") as f:
            f.write(response.content)
        
        ok, size = check_size(filename)
        if not ok:
            os.remove(filename)
            await msg.edit_text(f"❌ الصورة كبيرة جداً ({size:.1f}MB) - الحد الأقصى {MAX_SIZE_MB}MB")
            return
        
        await msg.edit_text("📤 جاري إرسال الصورة...")
        with open(filename, "rb") as img:
            await update.message.reply_photo(photo=img)
        
        os.remove(filename)
        await msg.delete()
    
    except Exception as e:
        await msg.edit_text(f"❌ فشل تنزيل الصورة: {str(e)}")

# ==================== الدالة الرئيسية ====================
async def download_pinterest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if "pinterest.com" not in url and "pin.it" not in url:
        await update.message.reply_text("❌ أرسل رابط Pinterest فقط")
        return
    
    msg = await update.message.reply_text("⏳ جاري التحليل...")
    
    try:
        # فحص نوع المحتوى أولاً
        ydl_opts_check = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts_check) as ydl:
            info = ydl.extract_info(url, download=False)
        
        is_video = info.get("ext") in ["mp4", "mov", "webm"] or info.get("vcodec") not in [None, "none"]
        
        if not is_video:
            await msg.edit_text("🖼️ تم اكتشاف صورة، جاري التنزيل...")
            await handle_image(url, update, msg)
            return
        
        # تنزيل الفيديو
        await msg.edit_text("⏳ جاري تنزيل الفيديو...")
        
        ydl_opts = {
            "outtmpl": "/tmp/%(id)s.%(ext)s",
            "quiet": True,
            "format": "best[ext=mp4]/best",
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        # التحقق من الحجم
        ok, size = check_size(filename)
        if not ok:
            os.remove(filename)
            await msg.edit_text(
                f"❌ الفيديو كبير جداً ({size:.1f}MB)\n"
                f"الحد الأقصى المسموح: {MAX_SIZE_MB}MB"
            )
            return
        
        await msg.edit_text(f"📤 جاري الإرسال... ({size:.1f}MB)")
        
        with open(filename, "rb") as video:
            await update.message.reply_video(video=video)
        
        os.remove(filename)
        await msg.delete()
    
    except Exception as e:
        await msg.edit_text(f"❌ فشل التنزيل:\n{str(e)}")

# ==================== تشغيل البوت ====================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_pinterest))

print("✅ البوت شغال...")
app.run_polling()
