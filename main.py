import os
import json
import logging
import sqlite3
from dotenv import load_dotenv
from googleapiclient.discovery import build
from pytube import YouTube
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup

con = sqlite3.connect("db.sqlite3")
cur = con.cursor()

language = "en"
COMMANDS = {
    "ru":
        {
            "start": "Привет {0}! Я Youtube Helper.\nДля получения дополнительной информации используйте команду /help",
            "help": open("help_commands_ru.txt", "r").read(),
            "findchannel": ["Введите название канала", "Такого канал не существует"],
            "findvideo": ["Введите название видео", "Такого видео не существует"],
            "downloadvideo": ["Отправьте мне ссылку на видео", "Извините, я не могу скачать это видео, оно слишком длинное"],
            "language": "Успешно!"
        },
    "en":
        {
            "start": "Hello {0}! I'm YouTube Helper.\nFor more information, use the /help command",
            "help": open("help_commands_en.txt", "r").read(),
            "findchannel": ["Enter channel name", "There is no such channel"],
            "findvideo": ["Enter video name", "There is no such video"],
            "downloadvideo": ["Send me the link to the video", "Sorry, I can't download this video, it's too long"],
            "language": "Successful!"
        }
}

load_dotenv()
API_KEY = os.getenv('API_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

youtube = build('youtube', 'v3', developerKey=API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def start(update, context):
    cur.execute(f"""INSERT INTO users(user_name) VALUES('{update.effective_user.first_name}')""")
    con.commit()
    await update.message.reply_html(COMMANDS[language]["start"].format(update.effective_user.mention_html()))


async def help_command(update, context):
    await update.message.reply_text(COMMANDS[language]["help"])


async def change_language_command(update, context):
    global language
    language = "en" if language == "ru" else "ru"
    await update.message.reply_text(COMMANDS[language]["language"])


async def search_channel_command(update, context):
    await update.message.reply_text(COMMANDS[language]["findchannel"][0])
    return 1


async def search_channel(update, context):
    channel_name = update.message.text
    pl_request = youtube.search().list(
        part="id",
        q=channel_name,
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
        # print(json.dumps(response, sort_keys=True, indent=4))
        title = response["items"][0]["snippet"]["title"]
        subscriberCount = response["items"][0]["statistics"]["subscriberCount"]
        videoCount = response["items"][0]["statistics"]["videoCount"]
        viewCount = response["items"][0]["statistics"]["viewCount"]
        registration_date = response["items"][0]["snippet"]["publishedAt"]
        await update.message.reply_text(
            f"Название канала: {title}\n"
            f"{subscriberCount} подписчиков\n"
            f"{videoCount} видео\n"
            f"{viewCount} просмотров\n"
            f"Дата регистрации: {registration_date}"
        )
    else:
        await update.message.reply_text(COMMANDS[language]["findchannel"][1])
    return ConversationHandler.END


async def search_video_command(update, context):
    await update.message.reply_text(COMMANDS[language]["findvideo"][0])
    return 1


async def search_video(update, context):
    video_name = update.message.text
    pl_request = youtube.search().list(
        part="id",
        q=video_name,
        maxResults=5
    )
    pl_response = pl_request.execute()
    video_id = None
    for item in pl_response["items"]:
        if item["id"]["kind"] == "youtube#video":
            video_id = item["id"]["videoId"]
            break
    if video_id:
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()
        title = response["items"][0]["snippet"]["title"]
        description = response["items"][0]["snippet"]["description"]
        duration = response["items"][0]["contentDetails"]["duration"]
        commentCount = response["items"][0]["statistics"]["commentCount"]
        likeCount = response["items"][0]["statistics"]["likeCount"]
        viewCount = response["items"][0]["statistics"]["viewCount"]
        viewCount = ''.join(["." + value if key % 3 == 0 and key != 0 else value for key, value in enumerate(viewCount[::-1])])[::-1]
        publication_date = response["items"][0]["snippet"]["publishedAt"]
        await update.message.reply_text(
            f"Название видео: {title}\n\n"
            f"Описание: \n\n{description}\n\n"
            f"Продолжительность видео: {duration}\n\n"
            f"{viewCount} просмотров\n\n"
            f"Дата публикации: {publication_date}\n"
            f"Количество лайков: {likeCount}\n"
            f"Количество комментариев: {commentCount}\n"
        )
    else:
        await update.message.reply_text(COMMANDS[language]["findvideo"][1])
    return ConversationHandler.END


async def download_video_command(update, context):
    await update.message.reply_text(COMMANDS[language]["downloadvideo"][0])
    return 1


async def download_video(update, context):
    video_url = update.message.text
    try:
        my_video = YouTube(video_url)
        s = my_video.streams.first().download()
        video = open(s, 'rb')
        await context.bot.send_video(chat_id=update.message.chat_id, video=video, supports_streaming=True, read_timeout=1000, connect_timeout=1000)
    except TimeoutError:
        await update.message.reply_text(COMMANDS[language]["downloadvideo"][1])
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("changelanguage", change_language_command))

    search_channel_handler = ConversationHandler(
        entry_points=[CommandHandler("findchannel", search_channel_command)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_channel)]
        },
        fallbacks=[]
    )

    search_video_handler = ConversationHandler(
        entry_points=[CommandHandler("findvideo", search_video_command)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_video)]
        },
        fallbacks=[]
    )

    download_video_handler = ConversationHandler(
        entry_points=[CommandHandler("downloadvideo", download_video_command)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_video)]
        },
        fallbacks=[]
    )

    application.add_handler(search_channel_handler)
    application.add_handler(search_video_handler)
    application.add_handler(download_video_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
    cur.close()