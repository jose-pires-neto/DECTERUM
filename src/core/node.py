import uuid
import logging
from typing import Optional
from .database import P2PDatabase
from ..network.cloudflare import CloudflareManager

logger = logging.getLogger(__name__)


class P2PNode:
    """Nó P2P central do sistema"""

    def __init__(self, port: int = 8000):
        self.port = port
        self.host = "localhost"
        self.is_running = True

        # Database
        self.db = P2PDatabase()

        # Cloudflare Manager
        self.cloudflare = CloudflareManager(port)

        # Configurar usuário atual
        self.current_user_id = self.db.get_setting("current_user_id")
        if not self.current_user_id:
            username = f"user_{uuid.uuid4().hex[:8]}"
            self.current_user_id = self.db.create_user(username)
            self.db.set_setting("current_user_id", self.current_user_id)

        self.node_id = self.current_user_id

        # Sistema de descoberta de rede
        self.network_manager = None
        self.setup_network_discovery()

        # DHT (mantém compatibilidade)
        self.dht = None
        self.setup_dht()

    def setup_network_discovery(self):
        """Configura descoberta de rede"""
        try:
            from ..network.discovery import NetworkManager
            user = self.db.get_user(self.current_user_id)
            self.network_manager = NetworkManager(
                self.node_id,
                user['username'] if user else 'Unknown',
                self.port
            )
            logger.info("✅ Network discovery configurado")
        except ImportError:
            logger.warning("⚠️ network_discovery.py não encontrado - usando descoberta básica")

    def setup_dht(self):
        """Configura DHT"""
        try:
            from ..network.dht import DecterumDHT, DHTNode
            dht_node = DHTNode(self.node_id, self.host, self.port)
            self.dht = DecterumDHT(dht_node)
            logger.info("✅ DHT configurado")
        except ImportError:
            logger.warning("⚠️ dht_manager.py não encontrado - DHT desabilitado")
        except Exception as e:
            logger.warning(f"⚠️ Erro configurando DHT: {e} - DHT desabilitado")


    def get_current_user(self) -> Optional[dict]:
        """Obtém usuário atual"""
        return self.db.get_user(self.current_user_id)

    def get_discovered_peers(self) -> list:
        """Obtém peers descobertos"""
        return self.db.get_discovered_peers()

    async def send_p2p_message(self, message):
        """Envia mensagem P2P (placeholder)"""
        # TODO: Implementar envio P2P real
        logger.info(f"Enviando mensagem P2P: {message.id}")
        pass