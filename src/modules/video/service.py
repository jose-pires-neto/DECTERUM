import sqlite3
import json
import time
import os
import logging
from typing import List, Dict, Optional, Tuple
from ..video.models import (
    Video, VideoLike, VideoComment, VideoView, VideoPlaylist, VideoShare,
    VIDEO_CATEGORIES, MAX_SHORT_DURATION, MAX_LONG_DURATION, MAX_FILE_SIZE
)

logger = logging.getLogger(__name__)


class VideoService:
    """Serviço principal para operações do módulo de vídeos"""

    def __init__(self, database):
        self.db = database
        self.video_storage_path = "storage/videos"
        self.thumbnail_storage_path = "storage/thumbnails"
        self._ensure_storage_dirs()

    def _ensure_storage_dirs(self):
        """Garante que os diretórios de armazenamento existam"""
        os.makedirs(self.video_storage_path, exist_ok=True)
        os.makedirs(self.thumbnail_storage_path, exist_ok=True)

    # ========== VÍDEOS ==========

    def create_video(self, author_id: str, author_username: str, title: str,
                    description: str, video_url: str, thumbnail_url: str,
                    duration: int, resolution: str, size_bytes: int,
                    mime_type: str, **kwargs) -> Video:
        """Cria um novo vídeo"""

        # Validações
        if duration > MAX_LONG_DURATION:
            raise ValueError(f"Duração máxima permitida: {MAX_LONG_DURATION // 3600}h")

        if size_bytes > MAX_FILE_SIZE:
            raise ValueError(f"Tamanho máximo permitido: {MAX_FILE_SIZE // (1024**3)}GB")

        video = Video.create(
            author_id=author_id,
            author_username=author_username,
            title=title,
            description=description,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            duration=duration,
            resolution=resolution,
            size_bytes=size_bytes,
            mime_type=mime_type
        )

        # Aplicar metadados opcionais
        if 'tags' in kwargs:
            video.tags = kwargs['tags']
        if 'category' in kwargs:
            video.category = kwargs['category']
        if 'is_public' in kwargs:
            video.is_public = kwargs['is_public']

        self._save_video(video)
        logger.info(f"Vídeo criado: {video.id} ({video.video_type}) por {author_username}")
        return video

    def get_videos(self, video_type: Optional[str] = None, category: Optional[str] = None,
                  author_id: Optional[str] = None, limit: int = 20, offset: int = 0,
                  sort_by: str = "timestamp") -> List[Dict]:
        """Obtém lista de vídeos com filtros"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        # Construir query dinâmica
        where_conditions = ["is_public = 1"]
        params = []

        if video_type:
            where_conditions.append("video_type = ?")
            params.append(video_type)

        if category:
            where_conditions.append("category = ?")
            params.append(category)

        if author_id:
            where_conditions.append("author_id = ?")
            params.append(author_id)

        where_clause = " AND ".join(where_conditions)

        order_clause = {
            "timestamp": "ORDER BY timestamp DESC",
            "views": "ORDER BY views_count DESC",
            "likes": "ORDER BY likes_count DESC",
            "duration": "ORDER BY duration ASC"
        }.get(sort_by, "ORDER BY timestamp DESC")

        query = f'''
            SELECT * FROM videos
            WHERE {where_clause}
            {order_clause}
            LIMIT ? OFFSET ?
        '''

        cursor.execute(query, params + [limit, offset])
        videos = []

        for row in cursor.fetchall():
            video_data = self._row_to_video_dict(row)
            videos.append(video_data)

        conn.close()
        return videos

    def get_video_by_id(self, video_id: str) -> Optional[Dict]:
        """Busca vídeo por ID"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_video_dict(row)
        return None

    def get_shorts_feed(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Obtém feed de shorts personalizado"""
        return self.get_videos(
            video_type="short",
            limit=limit,
            sort_by="timestamp"
        )

    def get_trending_videos(self, video_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Obtém vídeos em tendência"""
        return self.get_videos(
            video_type=video_type,
            limit=limit,
            sort_by="views"
        )

    def search_videos(self, query: str, video_type: Optional[str] = None,
                     limit: int = 20, offset: int = 0) -> List[Dict]:
        """Busca vídeos por termo"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        where_conditions = ["is_public = 1"]
        params = []

        # Busca em título, descrição e tags
        search_condition = "(title LIKE ? OR description LIKE ? OR tags LIKE ?)"
        search_term = f"%{query}%"
        where_conditions.append(search_condition)
        params.extend([search_term, search_term, search_term])

        if video_type:
            where_conditions.append("video_type = ?")
            params.append(video_type)

        where_clause = " AND ".join(where_conditions)

        cursor.execute(f'''
            SELECT * FROM videos
            WHERE {where_clause}
            ORDER BY views_count DESC, timestamp DESC
            LIMIT ? OFFSET ?
        ''', params + [limit, offset])

        videos = []
        for row in cursor.fetchall():
            video_data = self._row_to_video_dict(row)
            videos.append(video_data)

        conn.close()
        return videos

    # ========== INTERAÇÕES ==========

    def like_video(self, video_id: str, user_id: str, username: str,
                  like_type: str) -> bool:
        """Like/dislike em vídeo"""
        if like_type not in ["like", "dislike"]:
            return False

        # Verificar se já curtiu/descurtiu
        existing_like = self._get_user_like(video_id, user_id)

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        if existing_like:
            if existing_like['like_type'] == like_type:
                # Remover like se é o mesmo tipo
                cursor.execute('DELETE FROM video_likes WHERE id = ?', (existing_like['id'],))
            else:
                # Atualizar para o tipo oposto
                cursor.execute(
                    'UPDATE video_likes SET like_type = ?, timestamp = ? WHERE id = ?',
                    (like_type, time.time(), existing_like['id'])
                )
        else:
            # Criar novo like
            like = VideoLike.create(video_id, user_id, username, like_type)
            cursor.execute('''
                INSERT INTO video_likes (id, video_id, user_id, username, like_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (like.id, like.video_id, like.user_id, like.username, like.like_type, like.timestamp))

        conn.commit()
        conn.close()

        # Atualizar contadores do vídeo
        self._update_video_counters(video_id)
        return True

    def add_comment(self, video_id: str, author_id: str, author_username: str,
                   content: str, parent_comment_id: Optional[str] = None) -> VideoComment:
        """Adiciona comentário ao vídeo"""
        comment = VideoComment.create(video_id, author_id, author_username, content, parent_comment_id)
        self._save_comment(comment)

        # Verificar se é resposta do criador do vídeo
        video = self.get_video_by_id(video_id)
        if video and video['author_id'] == author_id:
            self._update_comment_creator_flag(comment.id, True)

        # Atualizar contador de comentários
        if not parent_comment_id:  # Só contar comentários principais
            self._increment_video_comments(video_id)

        return comment

    def get_video_comments(self, video_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Obtém comentários de um vídeo"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM video_comments
            WHERE video_id = ? AND parent_comment_id IS NULL
            ORDER BY likes_count DESC, timestamp DESC
            LIMIT ? OFFSET ?
        ''', (video_id, limit, offset))

        comments = []
        for row in cursor.fetchall():
            comment_data = self._row_to_comment_dict(row)

            # Carregar respostas
            comment_data['replies'] = self._get_comment_replies(comment_data['id'])
            comments.append(comment_data)

        conn.close()
        return comments

    def record_view(self, video_id: str, viewer_id: str, viewer_username: str,
                   watch_time: int, completion_rate: float) -> VideoView:
        """Registra visualização de vídeo"""
        view = VideoView.create(video_id, viewer_id, viewer_username, watch_time, completion_rate)
        self._save_view(view)

        # Incrementar contador apenas se assistiu pelo menos 30% ou 30 segundos
        if completion_rate >= 0.3 or watch_time >= 30:
            self._increment_video_views(video_id)

        return view

    def share_video(self, video_id: str, sharer_id: str, sharer_username: str,
                   platform: str) -> VideoShare:
        """Registra compartilhamento de vídeo"""
        share = VideoShare.create(video_id, sharer_id, sharer_username, platform)
        self._save_share(share)
        self._increment_video_shares(video_id)
        return share

    # ========== PLAYLISTS ==========

    def create_playlist(self, creator_id: str, creator_username: str,
                       title: str, description: str, is_public: bool = True) -> VideoPlaylist:
        """Cria nova playlist"""
        playlist = VideoPlaylist.create(creator_id, creator_username, title, description, is_public)
        self._save_playlist(playlist)
        return playlist

    def add_video_to_playlist(self, playlist_id: str, video_id: str, user_id: str) -> bool:
        """Adiciona vídeo à playlist"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        # Verificar se o usuário é dono da playlist
        cursor.execute('SELECT creator_id, video_ids FROM playlists WHERE id = ?', (playlist_id,))
        row = cursor.fetchone()

        if not row or row[0] != user_id:
            conn.close()
            return False

        current_video_ids = json.loads(row[1]) if row[1] else []

        if video_id not in current_video_ids:
            current_video_ids.append(video_id)
            cursor.execute(
                'UPDATE playlists SET video_ids = ? WHERE id = ?',
                (json.dumps(current_video_ids), playlist_id)
            )
            conn.commit()

        conn.close()
        return True

    def get_user_playlists(self, user_id: str) -> List[Dict]:
        """Obtém playlists do usuário"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM playlists
            WHERE creator_id = ?
            ORDER BY timestamp DESC
        ''', (user_id,))

        playlists = []
        for row in cursor.fetchall():
            playlist_data = self._row_to_playlist_dict(row)
            playlists.append(playlist_data)

        conn.close()
        return playlists

    # ========== ANALYTICS ==========

    def get_video_analytics(self, video_id: str, author_id: str) -> Dict:
        """Obtém analytics de um vídeo (apenas para o autor)"""
        video = self.get_video_by_id(video_id)
        if not video or video['author_id'] != author_id:
            return {}

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        # Estatísticas de visualização
        cursor.execute('''
            SELECT
                COUNT(*) as total_views,
                AVG(watch_time) as avg_watch_time,
                AVG(completion_rate) as avg_completion_rate
            FROM video_views
            WHERE video_id = ?
        ''', (video_id,))

        view_stats = cursor.fetchone()

        # Estatísticas de engajamento
        cursor.execute('''
            SELECT
                SUM(CASE WHEN like_type = 'like' THEN 1 ELSE 0 END) as likes,
                SUM(CASE WHEN like_type = 'dislike' THEN 1 ELSE 0 END) as dislikes
            FROM video_likes
            WHERE video_id = ?
        ''', (video_id,))

        engagement_stats = cursor.fetchone()

        conn.close()

        return {
            'video_id': video_id,
            'total_views': view_stats[0] or 0,
            'avg_watch_time': view_stats[1] or 0,
            'avg_completion_rate': view_stats[2] or 0,
            'likes': engagement_stats[0] or 0,
            'dislikes': engagement_stats[1] or 0,
            'comments': video['comments_count'],
            'shares': video['shares_count']
        }

    # ========== MÉTODOS INTERNOS ==========

    def _save_video(self, video: Video):
        """Salva vídeo no banco"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO videos
            (id, author_id, author_username, title, description, video_url, thumbnail_url,
             duration, video_type, resolution, size_bytes, mime_type, timestamp, views_count,
             likes_count, dislikes_count, comments_count, shares_count, is_public, is_monetized,
             tags, category, language, quality_levels, chapters, subtitles_url, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            video.id, video.author_id, video.author_username, video.title, video.description,
            video.video_url, video.thumbnail_url, video.duration, video.video_type,
            video.resolution, video.size_bytes, video.mime_type, video.timestamp,
            video.views_count, video.likes_count, video.dislikes_count, video.comments_count,
            video.shares_count, int(video.is_public), int(video.is_monetized),
            json.dumps(video.tags), video.category, video.language,
            json.dumps(video.quality_levels), json.dumps(video.chapters),
            video.subtitles_url, json.dumps(video.metadata)
        ))

        conn.commit()
        conn.close()

    def _save_comment(self, comment: VideoComment):
        """Salva comentário no banco"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO video_comments
            (id, video_id, author_id, author_username, content, timestamp,
             parent_comment_id, likes_count, replies_count, is_pinned, is_creator_reply)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            comment.id, comment.video_id, comment.author_id, comment.author_username,
            comment.content, comment.timestamp, comment.parent_comment_id,
            comment.likes_count, comment.replies_count, int(comment.is_pinned),
            int(comment.is_creator_reply)
        ))

        conn.commit()
        conn.close()

    def _save_view(self, view: VideoView):
        """Salva visualização no banco"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO video_views
            (id, video_id, viewer_id, viewer_username, watch_time, completion_rate,
             timestamp, device_type, quality_watched)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            view.id, view.video_id, view.viewer_id, view.viewer_username,
            view.watch_time, view.completion_rate, view.timestamp,
            view.device_type, view.quality_watched
        ))

        conn.commit()
        conn.close()

    def _save_share(self, share: VideoShare):
        """Salva compartilhamento no banco"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO video_shares
            (id, video_id, sharer_id, sharer_username, platform, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (share.id, share.video_id, share.sharer_id, share.sharer_username,
              share.platform, share.timestamp))

        conn.commit()
        conn.close()

    def _save_playlist(self, playlist: VideoPlaylist):
        """Salva playlist no banco"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO playlists
            (id, creator_id, creator_username, title, description, is_public,
             video_ids, thumbnail_url, timestamp, views_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            playlist.id, playlist.creator_id, playlist.creator_username,
            playlist.title, playlist.description, int(playlist.is_public),
            json.dumps(playlist.video_ids), playlist.thumbnail_url,
            playlist.timestamp, playlist.views_count
        ))

        conn.commit()
        conn.close()

    def _row_to_video_dict(self, row) -> Dict:
        """Converte row do banco para dict do vídeo"""
        return {
            'id': row[0],
            'author_id': row[1],
            'author_username': row[2],
            'title': row[3],
            'description': row[4],
            'video_url': row[5],
            'thumbnail_url': row[6],
            'duration': row[7],
            'video_type': row[8],
            'resolution': row[9],
            'size_bytes': row[10],
            'mime_type': row[11],
            'timestamp': row[12],
            'views_count': row[13],
            'likes_count': row[14],
            'dislikes_count': row[15],
            'comments_count': row[16],
            'shares_count': row[17],
            'is_public': bool(row[18]),
            'is_monetized': bool(row[19]),
            'tags': json.loads(row[20]) if row[20] else [],
            'category': row[21],
            'language': row[22],
            'quality_levels': json.loads(row[23]) if row[23] else [],
            'chapters': json.loads(row[24]) if row[24] else [],
            'subtitles_url': row[25],
            'metadata': json.loads(row[26]) if row[26] else {}
        }

    def _row_to_comment_dict(self, row) -> Dict:
        """Converte row do banco para dict do comentário"""
        return {
            'id': row[0],
            'video_id': row[1],
            'author_id': row[2],
            'author_username': row[3],
            'content': row[4],
            'timestamp': row[5],
            'parent_comment_id': row[6],
            'likes_count': row[7],
            'replies_count': row[8],
            'is_pinned': bool(row[9]),
            'is_creator_reply': bool(row[10])
        }

    def _row_to_playlist_dict(self, row) -> Dict:
        """Converte row do banco para dict da playlist"""
        return {
            'id': row[0],
            'creator_id': row[1],
            'creator_username': row[2],
            'title': row[3],
            'description': row[4],
            'is_public': bool(row[5]),
            'video_ids': json.loads(row[6]) if row[6] else [],
            'thumbnail_url': row[7],
            'timestamp': row[8],
            'views_count': row[9]
        }

    def _get_user_like(self, video_id: str, user_id: str) -> Optional[Dict]:
        """Busca like do usuário no vídeo"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, like_type, timestamp
            FROM video_likes
            WHERE video_id = ? AND user_id = ?
        ''', (video_id, user_id))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0],
                'like_type': row[1],
                'timestamp': row[2]
            }
        return None

    def _get_comment_replies(self, comment_id: str, limit: int = 10) -> List[Dict]:
        """Obtém respostas de um comentário"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM video_comments
            WHERE parent_comment_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        ''', (comment_id, limit))

        replies = []
        for row in cursor.fetchall():
            replies.append(self._row_to_comment_dict(row))

        conn.close()
        return replies

    def _update_video_counters(self, video_id: str):
        """Atualiza contadores de likes/dislikes do vídeo"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                SUM(CASE WHEN like_type = 'like' THEN 1 ELSE 0 END) as likes,
                SUM(CASE WHEN like_type = 'dislike' THEN 1 ELSE 0 END) as dislikes
            FROM video_likes
            WHERE video_id = ?
        ''', (video_id,))

        result = cursor.fetchone()
        likes = result[0] or 0
        dislikes = result[1] or 0

        cursor.execute('''
            UPDATE videos
            SET likes_count = ?, dislikes_count = ?
            WHERE id = ?
        ''', (likes, dislikes, video_id))

        conn.commit()
        conn.close()

    def _increment_video_views(self, video_id: str):
        """Incrementa contador de visualizações"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE videos SET views_count = views_count + 1 WHERE id = ?',
            (video_id,)
        )

        conn.commit()
        conn.close()

    def _increment_video_comments(self, video_id: str):
        """Incrementa contador de comentários"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE videos SET comments_count = comments_count + 1 WHERE id = ?',
            (video_id,)
        )

        conn.commit()
        conn.close()

    def _increment_video_shares(self, video_id: str):
        """Incrementa contador de compartilhamentos"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE videos SET shares_count = shares_count + 1 WHERE id = ?',
            (video_id,)
        )

        conn.commit()
        conn.close()

    def _update_comment_creator_flag(self, comment_id: str, is_creator: bool):
        """Atualiza flag de comentário do criador"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE video_comments SET is_creator_reply = ? WHERE id = ?',
            (int(is_creator), comment_id)
        )

        conn.commit()
        conn.close()