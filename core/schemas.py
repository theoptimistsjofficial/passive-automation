from pydantic import BaseModel, Field
from typing import List, Optional


class Slide(BaseModel):
    index: int
    heading: str
    body: str
    narration: str
    stock_query: str


class VideoScript(BaseModel):
    topic_id: str
    title_working: str
    hook: str
    slides: List[Slide]
    cta: str


class SEOPackage(BaseModel):
    title: str = Field(..., max_length=100)
    description: str
    tags: List[str]
    hashtags: List[str]


class QualityVerdict(BaseModel):
    approved: bool
    reasons: List[str] = []


class RenderedVideo(BaseModel):
    topic_id: str
    mp4_path: str
    thumbnail_path: Optional[str] = None
    duration_seconds: float
    seo: SEOPackage
    youtube_video_id: Optional[str] = None
