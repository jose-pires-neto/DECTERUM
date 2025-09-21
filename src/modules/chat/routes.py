from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from .service import ChatService
from .models import Message
import time
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])


def setup_chat_routes(chat_service: ChatService, node) -> APIRouter:
    """Configura as rotas do chat"""

    @router.get("/messages/{contact_id}")
    async def get_messages(contact_id: str) -> List[Dict]:
        """Obtém mensagens com um contato"""
        try:
            messages = chat_service.get_conversation(node.current_user_id, contact_id)
            return messages
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/send")
    async def send_message(data: Dict[str, Any]) -> Dict:
        """Envia uma mensagem"""
        try:
            recipient_id = data.get('recipient_id')
            content = data.get('content')

            if not recipient_id or not content:
                raise HTTPException(status_code=400, detail="recipient_id e content são obrigatórios")

            user = node.db.get_user(node.current_user_id)
            if not user:
                raise HTTPException(status_code=404, detail="Usuário não encontrado")

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
                    print(f"Erro enviando mensagem P2P: {e}")

            return {
                "success": True,
                "message_id": message.id,
                "timestamp": message.timestamp
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/contacts")
    async def get_contacts() -> List[Dict]:
        """Obtém lista de contatos"""
        try:
            contacts = chat_service.get_user_contacts(node.current_user_id)
            return contacts
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/contacts")
    async def add_contact(data: Dict[str, Any]) -> Dict:
        """Adiciona um novo contato"""
        try:
            contact_id = data.get('contact_id')
            username = data.get('username')

            if not contact_id or not username:
                raise HTTPException(status_code=400, detail="contact_id e username são obrigatórios")

            chat_service.add_contact(node.current_user_id, contact_id, username)

            return {"success": True, "message": "Contato adicionado com sucesso"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router