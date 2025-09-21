from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging

from .service import FeedService
from .models import BADGE_TYPES, POST_TYPES

logger = logging.getLogger(__name__)


def setup_feed_routes(feed_service: FeedService, node) -> APIRouter:
    """Configura rotas do feed social"""
    router = APIRouter(prefix="/api/feed", tags=["feed"])

    # ========== POSTS ==========

    @router.post("/posts")
    async def create_post(data: Dict[str, Any]):
        """Cria um novo post"""
        try:
            content = data.get('content')
            post_type = data.get('post_type', 'text')
            parent_post_id = data.get('parent_post_id')
            tags = data.get('tags', [])

            if not content or not content.strip():
                return JSONResponse(
                    status_code=400,
                    content={"error": "Conteúdo do post é obrigatório"}
                )

            if post_type not in POST_TYPES:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Tipo de post inválido: {post_type}"}
                )

            user = node.get_current_user()
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Usuário não autenticado"}
                )

            post = feed_service.create_post(
                author_id=node.current_user_id,
                author_username=user['username'],
                content=content.strip(),
                post_type=post_type,
                parent_post_id=parent_post_id,
                tags=tags
            )

            return {
                "success": True,
                "post_id": post.id,
                "message": "Post criado com sucesso",
                "post": {
                    "id": post.id,
                    "content": post.content,
                    "timestamp": post.timestamp,
                    "post_type": post.post_type,
                    "parent_post_id": post.parent_post_id,
                    "thread_level": post.thread_level
                }
            }

        except Exception as e:
            logger.error(f"Erro criando post: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @router.get("/posts")
    async def get_feed(
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        sort_by: str = Query("timestamp", regex="^(timestamp|weight|engagement)$")
    ):
        """Obtém posts do feed"""
        try:
            user = node.get_current_user()
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Usuário não autenticado"}
                )

            posts = feed_service.get_feed(
                user_id=node.current_user_id,
                limit=limit,
                offset=offset,
                sort_by=sort_by
            )

            return {
                "success": True,
                "posts": posts,
                "total": len(posts),
                "offset": offset,
                "sort_by": sort_by
            }

        except Exception as e:
            logger.error(f"Erro obtendo feed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @router.get("/posts/{post_id}")
    async def get_post(post_id: str):
        """Obtém um post específico"""
        try:
            user = node.get_current_user()
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Usuário não autenticado"}
                )

            post = feed_service.get_post_by_id(post_id)
            if not post:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Post não encontrado"}
                )

            # Incluir voto do usuário atual
            user_vote = feed_service.get_user_vote(post_id, node.current_user_id)
            post['user_vote'] = user_vote

            return {
                "success": True,
                "post": post
            }

        except Exception as e:
            logger.error(f"Erro obtendo post {post_id}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @router.get("/posts/{post_id}/comments")
    async def get_post_comments(
        post_id: str,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0)
    ):
        """Obtém comentários de um post"""
        try:
            user = node.get_current_user()
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Usuário não autenticado"}
                )

            comments = feed_service.get_post_comments(post_id, limit, offset)

            # Adicionar voto do usuário para cada comentário
            for comment in comments:
                comment['user_vote'] = feed_service.get_user_vote(
                    comment['id'], node.current_user_id
                )

            return {
                "success": True,
                "comments": comments,
                "total": len(comments),
                "offset": offset
            }

        except Exception as e:
            logger.error(f"Erro obtendo comentários do post {post_id}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    # ========== VOTAÇÃO ==========

    @router.post("/posts/{post_id}/vote")
    async def vote_post(post_id: str, data: Dict[str, Any]):
        """Vota em um post"""
        try:
            vote_type = data.get('vote_type')

            if vote_type not in ["up", "down"]:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Tipo de voto deve ser 'up' ou 'down'"}
                )

            user = node.get_current_user()
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Usuário não autenticado"}
                )

            success = feed_service.vote_post(
                post_id=post_id,
                voter_id=node.current_user_id,
                voter_username=user['username'],
                vote_type=vote_type
            )

            if not success:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Erro ao processar voto"}
                )

            # Retornar estado atualizado do post
            post = feed_service.get_post_by_id(post_id)
            user_vote = feed_service.get_user_vote(post_id, node.current_user_id)

            return {
                "success": True,
                "message": "Voto processado com sucesso",
                "post": {
                    "upvotes": post['upvotes'],
                    "downvotes": post['downvotes'],
                    "net_votes": post['net_votes'],
                    "weight_score": post['weight_score']
                },
                "user_vote": user_vote
            }

        except Exception as e:
            logger.error(f"Erro votando no post {post_id}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    # ========== SELOS COMUNITÁRIOS ==========

    @router.post("/posts/{post_id}/badges")
    async def award_badge(post_id: str, data: Dict[str, Any]):
        """Atribui selo comunitário a um post"""
        try:
            badge_type = data.get('badge_type')

            if badge_type not in BADGE_TYPES:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": f"Tipo de selo inválido: {badge_type}",
                        "available_badges": list(BADGE_TYPES.keys())
                    }
                )

            user = node.get_current_user()
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Usuário não autenticado"}
                )

            success = feed_service.award_badge(
                post_id=post_id,
                badge_type=badge_type,
                awarded_by=node.current_user_id,
                awarded_by_username=user['username']
            )

            if not success:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Você já atribuiu este selo a este post"}
                )

            # Retornar selos atualizados
            badges = feed_service.get_post_badges(post_id)

            return {
                "success": True,
                "message": f"Selo '{BADGE_TYPES[badge_type]}' atribuído com sucesso",
                "badges": badges
            }

        except Exception as e:
            logger.error(f"Erro atribuindo selo ao post {post_id}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @router.get("/posts/{post_id}/badges")
    async def get_post_badges(post_id: str):
        """Obtém selos de um post"""
        try:
            badges = feed_service.get_post_badges(post_id)

            # Formatar com nomes legíveis
            formatted_badges = {}
            for badge_type, count in badges.items():
                formatted_badges[badge_type] = {
                    "count": count,
                    "name": BADGE_TYPES.get(badge_type, badge_type),
                    "type": badge_type
                }

            return {
                "success": True,
                "badges": formatted_badges
            }

        except Exception as e:
            logger.error(f"Erro obtendo selos do post {post_id}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    # ========== SUB-THREADS ==========

    @router.post("/posts/{post_id}/threads")
    async def create_sub_thread(post_id: str, data: Dict[str, Any]):
        """Cria uma sub-thread para um post"""
        try:
            title = data.get('title')
            description = data.get('description', '')
            parent_thread_id = data.get('parent_thread_id')

            if not title or not title.strip():
                return JSONResponse(
                    status_code=400,
                    content={"error": "Título da sub-thread é obrigatório"}
                )

            user = node.get_current_user()
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Usuário não autenticado"}
                )

            sub_thread = feed_service.create_sub_thread(
                root_post_id=post_id,
                title=title.strip(),
                description=description.strip(),
                created_by=node.current_user_id,
                created_by_username=user['username'],
                parent_thread_id=parent_thread_id
            )

            return {
                "success": True,
                "message": "Sub-thread criada com sucesso",
                "thread": {
                    "id": sub_thread.id,
                    "title": sub_thread.title,
                    "description": sub_thread.description,
                    "timestamp": sub_thread.timestamp
                }
            }

        except Exception as e:
            logger.error(f"Erro criando sub-thread para post {post_id}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @router.get("/posts/{post_id}/threads")
    async def get_post_threads(post_id: str):
        """Obtém sub-threads de um post"""
        try:
            threads = feed_service.get_post_threads(post_id)

            return {
                "success": True,
                "threads": threads,
                "total": len(threads)
            }

        except Exception as e:
            logger.error(f"Erro obtendo sub-threads do post {post_id}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    # ========== REPUTAÇÃO ==========

    @router.get("/users/{user_id}/reputation")
    async def get_user_reputation(user_id: str):
        """Obtém reputação de um usuário"""
        try:
            reputation = feed_service.get_user_reputation(user_id)

            if not reputation:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Reputação não encontrada"}
                )

            return {
                "success": True,
                "reputation": {
                    "user_id": reputation.user_id,
                    "username": reputation.username,
                    "total_posts": reputation.total_posts,
                    "total_votes_received": reputation.total_votes_received,
                    "total_votes_given": reputation.total_votes_given,
                    "positive_votes_received": reputation.positive_votes_received,
                    "badges_received": reputation.badges_received,
                    "engagement_score": reputation.engagement_score,
                    "vote_weight": reputation.vote_weight,
                    "reputation_level": reputation.reputation_level,
                    "vote_accuracy": reputation.vote_accuracy
                }
            }

        except Exception as e:
            logger.error(f"Erro obtendo reputação do usuário {user_id}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @router.get("/me/reputation")
    async def get_my_reputation():
        """Obtém reputação do usuário atual"""
        try:
            user = node.get_current_user()
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Usuário não autenticado"}
                )

            return await get_user_reputation(node.current_user_id)

        except Exception as e:
            logger.error(f"Erro obtendo minha reputação: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    # ========== INFORMAÇÕES GERAIS ==========

    @router.get("/badge-types")
    async def get_badge_types():
        """Lista tipos de selos disponíveis"""
        return {
            "success": True,
            "badge_types": BADGE_TYPES
        }

    @router.get("/post-types")
    async def get_post_types():
        """Lista tipos de posts disponíveis"""
        return {
            "success": True,
            "post_types": POST_TYPES
        }

    @router.get("/stats")
    async def get_feed_stats():
        """Estatísticas gerais do feed"""
        try:
            # TODO: Implementar estatísticas gerais
            # Por enquanto, retornar dados básicos

            return {
                "success": True,
                "stats": {
                    "total_posts": 0,
                    "total_votes": 0,
                    "total_badges": 0,
                    "active_threads": 0,
                    "message": "Estatísticas serão implementadas em breve"
                }
            }

        except Exception as e:
            logger.error(f"Erro obtendo estatísticas: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    return router