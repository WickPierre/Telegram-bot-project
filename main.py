import os
import json
import logging
from dotenv import load_dotenv
from googleapiclient.discovery import build
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from googletrans import Translator, constants

translator = Translator()
language = "ru"
translations = {
    "start": "Hello {0}! I'm YouTube Helper.\nFor more information, use the /help command",
    "help": "I can help you find and download videos from YouTube.\n\nYou can control me by sending these commands:"
}

load_dotenv()
API_KEY = os.getenv('API_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

youtube = build('youtube', 'v3', developerKey=API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def start(update, context):
    user = update.effective_user
    response = translator.translate(translations["start"], dest=language).text.format(user.mention_html())
    await update.message.reply_html(response)


async def help_command(update, context):
    response = translator.translate(translations["help"], dest=language).text
    await update.message.reply_text(response)


async def search_channel_command(update, context):
    pl_request = youtube.search().list(
        part="snippet",
        q=update.message.text.split()[1],
        maxResults=10
    )
    pl_response = pl_request.execute()
    channel_id = None
    for item in pl_response["items"]:
        if item["id"]["kind"] == "youtube#channel":
            channel_id = item["id"]["channelId"]
            break
    if channel_id:
        request = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            id=channel_id
        )
        response = request.execute()
        await update.message.reply_text(json.dumps(response, sort_keys=True, indent=4, ensure_ascii=False))
    else:
        await update.message.reply_text("Такого канал не существует")


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("findchannel", search_channel_command))
    # text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, echo)
    # application.add_handler(text_handler)
    application.run_polling()


if __name__ == '__main__':
    main()