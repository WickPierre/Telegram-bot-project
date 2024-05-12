import os
import logging
import sqlite3
import math
import re
from dotenv import load_dotenv
from googleapiclient.discovery import build
from pytube import YouTube
from telegram.ext import Application, ApplicationBuilder, MessageHandler, filters, CommandHandler, ConversationHandler
from moviepy.editor import VideoFileClip

con = sqlite3.connect("db.sqlite3")
cur = con.cursor()
COMMANDS = {
    "ru":
        {
            "start": "Привет {0}! Я Youtube Helper.\nДля получения дополнительной информации используйте команду /help",
            "help": open("help_commands_ru.txt", "r").read(),
            "findchannel": {
                "ask_name": "Введите название канала",
                "response": "Название канала: {}\n`{}` подписчиков\n`{}` видео\n`{}` просмотров\nДата регистрации: `{}`",
                "error": "Такого канал не существует"
            },
            "findvideo": {
                "ask_name": "Введите название видео",
                "response": "Название видео: {}\n\nСсылка: {}\n\nОписание: \n\n{}\n\nПродолжительность видео: "
                            "<code>{}</code>\n\n<code>{}</code> просмотров\n\nДата публикации: <code>{}</code>\n\n"
                            "<code>{}</code> лайков\n\n<code>{}</code> комментариев",
                "error": "Такого видео не существует"
            },
            "downloadvideo": {
                "ask_link": "Отправьте мне ссылку на видео",
                "error": "Что-то пошло не так. Попробуйте ещё раз позже."
            },
            "language": "Успешно!"
        },
    "en":
        {
            "start": "Hello {0}! I'm YouTube Helper.\nFor more information, use the /help command",
            "help": open("help_commands_en.txt", "r").read(),
            "findchannel": {
                "ask_name": "Enter channel name",
                "response": "Channel name: {}\n`{}` subscribers\n`{}` videos\n`{}` views\nRegistration date: `{}`",
                "error": "There is no such channel"
            },
            "findvideo": {
                "ask_name": "Enter video name",
                "response": "Video title: {}\n\nLink: {}\n\nDescription: \n\n{}\n\nVideo duration: <code>{}</code>\n\n"
                            "<code>{}</code> views\n\nPublication date: <code>{}</code>\n\n<code>{}</code> likes\n\n"
                            "<code>{}</code> comments",
                "error": "There is no such video"
            },
            "downloadvideo": {
                "ask_link": "Send me the link to the video",
                "error": "Something went wrong. Try again later."
            },
            "language": "Successful!"
        }
}

load_dotenv()
API_KEY = os.getenv('API_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

youtube = build('youtube', 'v3', developerKey=API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def convert_duration(duration):
    days_patter = re.compile(r'(\d+)D')
    hours_pattern = re.compile(r'(\d+)H')
    minutes_pattern = re.compile(r'(\d+)M')
    seconds_pattern = re.compile(r'(\d+)S')

    days = days_patter.search(duration)
    hours = hours_pattern.search(duration)
    minutes = minutes_pattern.search(duration)
    seconds = seconds_pattern.search(duration)

    hours = int(hours.group(1)) if hours else 0
    minutes = int(minutes.group(1)) if minutes else 0
    seconds = int(seconds.group(1)) if seconds else 0
    if days:
        days = int(days.group(1))
        hours += days * 24

    return f"{hours:02}:{minutes:02}:{seconds:02}"


def get_user_language(user_name):
    language = cur.execute(f"SELECT language FROM users WHERE user_name = '{user_name}'").fetchall()[0][0]
    return language


def split_video(size, filename):
    video_file = VideoFileClip(filename, audio=True)
    duration = video_file.duration
    k = duration / size
    part_duration = k * 40000000
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
    telegram_user_name = update.effective_user.username
    user_names = list(map(lambda x: x[0], cur.execute("SELECT user_name FROM users").fetchall()))
    if user_name not in user_names:
        cur.execute(f"""INSERT INTO users(user_name, telegram_user_name, language) 
                        VALUES('{user_name}', '{telegram_user_name}', 'en')""")
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
    con.commit()
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
        subscriberCount = ''.join(
            [" " + value if key % 3 == 0 and key != 0 else value for key, value in enumerate(subscriberCount[::-1])])[
                          ::-1]
        videoCount = response["items"][0]["statistics"]["videoCount"]
        viewCount = response["items"][0]["statistics"]["viewCount"]
        viewCount = ''.join(
            [" " + value if key % 3 == 0 and key != 0 else value for key, value in enumerate(viewCount[::-1])])[::-1]
        registration_date = "".join(response["items"][0]["snippet"]["publishedAt"].split("T")[::-1]).split("Z")
        registration_date = " ".join([registration_date[0], "-".join(registration_date[1].split("-")[::-1])])
        await update.message.reply_text(COMMANDS[get_user_language(user_name)]["findchannel"]["response"].format(
            title, subscriberCount, videoCount, viewCount, registration_date), parse_mode="MarkDown")
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
        url = f'https://www.youtube.com/watch?v={response["items"][0]["id"]}'
        description = response["items"][0]["snippet"]["description"]
        duration = response["items"][0]["contentDetails"]["duration"]
        duration = convert_duration(duration)
        commentCount = response["items"][0]["statistics"].get("commentCount")
        if not commentCount:
            commentCount = 0
        else:
            commentCount = ''.join(
                [" " + value if key % 3 == 0 and key != 0 else value for key, value in enumerate(commentCount[::-1])])[
                           ::-1]
        likeCount = response["items"][0]["statistics"]["likeCount"]
        likeCount = ''.join(
            [" " + value if key % 3 == 0 and key != 0 else value for key, value in enumerate(likeCount[::-1])])[::-1]
        viewCount = response["items"][0]["statistics"]["viewCount"]
        viewCount = ''.join(
            [" " + value if key % 3 == 0 and key != 0 else value for key, value in enumerate(viewCount[::-1])])[::-1]
        publication_date = "".join(response["items"][0]["snippet"]["publishedAt"].split("T")[::-1]).split("Z")
        publication_date = " ".join([publication_date[0], "-".join(publication_date[1].split("-")[::-1])])
        await update.message.reply_text(COMMANDS[get_user_language(user_name)]["findvideo"]["response"].format(
            title, url, description, duration, viewCount, publication_date, likeCount, commentCount), parse_mode="HTML")
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
    try:
        my_video = YouTube(video_url)
        video_path = my_video.streams.get_lowest_resolution().download()
        if os.path.getsize(video_path) > 50 * 1024 * 1024:
            video_files = split_video(os.path.getsize(video_path), video_path)
            video_path = "output{}.mp4"
        else:
            video_files = [[open(video_path, "rb").read(), VideoFileClip(video_path).duration]]
        size = VideoFileClip(video_path.format(1)).w, VideoFileClip(video_path.format(1)).h
        for part_num, file_part in enumerate(video_files, start=1):
            params = {
                "duration": file_part[1],
                "width": size[0],
                "height": size[1],
                "supports_streaming": True,
                "read_timeout": 1000,
                "write_timeout": 1000,
                "pool_timeout": 1000,
                "connect_timeout": 1000
            }
            await update.message.reply_video(file_part[0], api_kwargs=params)
            os.remove(video_path.format(part_num))
    except Exception:
        await update.message.reply_text(COMMANDS[get_user_language(user_name)]["downloadvideo"]["error"])
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