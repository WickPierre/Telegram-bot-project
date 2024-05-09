import os
import math
from moviepy.editor import VideoFileClip, AudioFileClip


def sol(video_name, audio_name):
    video_clip = VideoFileClip(video_name)
    audio_clip = AudioFileClip(audio_name)

    audio_clip = audio_clip.volumex(1.0)
    start = 0
    end = video_clip.end
    audio_clip = audio_clip.subclip(start, end)

    final_audio = audio_clip
    final_clip = video_clip.set_audio(final_audio)


def split_video(size, filename):
    video_file = VideoFileClip(filename, audio=True)
    duration = video_file.duration
    k = duration / size
    part_duration = k * 50 * 1024 * 1024
    dur1 = 0
    dur2 = part_duration
    e = 1
    number_of_videos = math.ceil(duration / part_duration)
    for i in range(number_of_videos):
        clip = video_file.subclip(dur1, dur2)
        clip.write_videofile(f"output{e}.mp4", audio_codec="aac")
        e += 1
        dur1 += part_duration
        if duration < part_duration * e:
            dur2 = duration
        else:
            dur2 += part_duration

split_video("")

# file_parts = []
# i = 1
# e = 0
# size = os.path.getsize("123.mp4")
# video_file = open("123.mp4", "rb")
# while True:
#     data = video_file.read(20971520)
#     if not data:
#         break
#     s = open(str(i) + ".mp4", "wb")
#     s.write(data)
#     i += 1