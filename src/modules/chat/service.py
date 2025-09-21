import uuid
import time
from typing import Dict, List, Optional
from .models import User, Contact, Message
from ...core.database import P2PDatabase


class ChatService:
    """Serviço responsável pela lógica de negócio do chat"""

    def __init__(self, database: P2PDatabase):
        self.db = database

    def create_message(self, sender_id: str, sender_username: str,
                      recipient_id: str, content: str) -> Message:
        """Cria uma nova mensagem"""
        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_username=sender_username,
            recipient_id=recipient_id,
            content=content,
            timestamp=time.time(),
            message_type="chat",
            delivered=False,
            read=False
        )
        self.db.save_message(message)
        return message

    def get_conversation(self, user_id: str, contact_id: str = None, limit: int = 100) -> List[Dict]:
        """Obtém conversas entre dois usuários ou todas as mensagens"""
        return self.db.get_messages(user_id, contact_id, limit)

    def get_user_contacts(self, user_id: str) -> List[Dict]:
        """Obtém lista de contatos do usuário"""
        return self.db.get_contacts(user_id)

    def add_contact(self, owner_id: str, contact_id: str, username: str):
        """Adiciona um novo contato"""
        self.db.add_contact(owner_id, contact_id, username)

    def mark_message_as_read(self, message_id: str):
        """Marca mensagem como lida"""
        # TODO: Implementar atualização de status de leitura
        pass

    def mark_message_as_delivered(self, message_id: str):
        """Marca mensagem como entregue"""
        # TODO: Implementar atualização de status de entrega
        pass