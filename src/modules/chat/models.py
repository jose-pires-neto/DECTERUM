from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Usuário da rede"""
    user_id: str
    username: str
    public_key: str
    last_seen: float
    status: str = "online"
    avatar: str = ""


@dataclass
class Contact:
    """Contato do usuário"""
    contact_id: str
    username: str
    added_at: float
    status: str = "offline"


@dataclass
class Message:
    """Mensagem da rede"""
    id: str
    sender_id: str
    sender_username: str
    recipient_id: str
    content: str
    timestamp: float
    message_type: str = "chat"
    delivered: bool = False
    read: bool = False


@dataclass
class Peer:
    """Peer da rede (legado)"""
    node_id: str
    host: str
    port: int
    tunnel_url: str
    last_seen: float
    status: str = "online"