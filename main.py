from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pytube import YouTube, Playlist

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

clients = {}

@app.get("/", response_class=HTMLResponse)
def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def download_playlist(playlist_url):
    playlist = Playlist(playlist_url)
    video_info = []
    for video in playlist.videos:
        yt = YouTube(video.watch_url)
        video_streams = yt.streams.filter(
            progressive=True, file_extension='mp4').order_by('resolution').desc()
        video_links = [{"resolution": stream.resolution,
                        "url": stream.url} for stream in video_streams]
        video_info.append({"title": yt.title, "links": video_links})
    return video_info, playlist.title


@app.post("/submit", response_class=HTMLResponse)
async def submit_youtube_link(request: Request, youtube_link: str = Form(...)):
    try:
        if "playlist" in youtube_link:
            video_info, playlist_title = download_playlist(youtube_link)
            clients[request.client.host] = {
                "request": request,
                "video_info": video_info,
                "playlist_title": playlist_title,
            }
            return templates.TemplateResponse("playlist.html", clients[request.client.host])
        else:
            yt = YouTube(youtube_link)
            video_streams = yt.streams.filter(
                progressive=True, file_extension='mp4').order_by('resolution').desc()
            audio_streams = yt.streams.filter(
                only_audio=True).order_by('abr').desc()
            video_links = [{"resolution": stream.resolution,
                            "url": stream.url} for stream in video_streams]
            audio_links = [{"abr": stream.abr, "url": stream.url}
                        for stream in audio_streams]
            clients[request.client.host] = {
                "request": request,
                "video_links": video_links,
                "audio_links": audio_links,
                "video_title": yt.title,
            }
            print(len(clients))
            return templates.TemplateResponse("result.html", clients[request.client.host])
    except:
        raise HTTPException(status_code=400)
    

@app.middleware("http")
async def remove_client_on_disconnect(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 200:
        return response
    clients.pop(request.client.host, None)
    return response