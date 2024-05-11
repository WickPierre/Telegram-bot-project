import os
import json
import logging
import sqlite3
import math
import requests
from dotenv import load_dotenv
from googleapiclient.discovery import build
from pytube import YouTube
from telegram.ext import Application, ApplicationBuilder, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup
from moviepy.editor import VideoFileClip, AudioFileClip

con = sqlite3.connect("db.sqlite3")
cur = con.cursor()
COMMANDS = {
    "ru":
        {
            "start": "Привет {0}! Я Youtube Helper.\nДля получения дополнительной информации используйте команду /help",
            "help": open("help_commands_ru.txt", "r").read(),
            "findchannel": {"ask_name": "Введите название канала", "error": "Такого канал не существует"},
            "findvideo": {"ask_name": "Введите название видео", "error": "Такого видео не существует"},
            "downloadvideo": {"ask_link": "Отправьте мне ссылку на видео",
                              "error": "Что-то пошло не так. Попробуйте ещё раз позже."},
            "language": "Успешно!"
        },
    "en":
        {
            "start": "Hello {0}! I'm YouTube Helper.\nFor more information, use the /help command",
            "help": open("help_commands_en.txt", "r").read(),
            "findchannel": {"ask_name": "Enter channel name", "error": "There is no such channel"},
            "findvideo": {"ask_name": "Enter video name", "error": "There is no such video"},
            "downloadvideo": {"ask_link": "Send me the link to the video",
                              "error": "Something went wrong. Try again later."},
            "language": "Successful!"
        }
}

load_dotenv()
API_KEY = os.getenv('API_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

youtube = build('youtube', 'v3', developerKey=API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_user_language(user_name):
    language = cur.execute(f"SELECT language FROM users WHERE user_name = '{user_name}'").fetchall()[0][0]
    return language


def split_video(size, filename):
    video_file = VideoFileClip(filename, audio=True)
    duration = video_file.duration
    k = duration / size
    part_duration = k * 37500000
    dur1 = 0
    dur2 = part_duration
    durations = []
    e = 1
    number_of_videos = math.ceil(duration / part_duration)
    for i in range(number_of_videos):
        clip = video_file.subclip(dur1, dur2)
        clip.write_videofile(f"output{e}.mp4", audio_codec="aac")
        durations.append(dur2 - dur1)
        e += 1
        dur1 += part_duration
        if duration < part_duration * e:
            dur2 = duration
        else:
            dur2 += part_duration
    os.remove(filename)
    return [[open(f"output{i + 1}.mp4", "rb").read(), durations[i]] for i in range(number_of_videos)]


async def start(update, context):
    user_name = update.effective_user.first_name
    user_names = list(map(lambda x: x[0], cur.execute("SELECT user_name FROM users").fetchall()))
    if user_name not in user_names:
        cur.execute(f"""INSERT INTO users(user_name, language) VALUES('{user_name}', 'en')""")
    con.commit()
    await update.message.reply_html(
        COMMANDS[get_user_language(user_name)]["start"].format(update.effective_user.mention_html()))


async def help_command(update, context):
    user_name = update.effective_user.first_name
    await update.message.reply_text(COMMANDS[get_user_language(user_name)]["help"])


async def change_language_command(update, context):
    user_name = update.effective_user.first_name
    language = get_user_language(user_name)
    cur.execute(
        f"""UPDATE users SET language = '{"en" if language == "ru" else "ru"}' WHERE user_name = '{user_name}'""")
    await update.message.reply_text(COMMANDS[get_user_language(user_name)]["language"])


async def search_channel_command(update, context):
    user_name = update.effective_user.first_name
    await update.message.reply_text(COMMANDS[get_user_language(user_name)]["findchannel"]["ask_name"])
    return 1


async def search_channel(update, context):
    user_name = update.effective_user.first_name
    channel_name = update.message.text
    try:
        pl_request = youtube.search().list(
            part="id",
            q=channel_name,
            maxResults=50,
            type="channel"
        )
        pl_response = pl_request.execute()
        channel_id = pl_response["items"][0]["id"]["channelId"]
        request = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            id=channel_id
        )
        response = request.execute()
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
    except Exception:
        await update.message.reply_text(COMMANDS[get_user_language(user_name)]["findchannel"]["error"])
    return ConversationHandler.END


async def search_video_command(update, context):
    user_name = update.effective_user.first_name
    await update.message.reply_text(COMMANDS[get_user_language(user_name)]["findvideo"]["ask_name"])
    return 1


async def search_video(update, context):
    user_name = update.effective_user.first_name
    video_name = update.message.text
    try:
        pl_request = youtube.search().list(
            part="id",
            q=video_name,
            maxResults=5,
            type="video"
        )
        pl_response = pl_request.execute()
        video_id = pl_response["items"][0]["id"]["videoId"]
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()
        title = response["items"][0]["snippet"]["title"]
        description = response["items"][0]["snippet"]["description"]
        duration = response["items"][0]["contentDetails"]["duration"]
        commentCount = response["items"][0]["statistics"].get("commentCount")
        if not commentCount:
            commentCount = 0
        likeCount = response["items"][0]["statistics"]["likeCount"]
        viewCount = response["items"][0]["statistics"]["viewCount"]
        viewCount = ''.join(
            ["." + value if key % 3 == 0 and key != 0 else value for key, value in enumerate(viewCount[::-1])])[::-1]
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
    except Exception:
        await update.message.reply_text(COMMANDS[get_user_language(user_name)]["findvideo"]["error"])
    return ConversationHandler.END


async def download_video_command(update, context):
    user_name = update.effective_user.first_name
    await update.message.reply_text(COMMANDS[get_user_language(user_name)]["downloadvideo"]["ask_link"])
    return 1


async def download_video(update, context):
    user_name = update.effective_user.first_name
    video_url = update.message.text
    my_video = YouTube(video_url)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    video_path = my_video.streams.get_lowest_resolution().download()
    if os.path.getsize(video_path) > 50 * 1024 * 1024:
        video_files = split_video(os.path.getsize(video_path), video_path)
        video_path = "output1.mp4"
    else:
        video_files = [[open(video_path, "rb").read(), VideoFileClip(video_path).duration]]
    size = VideoFileClip(video_path).w, VideoFileClip(video_path).h
    total_file_parts = len(video_files)
    counter = 1
    for part_num, file_part in enumerate(video_files, start=1):
        files = {"video": ("file.mp4", file_part[0])}
        params = {
            "chat_id": update.message.chat_id,
            "duration": file_part[1],
            "width": size[0],
            "height": size[1],
            "supports_streaming": True,
            "part": part_num,
            "total": total_file_parts,
        }
        response = requests.post(url, params=params, files=files)
        os.remove(f"output{counter}.mp4")
        counter += 1
        if not response.json()["ok"]:
            await update.message.reply_text(COMMANDS[get_user_language(user_name)]["downloadvideo"]["error"])
            break
    return ConversationHandler.END


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
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