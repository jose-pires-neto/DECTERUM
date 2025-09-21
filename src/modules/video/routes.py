from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import os
import uuid
import json
import logging
from datetime import datetime
from ..video.service import VideoService
from ..video.models import SUPPORTED_VIDEO_FORMATS, MAX_FILE_SIZE, MAX_TITLE_LENGTH, MAX_DESCRIPTION_LENGTH
from ...core.database import Database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/videos", tags=["videos"])

# Dependency para obter o serviço de vídeos
def get_video_service():
    db = Database()
    return VideoService(db)

# ========== ENDPOINTS DE VÍDEOS ==========

@router.post("/upload")
async def upload_video(
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("general"),
    tags: str = Form(""),
    is_public: bool = Form(True),
    video_file: UploadFile = File(...),
    thumbnail_file: Optional[UploadFile] = File(None),
    author_id: str = Form(...),
    author_username: str = Form(...),
    video_service: VideoService = Depends(get_video_service)
):
    """Upload de vídeo"""
    try:
        # Validações básicas
        if len(title) > MAX_TITLE_LENGTH:
            raise HTTPException(400, f"Título muito longo. Máximo {MAX_TITLE_LENGTH} caracteres.")

        if len(description) > MAX_DESCRIPTION_LENGTH:
            raise HTTPException(400, f"Descrição muito longa. Máximo {MAX_DESCRIPTION_LENGTH} caracteres.")

        if video_file.content_type not in SUPPORTED_VIDEO_FORMATS:
            raise HTTPException(400, f"Formato não suportado. Use: {', '.join(SUPPORTED_VIDEO_FORMATS.keys())}")

        # Verificar tamanho do arquivo
        video_content = await video_file.read()
        if len(video_content) > MAX_FILE_SIZE:
            raise HTTPException(400, f"Arquivo muito grande. Máximo {MAX_FILE_SIZE // (1024**3)}GB.")

        # Gerar nomes únicos para os arquivos
        video_filename = f"{uuid.uuid4()}{SUPPORTED_VIDEO_FORMATS[video_file.content_type]}"
        video_path = os.path.join(video_service.video_storage_path, video_filename)

        # Salvar arquivo de vídeo
        with open(video_path, "wb") as f:
            f.write(video_content)

        # Processar thumbnail
        thumbnail_url = None
        if thumbnail_file and thumbnail_file.content_type.startswith("image/"):
            thumbnail_filename = f"{uuid.uuid4()}.jpg"
            thumbnail_path = os.path.join(video_service.thumbnail_storage_path, thumbnail_filename)

            thumbnail_content = await thumbnail_file.read()
            with open(thumbnail_path, "wb") as f:
                f.write(thumbnail_content)

            thumbnail_url = f"/api/videos/thumbnail/{thumbnail_filename}"

        # Processar tags
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

        # Simular extração de metadados do vídeo (em produção, usar biblioteca como ffmpeg-python)
        duration = 120  # segundos - seria extraído do arquivo real
        resolution = "720p"  # seria detectado automaticamente

        # Criar vídeo
        video = video_service.create_video(
            author_id=author_id,
            author_username=author_username,
            title=title,
            description=description,
            video_url=f"/api/videos/stream/{video_filename}",
            thumbnail_url=thumbnail_url,
            duration=duration,
            resolution=resolution,
            size_bytes=len(video_content),
            mime_type=video_file.content_type,
            tags=tag_list,
            category=category,
            is_public=is_public
        )

        return {
            "success": True,
            "video_id": video.id,
            "message": "Vídeo enviado com sucesso!",
            "video_type": video.video_type
        }

    except Exception as e:
        logger.error(f"Erro no upload: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.get("/stream/{filename}")
async def stream_video(filename: str, video_service: VideoService = Depends(get_video_service)):
    """Stream de vídeo"""
    video_path = os.path.join(video_service.video_storage_path, filename)

    if not os.path.exists(video_path):
        raise HTTPException(404, "Vídeo não encontrado")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"}
    )

@router.get("/thumbnail/{filename}")
async def get_thumbnail(filename: str, video_service: VideoService = Depends(get_video_service)):
    """Obter thumbnail"""
    thumbnail_path = os.path.join(video_service.thumbnail_storage_path, filename)

    if not os.path.exists(thumbnail_path):
        raise HTTPException(404, "Thumbnail não encontrada")

    return FileResponse(thumbnail_path, media_type="image/jpeg")

@router.get("/")
async def get_videos(
    video_type: Optional[str] = Query(None, description="short ou long"),
    category: Optional[str] = Query(None),
    author_id: Optional[str] = Query(None),
    sort_by: str = Query("timestamp", description="timestamp, views, likes, duration"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    video_service: VideoService = Depends(get_video_service)
):
    """Listar vídeos com filtros"""
    try:
        videos = video_service.get_videos(
            video_type=video_type,
            category=category,
            author_id=author_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by
        )

        return {
            "success": True,
            "videos": videos,
            "count": len(videos),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Erro ao buscar vídeos: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.get("/shorts")
async def get_shorts_feed(
    user_id: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    video_service: VideoService = Depends(get_video_service)
):
    """Feed de shorts personalizado"""
    try:
        shorts = video_service.get_shorts_feed(user_id, limit)

        return {
            "success": True,
            "shorts": shorts,
            "count": len(shorts)
        }

    except Exception as e:
        logger.error(f"Erro ao buscar shorts: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.get("/trending")
async def get_trending_videos(
    video_type: Optional[str] = Query(None, description="short ou long"),
    limit: int = Query(20, ge=1, le=50),
    video_service: VideoService = Depends(get_video_service)
):
    """Vídeos em tendência"""
    try:
        trending = video_service.get_trending_videos(video_type, limit)

        return {
            "success": True,
            "trending": trending,
            "count": len(trending)
        }

    except Exception as e:
        logger.error(f"Erro ao buscar trending: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.get("/search")
async def search_videos(
    q: str = Query(..., min_length=1, description="Termo de busca"),
    video_type: Optional[str] = Query(None, description="short ou long"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    video_service: VideoService = Depends(get_video_service)
):
    """Buscar vídeos"""
    try:
        results = video_service.search_videos(q, video_type, limit, offset)

        return {
            "success": True,
            "query": q,
            "results": results,
            "count": len(results),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Erro na busca: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.get("/{video_id}")
async def get_video(
    video_id: str,
    video_service: VideoService = Depends(get_video_service)
):
    """Obter vídeo por ID"""
    try:
        video = video_service.get_video_by_id(video_id)

        if not video:
            raise HTTPException(404, "Vídeo não encontrado")

        return {
            "success": True,
            "video": video
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar vídeo: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

# ========== ENDPOINTS DE INTERAÇÃO ==========

@router.post("/{video_id}/like")
async def like_video(
    video_id: str,
    user_id: str = Form(...),
    username: str = Form(...),
    like_type: str = Form(..., description="like ou dislike"),
    video_service: VideoService = Depends(get_video_service)
):
    """Curtir/descurtir vídeo"""
    try:
        if like_type not in ["like", "dislike"]:
            raise HTTPException(400, "like_type deve ser 'like' ou 'dislike'")

        success = video_service.like_video(video_id, user_id, username, like_type)

        if not success:
            raise HTTPException(400, "Erro ao processar like")

        return {
            "success": True,
            "message": f"{'Like' if like_type == 'like' else 'Dislike'} registrado"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no like: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.post("/{video_id}/comment")
async def add_comment(
    video_id: str,
    author_id: str = Form(...),
    author_username: str = Form(...),
    content: str = Form(..., min_length=1, max_length=1000),
    parent_comment_id: Optional[str] = Form(None),
    video_service: VideoService = Depends(get_video_service)
):
    """Adicionar comentário"""
    try:
        comment = video_service.add_comment(
            video_id=video_id,
            author_id=author_id,
            author_username=author_username,
            content=content,
            parent_comment_id=parent_comment_id
        )

        return {
            "success": True,
            "comment_id": comment.id,
            "message": "Comentário adicionado com sucesso"
        }

    except Exception as e:
        logger.error(f"Erro ao adicionar comentário: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.get("/{video_id}/comments")
async def get_video_comments(
    video_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    video_service: VideoService = Depends(get_video_service)
):
    """Obter comentários do vídeo"""
    try:
        comments = video_service.get_video_comments(video_id, limit, offset)

        return {
            "success": True,
            "video_id": video_id,
            "comments": comments,
            "count": len(comments),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Erro ao buscar comentários: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.post("/{video_id}/view")
async def record_view(
    video_id: str,
    viewer_id: str = Form(...),
    viewer_username: str = Form(...),
    watch_time: int = Form(..., ge=0),
    completion_rate: float = Form(..., ge=0.0, le=1.0),
    device_type: str = Form("web"),
    quality_watched: str = Form("720p"),
    video_service: VideoService = Depends(get_video_service)
):
    """Registrar visualização"""
    try:
        view = video_service.record_view(
            video_id=video_id,
            viewer_id=viewer_id,
            viewer_username=viewer_username,
            watch_time=watch_time,
            completion_rate=completion_rate
        )

        return {
            "success": True,
            "view_id": view.id,
            "message": "Visualização registrada"
        }

    except Exception as e:
        logger.error(f"Erro ao registrar visualização: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.post("/{video_id}/share")
async def share_video(
    video_id: str,
    sharer_id: str = Form(...),
    sharer_username: str = Form(...),
    platform: str = Form(..., description="internal, external, download"),
    video_service: VideoService = Depends(get_video_service)
):
    """Compartilhar vídeo"""
    try:
        share = video_service.share_video(
            video_id=video_id,
            sharer_id=sharer_id,
            sharer_username=sharer_username,
            platform=platform
        )

        return {
            "success": True,
            "share_id": share.id,
            "message": "Compartilhamento registrado"
        }

    except Exception as e:
        logger.error(f"Erro ao compartilhar: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

# ========== ENDPOINTS DE PLAYLISTS ==========

@router.post("/playlists")
async def create_playlist(
    creator_id: str = Form(...),
    creator_username: str = Form(...),
    title: str = Form(..., max_length=200),
    description: str = Form("", max_length=1000),
    is_public: bool = Form(True),
    video_service: VideoService = Depends(get_video_service)
):
    """Criar playlist"""
    try:
        playlist = video_service.create_playlist(
            creator_id=creator_id,
            creator_username=creator_username,
            title=title,
            description=description,
            is_public=is_public
        )

        return {
            "success": True,
            "playlist_id": playlist.id,
            "message": "Playlist criada com sucesso"
        }

    except Exception as e:
        logger.error(f"Erro ao criar playlist: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.post("/playlists/{playlist_id}/videos")
async def add_video_to_playlist(
    playlist_id: str,
    video_id: str = Form(...),
    user_id: str = Form(...),
    video_service: VideoService = Depends(get_video_service)
):
    """Adicionar vídeo à playlist"""
    try:
        success = video_service.add_video_to_playlist(playlist_id, video_id, user_id)

        if not success:
            raise HTTPException(403, "Não autorizado ou playlist não encontrada")

        return {
            "success": True,
            "message": "Vídeo adicionado à playlist"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao adicionar à playlist: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@router.get("/playlists/user/{user_id}")
async def get_user_playlists(
    user_id: str,
    video_service: VideoService = Depends(get_video_service)
):
    """Obter playlists do usuário"""
    try:
        playlists = video_service.get_user_playlists(user_id)

        return {
            "success": True,
            "user_id": user_id,
            "playlists": playlists,
            "count": len(playlists)
        }

    except Exception as e:
        logger.error(f"Erro ao buscar playlists: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

# ========== ENDPOINTS DE ANALYTICS ==========

@router.get("/{video_id}/analytics")
async def get_video_analytics(
    video_id: str,
    author_id: str = Query(..., description="ID do autor do vídeo"),
    video_service: VideoService = Depends(get_video_service)
):
    """Obter analytics do vídeo (apenas para o autor)"""
    try:
        analytics = video_service.get_video_analytics(video_id, author_id)

        if not analytics:
            raise HTTPException(403, "Acesso negado ou vídeo não encontrado")

        return {
            "success": True,
            "analytics": analytics
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar analytics: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

# ========== ENDPOINTS UTILITÁRIOS ==========

@router.get("/categories")
async def get_categories():
    """Listar categorias disponíveis"""
    from ..video.models import VIDEO_CATEGORIES

    return {
        "success": True,
        "categories": VIDEO_CATEGORIES
    }

@router.get("/formats")
async def get_supported_formats():
    """Listar formatos suportados"""
    return {
        "success": True,
        "formats": SUPPORTED_VIDEO_FORMATS,
        "max_file_size": MAX_FILE_SIZE,
        "max_duration": {
            "short": 60,
            "long": 36000
        }
    }