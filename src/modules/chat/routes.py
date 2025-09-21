from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from .service import ChatService
from .models import Message
import time
import uuid

router = APIRouter(prefix="/api/chat", tags=["chat"])


def setup_chat_routes(chat_service: ChatService, node) -> APIRouter:
    """Configura as rotas do chat"""

    @router.get("/messages/{contact_id}")
    async def get_messages(contact_id: str) -> List[Dict]:
        """Obtém mensagens com um contato"""
        try:
            messages = chat_service.get_conversation(node.current_user_id, contact_id)
            return {"messages": messages}
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
    async def get_contacts() -> Dict:
        """Obtém lista de contatos"""
        try:
            contacts = chat_service.get_user_contacts(node.current_user_id)
            return {"contacts": contacts}
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

    @router.delete("/contacts/{contact_id}")
    async def remove_contact(contact_id: str) -> Dict:
        """Remove um contato"""
        try:
            chat_service.remove_contact(node.current_user_id, contact_id)
            return {"success": True, "message": "Contato removido com sucesso"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/messages/{contact_id}/mark-read")
    async def mark_messages_read(contact_id: str) -> Dict:
        """Marca todas as mensagens de um contato como lidas"""
        try:
            chat_service.mark_messages_as_read(node.current_user_id, contact_id)
            return {"success": True, "message": "Mensagens marcadas como lidas"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router