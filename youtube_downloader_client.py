from pytube import YouTube


def video_downloader(video_url):
    my_video = YouTube(video_url)
    my_video.streams.get_highest_resolution().download()
    return my_video.title


video_downloader("https://www.youtube.com/watch?v=h_o3ZGZ3jL8&t=36s")