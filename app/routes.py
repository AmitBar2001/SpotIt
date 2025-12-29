from fastapi import APIRouter, Query, BackgroundTasks
from app.schema import SeparateFromLinkRequest
from app import service

router = APIRouter()

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