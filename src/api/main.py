from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import logging
import os

from ..core.node import P2PNode
from ..core.database import P2PDatabase
from ..modules.chat.service import ChatService
from ..modules.chat.routes import setup_chat_routes
from ..modules.feed.service import FeedService
from ..modules.feed.routes import setup_feed_routes

logger = logging.getLogger(__name__)


async def start_network_services_async(node):
    """Inicia serviços de rede de forma assíncrona"""
    # Configurar túnel Cloudflare
    tunnel_url = node.cloudflare.setup_tunnel()
    if tunnel_url:
        logger.info(f"🌐 Túnel público: {tunnel_url}")

    # Iniciar descoberta de rede
    if node.network_manager:
        try:
            node.network_manager.start()
            logger.info("🔍 Descoberta de rede iniciada")
        except Exception as e:
            logger.error(f"Erro iniciando descoberta: {e}")

    # Iniciar DHT de forma assíncrona
    if node.dht:
        try:
            await node.dht.start()
            logger.info("🕸️ DHT iniciado com sucesso")
        except Exception as e:
            logger.error(f"Erro iniciando DHT: {e}")


async def stop_network_services_async(node):
    """Para serviços de rede de forma assíncrona"""
    if node.cloudflare:
        node.cloudflare.stop_tunnel()

    if node.network_manager:
        try:
            node.network_manager.stop()
        except Exception as e:
            logger.error(f"Erro parando descoberta: {e}")

    if node.dht:
        try:
            await node.dht.stop()
            logger.info("🛑 DHT parado")
        except Exception as e:
            logger.error(f"Erro parando DHT: {e}")


def create_app(port: int = 8000) -> FastAPI:
    """Cria e configura a aplicação FastAPI"""

    app = FastAPI(title="DECTERUM P2P", description="Sistema P2P Descentralizado")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Inicializar componentes principais
    node = P2PNode(port)
    chat_service = ChatService(node.db)
    feed_service = FeedService(node.db)

    # Configurar rotas dos módulos
    chat_router = setup_chat_routes(chat_service, node)
    feed_router = setup_feed_routes(feed_service, node)

    app.include_router(chat_router)
    app.include_router(feed_router)

    # Rotas estáticas
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def index():
        """Página principal"""
        return FileResponse("static/index.html")

    @app.get("/api/status")
    async def get_status():
        """Status do sistema"""
        user = node.get_current_user()
        peers = node.get_discovered_peers()

        return {
            "status": "online",
            "node_id": node.node_id,
            "user": user,
            "tunnel_url": node.cloudflare.tunnel_url,
            "discovered_peers": len(peers),
            "peers": peers
        }

    @app.get("/api/user")
    async def get_user():
        """Dados do usuário atual"""
        user = node.get_current_user()
        if not user:
            return JSONResponse(status_code=404, content={"error": "Usuário não encontrado"})
        return user

    @app.post("/api/user/update")
    async def update_user(data: Dict[str, Any]):
        """Atualiza dados do usuário"""
        try:
            username = data.get('username')
            if username:
                node.db.update_user(node.current_user_id, username=username)
                return {"success": True, "message": "Usuário atualizado"}
            return JSONResponse(status_code=400, content={"error": "Nome de usuário obrigatório"})
        except Exception as e:
            logger.error(f"Erro atualizando usuário: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.get("/api/peers")
    async def get_peers():
        """Lista peers descobertos"""
        return node.get_discovered_peers()

    @app.get("/api/contacts")
    async def get_contacts():
        """Lista contatos do usuário"""
        try:
            contacts = chat_service.get_user_contacts(node.current_user_id)
            return {"contacts": contacts}
        except Exception as e:
            logger.error(f"Erro obtendo contatos: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.post("/api/contacts")
    async def add_contact(data: Dict[str, Any]):
        """Adiciona um novo contato"""
        try:
            contact_id = data.get('contact_id')
            username = data.get('username')

            if not contact_id or not username:
                return JSONResponse(status_code=400, content={"error": "contact_id e username são obrigatórios"})

            chat_service.add_contact(node.current_user_id, contact_id, username)
            return {"success": True, "message": "Contato adicionado com sucesso"}

        except Exception as e:
            logger.error(f"Erro adicionando contato: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.get("/api/network-info")
    async def get_network_info():
        """Informações da rede"""
        try:
            peers = node.get_discovered_peers()
            user = node.get_current_user()
            tunnel_active = node.cloudflare.tunnel_url is not None

            return {
                "node_id": node.node_id,
                "username": user['username'] if user else 'Unknown',
                "network_status": "online",
                "peers_connected": len(peers),
                "local_port": node.port,
                "tunnel_active": tunnel_active,
                "tunnel_url": node.cloudflare.tunnel_url or "",
                "peers": peers,
                "dht_active": node.dht is not None,
                "network_discovery_active": node.network_manager is not None
            }
        except Exception as e:
            logger.error(f"Erro obtendo info da rede: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.post("/api/send")
    async def send_message(data: Dict[str, Any]):
        """Envia uma mensagem"""
        try:
            recipient_id = data.get('recipient_id')
            content = data.get('content')

            if not recipient_id or not content:
                return JSONResponse(status_code=400, content={"error": "recipient_id e content são obrigatórios"})

            user = node.get_current_user()
            if not user:
                return JSONResponse(status_code=404, content={"error": "Usuário não encontrado"})

            message = chat_service.create_message(
                sender_id=node.current_user_id,
                sender_username=user['username'],
                recipient_id=recipient_id,
                content=content
            )

            # Tentar entregar a mensagem via P2P se possível
            if hasattr(node, 'send_p2p_message'):
                try:
                    await node.send_p2p_message(message)
                except Exception as e:
                    logger.warning(f"Erro enviando mensagem P2P: {e}")

            return {
                "success": True,
                "message_id": message.id,
                "timestamp": message.timestamp
            }

        except Exception as e:
            logger.error(f"Erro enviando mensagem: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.post("/api/discover")
    async def discover_peers():
        """Força descoberta de peers"""
        try:
            if node.network_manager:
                # Trigger manual discovery
                peers = node.get_discovered_peers()
                return {
                    "success": True,
                    "message": "Descoberta iniciada",
                    "peers_found": len(peers),
                    "peers": peers
                }
            else:
                return JSONResponse(status_code=503, content={"error": "Descoberta de rede não disponível"})
        except Exception as e:
            logger.error(f"Erro na descoberta: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.get("/api/messages")
    async def get_messages(contact_id: str = None):
        """Obtém mensagens"""
        try:
            if contact_id:
                messages = chat_service.get_conversation(node.current_user_id, contact_id)
            else:
                messages = chat_service.get_conversation(node.current_user_id)

            return {"messages": messages}
        except Exception as e:
            logger.error(f"Erro obtendo mensagens: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.on_event("startup")
    async def startup_event():
        """Eventos de inicialização"""
        logger.info("🚀 Iniciando DECTERUM...")
        await start_network_services_async(node)

    @app.on_event("shutdown")
    async def shutdown_event():
        """Eventos de encerramento"""
        logger.info("🛑 Parando DECTERUM...")
        await stop_network_services_async(node)

    # Armazenar referências para uso em outras partes
    app.state.node = node
    app.state.chat_service = chat_service
    app.state.feed_service = feed_service

    return app