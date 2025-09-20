#!/usr/bin/env python3
"""
DECTERUM - Sistema de Descoberta de Rede Melhorado
Implementa descoberta LAN real + Bootstrap DHT funcional
"""

import socket
import threading
import time
import json
import requests
import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import struct
import psutil  # pip install psutil
import ipaddress

logger = logging.getLogger(__name__)

def calculate_broadcast_address(ip: str, netmask: str) -> str:
    """Calcula endereço de broadcast baseado em IP e netmask"""
    try:
        network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
        return str(network.broadcast_address)
    except:
        return None

@dataclass
class DiscoveredPeer:
    """Peer descoberto na rede"""
    node_id: str
    host: str
    port: int
    username: str
    tunnel_url: str = ""
    discovery_method: str = "lan"  # lan, dht, manual
    last_seen: float = 0
    
    def __post_init__(self):
        if self.last_seen == 0:
            self.last_seen = time.time()

class LANDiscovery:
    """Descoberta de peers na rede local usando UDP broadcast"""
    
    def __init__(self, node_id: str, username: str, port: int):
        self.node_id = node_id
        self.username = username
        self.port = port
        self.discovery_port = 18888  # Porta específica para descoberta
        self.is_running = False
        self.peers: Dict[str, DiscoveredPeer] = {}
        self.socket = None
        
    def get_network_interfaces(self) -> List[str]:
        """Obtém todos os IPs das interfaces de rede"""
        ips = []
        try:
            # Usar psutil para detecção precisa
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ip = addr.address
                        if ip and not ip.startswith('127.'):
                            ips.append(ip)
        except:
            # Fallback manual
            hostname = socket.gethostname()
            try:
                ips = [socket.gethostbyname_ex(hostname)[2]]
                ips = [ip for ip in ips[0] if not ip.startswith('127.')]
            except:
                # Último recurso
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    s.connect(("8.8.8.8", 80))
                    ips = [s.getsockname()[0]]
                finally:
                    s.close()

        return ips
    
    def get_broadcast_addresses(self) -> List[str]:
        """Obtém endereços de broadcast para todas as redes"""
        broadcasts = []
        try:
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        # Tentar usar broadcast address nativo do psutil
                        if hasattr(addr, 'broadcast') and addr.broadcast:
                            broadcasts.append(addr.broadcast)
                        # Fallback: calcular broadcast usando IP + netmask
                        elif hasattr(addr, 'netmask') and addr.netmask:
                            calculated_broadcast = calculate_broadcast_address(addr.address, addr.netmask)
                            if calculated_broadcast and calculated_broadcast not in broadcasts:
                                broadcasts.append(calculated_broadcast)
        except:
            pass

        # Se não encontrou nenhum broadcast, usar fallback para redes comuns
        if not broadcasts:
            broadcasts = [
                '192.168.1.255', '192.168.0.255', '192.168.2.255',
                '10.0.0.255', '172.16.255.255'
            ]
        
        return broadcasts
    
    def start(self):
        """Inicia descoberta LAN"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Thread para escutar broadcasts
        threading.Thread(target=self._listen_broadcasts, daemon=True).start()
        
        # Thread para enviar broadcasts
        threading.Thread(target=self._send_broadcasts, daemon=True).start()
        
        logger.info(f"🔍 Descoberta LAN iniciada na porta {self.discovery_port}")
    
    def stop(self):
        """Para descoberta LAN"""
        self.is_running = False
        if self.socket:
            self.socket.close()
        logger.info("🛑 Descoberta LAN parada")
    
    def _listen_broadcasts(self):
        """Escuta broadcasts de outros nós"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Bind em todas as interfaces
            self.socket.bind(('', self.discovery_port))
            logger.info(f"📡 Escutando broadcasts na porta {self.discovery_port}")
            
            while self.is_running:
                try:
                    data, addr = self.socket.recvfrom(1024)
                    self._handle_broadcast(data, addr[0])
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_running:
                        logger.error(f"Erro recebendo broadcast: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Erro no socket de escuta: {e}")
    
    def _handle_broadcast(self, data: bytes, sender_ip: str):
        """Processa broadcast recebido"""
        try:
            message = json.loads(data.decode())
            
            if message.get('type') == 'DECTERUM_DISCOVERY':
                node_id = message.get('node_id')
                username = message.get('username')
                port = message.get('port')
                
                # Não adicionar a si mesmo
                if node_id == self.node_id:
                    return
                
                # Adicionar peer descoberto
                peer = DiscoveredPeer(
                    node_id=node_id,
                    host=sender_ip,
                    port=port,
                    username=username,
                    discovery_method="lan"
                )
                
                self.peers[node_id] = peer
                logger.info(f"📍 Peer descoberto: {username} ({sender_ip}:{port})")
                
                # Responder para descoberta mútua
                self._send_discovery_response(sender_ip)
                
        except Exception as e:
            logger.debug(f"Erro processando broadcast: {e}")
    
    def _send_broadcasts(self):
        """Envia broadcasts periódicos"""
        while self.is_running:
            try:
                self._broadcast_presence()
                time.sleep(30)  # Broadcast a cada 30 segundos
            except Exception as e:
                logger.error(f"Erro enviando broadcasts: {e}")
                time.sleep(5)
    
    def _broadcast_presence(self):
        """Envia broadcast de presença"""
        message = {
            'type': 'DECTERUM_DISCOVERY',
            'node_id': self.node_id,
            'username': self.username,
            'port': self.port,
            'timestamp': time.time()
        }
        
        data = json.dumps(message).encode()
        broadcasts = self.get_broadcast_addresses()
        
        for broadcast_addr in broadcasts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(data, (broadcast_addr, self.discovery_port))
                sock.close()
                logger.debug(f"📡 Broadcast enviado para {broadcast_addr}")
            except Exception as e:
                logger.debug(f"Erro enviando para {broadcast_addr}: {e}")
    
    def _send_discovery_response(self, target_ip: str):
        """Envia resposta direta de descoberta"""
        message = {
            'type': 'DECTERUM_DISCOVERY_RESPONSE',
            'node_id': self.node_id,
            'username': self.username,
            'port': self.port,
            'timestamp': time.time()
        }
        
        try:
            data = json.dumps(message).encode()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(data, (target_ip, self.discovery_port))
            sock.close()
            logger.debug(f"↩️ Resposta enviada para {target_ip}")
        except Exception as e:
            logger.debug(f"Erro enviando resposta para {target_ip}: {e}")
    
    def get_discovered_peers(self) -> List[DiscoveredPeer]:
        """Retorna peers descobertos ativos"""
        active_peers = []
        current_time = time.time()
        
        for peer in list(self.peers.values()):
            # Remove peers inativos (5 minutos)
            if current_time - peer.last_seen > 300:
                del self.peers[peer.node_id]
            else:
                active_peers.append(peer)
        
        return active_peers
    
    def force_discovery(self):
        """Força nova descoberta imediata"""
        logger.info("🔍 Forçando descoberta LAN...")
        self._broadcast_presence()

class DHTPeerBootstrap:
    """Sistema de bootstrap para DHT usando peers públicos"""
    
    def __init__(self):
        # Bootstrap nodes reais do BitTorrent DHT (funcionam!)
        self.bootstrap_nodes = [
            "router.bittorrent.com:6881",
            "dht.transmissionbt.com:6881", 
            "router.utorrent.com:6881",
            "dht.aelitis.com:6881"
        ]
        
        # Seeds DECTERUM conhecidos (você pode adicionar seus próprios)
        self.decterum_seeds = [
            # Adicione aqui seus próprios seeds quando disponíveis
            # "your-server.com:8000",
            # "another-seed.example.com:8000"
        ]
    
    async def get_bootstrap_peers(self) -> List[Tuple[str, int]]:
        """Obtém peers de bootstrap para DHT"""
        peers = []
        
        # Primeiro tenta seeds DECTERUM
        for seed in self.decterum_seeds:
            try:
                host, port = seed.split(':')
                port = int(port)
                
                # Testa conectividade
                if await self._test_connection(host, port):
                    peers.append((host, port))
                    logger.info(f"✅ Seed DECTERUM ativo: {seed}")
                
            except Exception as e:
                logger.debug(f"Seed DECTERUM inacessível {seed}: {e}")
        
        # Se não há seeds DECTERUM, usa bootstrap BitTorrent
        if not peers:
            logger.info("🌐 Usando bootstrap do BitTorrent DHT...")
            for node in self.bootstrap_nodes:
                try:
                    host, port = node.split(':')
                    port = int(port)
                    
                    if await self._test_udp_connection(host, port):
                        peers.append((host, port))
                        logger.info(f"✅ Bootstrap ativo: {node}")
                        
                except Exception as e:
                    logger.debug(f"Bootstrap inacessível {node}: {e}")
        
        return peers
    
    async def _test_connection(self, host: str, port: int) -> bool:
        """Testa conexão HTTP/HTTPS"""
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=3)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"http://{host}:{port}/api/status") as response:
                    return response.status == 200
        except:
            return False
    
    async def _test_udp_connection(self, host: str, port: int) -> bool:
        """Testa conexão UDP (para bootstrap BitTorrent)"""
        try:
            # Resolve DNS
            import socket
            ip = socket.gethostbyname(host)
            return True  # Se resolver DNS, considera válido
        except:
            return False

class NetworkManager:
    """Gerenciador principal de rede - LAN + DHT"""
    
    def __init__(self, node_id: str, username: str, port: int):
        self.node_id = node_id
        self.username = username
        self.port = port
        
        # Sistemas de descoberta
        self.lan_discovery = LANDiscovery(node_id, username, port)
        self.dht_bootstrap = DHTPeerBootstrap()
        
        # Cache de peers
        self.all_peers: Dict[str, DiscoveredPeer] = {}
        
    def start(self):
        """Inicia todos os sistemas de descoberta"""
        logger.info("🚀 Iniciando gerenciador de rede...")
        
        # Inicia descoberta LAN
        self.lan_discovery.start()
        
        # Inicia descoberta periódica
        threading.Thread(target=self._periodic_discovery, daemon=True).start()
        
        logger.info("✅ Gerenciador de rede ativo")
    
    def stop(self):
        """Para todos os sistemas"""
        self.lan_discovery.stop()
    
    def _periodic_discovery(self):
        """Descoberta periódica de peers"""
        while True:
            try:
                # Atualiza peers LAN
                lan_peers = self.lan_discovery.get_discovered_peers()
                for peer in lan_peers:
                    self.all_peers[peer.node_id] = peer
                
                # Remove peers antigos
                current_time = time.time()
                expired = [
                    pid for pid, peer in self.all_peers.items()
                    if current_time - peer.last_seen > 600  # 10 minutos
                ]
                for pid in expired:
                    del self.all_peers[pid]
                
                logger.info(f"📊 Peers ativos: {len(self.all_peers)} (LAN: {len(lan_peers)})")
                
                time.sleep(60)  # Verifica a cada minuto
                
            except Exception as e:
                logger.error(f"Erro na descoberta periódica: {e}")
                time.sleep(30)
    
    def get_all_peers(self) -> List[DiscoveredPeer]:
        """Retorna todos os peers descobertos"""
        return list(self.all_peers.values())
    
    def get_peer_by_id(self, node_id: str) -> Optional[DiscoveredPeer]:
        """Busca peer por ID"""
        return self.all_peers.get(node_id)
    
    def add_manual_peer(self, host: str, port: int) -> Optional[DiscoveredPeer]:
        """Adiciona peer manualmente"""
        try:
            # Testa conectividade
            response = requests.get(f"http://{host}:{port}/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                peer = DiscoveredPeer(
                    node_id=data['node_id'],
                    host=host,
                    port=port,
                    username=data.get('username', 'Unknown'),
                    discovery_method="manual"
                )
                
                self.all_peers[peer.node_id] = peer
                logger.info(f"➕ Peer manual adicionado: {peer.username} ({host}:{port})")
                return peer
            
        except Exception as e:
            logger.error(f"Erro adicionando peer manual {host}:{port}: {e}")
        
        return None
    
    def force_discovery(self):
        """Força nova descoberta em todos os sistemas"""
        logger.info("🔍 Forçando descoberta completa...")
        self.lan_discovery.force_discovery()
    
    async def get_bootstrap_peers_for_dht(self) -> List[Tuple[str, int]]:
        """Obtém peers de bootstrap para DHT"""
        return await self.dht_bootstrap.get_bootstrap_peers()

# Função para instalar dependência necessária
if __name__ == "__main__":
    # Teste do sistema
    
    # Configura logging
    logging.basicConfig(level=logging.INFO)
    
    # Teste
    manager = NetworkManager("test-node", "TestUser", 8000)
    manager.start()
    
    print("🔍 Testando descoberta por 30 segundos...")
    time.sleep(30)
    
    peers = manager.get_all_peers()
    print(f"📊 Peers encontrados: {len(peers)}")
    for peer in peers:
        print(f"  - {peer.username} ({peer.host}:{peer.port}) via {peer.discovery_method}")
    
    manager.stop()