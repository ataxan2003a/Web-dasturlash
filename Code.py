import os
import zipfile
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

languages = {
    "uz": "O'zbekcha",
    "ru": "Русский",
    "en": "English"
}

user_languages = {}

def download_file(url, folder):
    filename = os.path.join(folder, os.path.basename(urlparse(url).path))
    if os.path.exists(filename):
        return filename
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, "wb") as file:
            file.write(response.content)
        return filename
    return None

def zip_folder(folder, zipf):
    for root, _, files in os.walk(folder):
        for file in files:
            zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder))

def scrape_website(url, chat_id):
    frontend_folder = f"frontend_{chat_id}"
    backend_folder = f"backend_{chat_id}"
    main_zip = f"website_{chat_id}.zip"

    os.makedirs(frontend_folder, exist_ok=True)
    os.makedirs(backend_folder, exist_ok=True)

    response = requests.get(url)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    with open(os.path.join(frontend_folder, "index.html"), "w", encoding="utf-8") as f:
        f.write(soup.prettify())

    downloaded = set()
    backend_ext = ["php", "py", "js"]

    for tag, attr in [("link", "href"), ("script", "src"), ("img", "src")]:
        for element in soup.find_all(tag):
            file_url = element.get(attr)
            if file_url and not file_url.startswith("data:"):
                full_url = urljoin(url, file_url)
                if full_url not in downloaded:
                    download_file(full_url, frontend_folder)
                    downloaded.add(full_url)

    for link in soup.find_all("a"):
        backend_url = link.get("href")
        if backend_url:
            ext = backend_url.split(".")[-1]
            if ext in backend_ext:
                full_url = urljoin(url, backend_url)
                if full_url not in downloaded:
                    download_file(full_url, backend_folder)
                    downloaded.add(full_url)

    with zipfile.ZipFile(main_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zip_folder(frontend_folder, zipf)
        zip_folder(backend_folder, zipf)

    return main_zip

async def start(update: Update, context):
    chat_id = update.message.chat_id
    user_languages[chat_id] = "uz"

    keyboard = [[InlineKeyboardButton(lang, callback_data=code)] for code, lang in languages.items()]
    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Assalamu alaykum! Tilni tanlang:", reply_markup=markup)

async def language_selection(update: Update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_languages[chat_id] = query.data

    await query.edit_message_text(f"Tanlangan til: {languages[query.data]}\nEndi sayt linkini yuboring:")

async def handle_message(update: Update, context):
    chat_id = update.message.chat_id
    text = update.message.text

    if text.startswith("http"):
        await update.message.reply_text("Sayt fayllari yuklanmoqda...")

        website_zip = scrape_website(text, chat_id)

        if website_zip:
            await update.message.reply_text("Frontend va Backend fayllari bitta faylda:")
            await context.bot.send_document(chat_id, document=open(website_zip, 'rb'))

            os.remove(website_zip)
        else:
            await update.message.reply_text("Saytni yuklab bo‘lmadi.")
    else:
        await update.message.reply_text("Iltimos, sayt linkini yuboring!")

def main():
    app = Application.builder().token("8056439074:AAEq-LFXae2G2KJ_7RPHJm829tvNPkp5rbI").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_selection))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
