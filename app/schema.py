from pydantic import BaseModel, Field, HttpUrl
from typing import Literal

StatusOptions = Literal["pending", "in_progress", "completed", "failed"]
FileKey = Literal["drums", "bass", "guitar", "other", "original"]

class TaskStatusUpdate(BaseModel):
    status: StatusOptions = Field(..., description="Current status of the task")
    message: str = Field(description="Optional message providing additional information about the task status")

class SeparateFromLinkRequest(BaseModel):
    url: HttpUrl = Field(..., description="The YouTube or Spotify URL")
    start_time: int | None = Field(None, ge=0, description="Start time in seconds for the audio clip. If not specified, will be auto-picked using the heatmap.")
    duration: int = Field(30, gt=0, le=300, description="Duration of the audio clip in seconds (max 300).")
    callback_url: HttpUrl = Field(..., description="URL to receive task status updates via POST requests.")

class SongMetadata(BaseModel):
    title: str = Field(..., description="Title of the song")
    artists: list[str] = Field(..., description="Artists of the song")
    album: str = Field(..., description="Album of the song")
    duration: int = Field(..., description="Duration of the song in seconds")
    youtube_views: int = Field(..., description="Number of YouTube views for the song")
    year: int = Field(..., description="Release year of the song")

class UpdateTaskBody(BaseModel):
    task_status: TaskStatusUpdate = Field(..., description="Status update for the task")
    song_metadata: SongMetadata = Field(..., description="Metadata of the song")
    file_keys: dict[FileKey, str] = Field(..., description="Mapping of file (object storage) keys for the song files")
    