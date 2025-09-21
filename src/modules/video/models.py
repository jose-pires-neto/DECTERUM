import uuid
import time
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class Video:
    """Modelo para vídeos do sistema"""
    id: str
    author_id: str
    author_username: str
    title: str
    description: str
    video_url: str
    thumbnail_url: str
    duration: int  # em segundos
    video_type: str  # "short" (<= 60s) ou "long" (> 60s)
    resolution: str  # "720p", "1080p", "4K", etc.
    size_bytes: int
    mime_type: str
    timestamp: float
    views_count: int = 0
    likes_count: int = 0
    dislikes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    is_public: bool = True
    is_monetized: bool = False
    tags: List[str] = None
    category: str = "general"  # gaming, music, education, entertainment, etc.
    language: str = "pt-BR"
    quality_levels: List[str] = None  # ["720p", "1080p"]
    chapters: List[Dict] = None  # [{"time": 0, "title": "Intro"}]
    subtitles_url: Optional[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.quality_levels is None:
            self.quality_levels = ["720p"]
        if self.chapters is None:
            self.chapters = []
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def create(cls, author_id: str, author_username: str, title: str,
               description: str, video_url: str, thumbnail_url: str,
               duration: int, resolution: str, size_bytes: int, mime_type: str):
        """Cria um novo vídeo"""
        video_type = "short" if duration <= 60 else "long"

        return cls(
            id=str(uuid.uuid4()),
            author_id=author_id,
            author_username=author_username,
            title=title,
            description=description,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            duration=duration,
            video_type=video_type,
            resolution=resolution,
            size_bytes=size_bytes,
            mime_type=mime_type,
            timestamp=time.time()
        )

    @property
    def formatted_duration(self) -> str:
        """Retorna duração formatada"""
        if self.duration < 60:
            return f"{self.duration}s"
        elif self.duration < 3600:
            mins = self.duration // 60
            secs = self.duration % 60
            return f"{mins}:{secs:02d}"
        else:
            hours = self.duration // 3600
            mins = (self.duration % 3600) // 60
            secs = self.duration % 60
            return f"{hours}:{mins:02d}:{secs:02d}"

    @property
    def formatted_size(self) -> str:
        """Retorna tamanho formatado"""
        if self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.1f} GB"

    @property
    def formatted_views(self) -> str:
        """Retorna visualizações formatadas"""
        if self.views_count < 1000:
            return str(self.views_count)
        elif self.views_count < 1000000:
            return f"{self.views_count / 1000:.1f}K"
        else:
            return f"{self.views_count / 1000000:.1f}M"

    @property
    def is_short(self) -> bool:
        """Verifica se é um short"""
        return self.video_type == "short"

    @property
    def engagement_rate(self) -> float:
        """Calcula taxa de engajamento"""
        if self.views_count == 0:
            return 0.0
        return (self.likes_count + self.comments_count + self.shares_count) / self.views_count


@dataclass
class VideoLike:
    """Modelo para likes/dislikes em vídeos"""
    id: str
    video_id: str
    user_id: str
    username: str
    like_type: str  # "like" ou "dislike"
    timestamp: float

    @classmethod
    def create(cls, video_id: str, user_id: str, username: str, like_type: str):
        """Cria um novo like/dislike"""
        return cls(
            id=str(uuid.uuid4()),
            video_id=video_id,
            user_id=user_id,
            username=username,
            like_type=like_type,
            timestamp=time.time()
        )


@dataclass
class VideoComment:
    """Modelo para comentários em vídeos"""
    id: str
    video_id: str
    author_id: str
    author_username: str
    content: str
    timestamp: float
    parent_comment_id: Optional[str] = None  # Para respostas
    likes_count: int = 0
    replies_count: int = 0
    is_pinned: bool = False
    is_creator_reply: bool = False  # Se é resposta do criador do vídeo

    @classmethod
    def create(cls, video_id: str, author_id: str, author_username: str,
               content: str, parent_comment_id: Optional[str] = None):
        """Cria um novo comentário"""
        return cls(
            id=str(uuid.uuid4()),
            video_id=video_id,
            author_id=author_id,
            author_username=author_username,
            content=content,
            timestamp=time.time(),
            parent_comment_id=parent_comment_id
        )


@dataclass
class VideoView:
    """Modelo para visualizações de vídeos"""
    id: str
    video_id: str
    viewer_id: str
    viewer_username: str
    watch_time: int  # segundos assistidos
    completion_rate: float  # percentual assistido
    timestamp: float
    device_type: str = "web"  # web, mobile, desktop
    quality_watched: str = "720p"

    @classmethod
    def create(cls, video_id: str, viewer_id: str, viewer_username: str,
               watch_time: int, completion_rate: float):
        """Cria uma nova visualização"""
        return cls(
            id=str(uuid.uuid4()),
            video_id=video_id,
            viewer_id=viewer_id,
            viewer_username=viewer_username,
            watch_time=watch_time,
            completion_rate=completion_rate,
            timestamp=time.time()
        )


@dataclass
class VideoPlaylist:
    """Modelo para playlists de vídeos"""
    id: str
    creator_id: str
    creator_username: str
    title: str
    description: str
    is_public: bool
    video_ids: List[str]
    thumbnail_url: Optional[str]
    timestamp: float
    views_count: int = 0

    def __post_init__(self):
        if self.video_ids is None:
            self.video_ids = []

    @classmethod
    def create(cls, creator_id: str, creator_username: str, title: str,
               description: str, is_public: bool = True):
        """Cria uma nova playlist"""
        return cls(
            id=str(uuid.uuid4()),
            creator_id=creator_id,
            creator_username=creator_username,
            title=title,
            description=description,
            is_public=is_public,
            video_ids=[],
            thumbnail_url=None,
            timestamp=time.time()
        )

    @property
    def video_count(self) -> int:
        """Retorna número de vídeos na playlist"""
        return len(self.video_ids)


@dataclass
class VideoShare:
    """Modelo para compartilhamentos de vídeos"""
    id: str
    video_id: str
    sharer_id: str
    sharer_username: str
    platform: str  # "internal", "external", "download"
    timestamp: float

    @classmethod
    def create(cls, video_id: str, sharer_id: str, sharer_username: str, platform: str):
        """Cria um novo compartilhamento"""
        return cls(
            id=str(uuid.uuid4()),
            video_id=video_id,
            sharer_id=sharer_id,
            sharer_username=sharer_username,
            platform=platform,
            timestamp=time.time()
        )


# Constantes
VIDEO_CATEGORIES = {
    "gaming": "Gaming",
    "music": "Música",
    "education": "Educação",
    "entertainment": "Entretenimento",
    "news": "Notícias",
    "sports": "Esportes",
    "technology": "Tecnologia",
    "lifestyle": "Estilo de Vida",
    "comedy": "Comédia",
    "tutorial": "Tutorial",
    "review": "Review",
    "vlog": "Vlog",
    "general": "Geral"
}

VIDEO_QUALITIES = {
    "240p": "240p",
    "360p": "360p",
    "480p": "480p",
    "720p": "HD (720p)",
    "1080p": "Full HD (1080p)",
    "1440p": "2K (1440p)",
    "2160p": "4K (2160p)"
}

SUPPORTED_VIDEO_FORMATS = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
    "video/avi": ".avi",
    "video/mov": ".mov"
}

# Limites do sistema
MAX_SHORT_DURATION = 60  # segundos
MAX_LONG_DURATION = 36000  # 10 horas em segundos
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB em bytes
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 5000