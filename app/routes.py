from fastapi import APIRouter, Query, BackgroundTasks, HTTPException
from app.schema import SeparateFromLinkRequest, SongMetadata
from app import service
from app.spotify import search_spotify_track

router = APIRouter()

@router.get(
    "/search-track/",
    summary="Search Track on Spotify",
    description="Search for a track on Spotify by name (and optional artist) and return metadata.",
    response_model=SongMetadata,
)
def search_track(
    query: str = Query(..., description="The search query (e.g. 'Song Name Artist Name')")
):
    track = search_spotify_track(query)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found on Spotify")
    
    release_date = track["album"].get("release_date", "")
    year = int(release_date[:4]) if release_date and len(release_date) >= 4 else 0
    
    return SongMetadata(
        title=track["name"],
        artists=[a["name"] for a in track["artists"]],
        album={
            "name": track["album"]["name"],
            "images": [i["url"] for i in track["album"]["images"]]
        },
        duration=int(track["duration_ms"] / 1000),
        youtube_views=0, # Not available from Spotify
        year=year
    )

@router.post(
    "/separate-from-link/",
    summary="Separate Audio from Link",
    description="Provide a YouTube or Spotify URL and get separated audio stems.",
)
async def separate_from_link(
    request: SeparateFromLinkRequest,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(
        service.process_link_separation_task,
        request.url,
        request.start_time,
        request.duration,
        request.callback_url
    )
    return {"message": "Request received and processing started", "status": "pending"}

@router.get(
    "/list-directories/",
    summary="List Directories in Bucket",
    description="Lists all directories in the mp3files bucket or objects inside a specific directory.",
)
def list_directories(
    directory: str | None = Query(
        None,
        description="The directory to list objects from. If not specified, lists all directories.",
    )
):
    return service.list_bucket_directories(directory)