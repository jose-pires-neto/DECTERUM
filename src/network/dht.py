#!/usr/bin/env python3
"""
DECTERUM DHT - Implementação Kademlia para Descoberta Global
Baseado no protocolo BitTorrent/IPFS para descoberta P2P escalável
"""

import asyncio
import json
import time
import hashlib
import random
import struct
import socket
import threading
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class DHTNode:
    """Nó na rede DHT"""
    node_id: str
    host: str
    port: int
    last_seen: float = 0
    
    def __post_init__(self):
        if self.last_seen == 0:
            self.last_seen = time.time()
    
    @property
    def address(self) -> Tuple[str, int]:
        return (self.host, self.port)
    
    def distance_to(self, other_id: str) -> int:
        """Calcula distância XOR entre nós (Kademlia)"""
        self_int = int(self.node_id, 16)
        other_int = int(other_id, 16)
        return self_int ^ other_int
    
    def is_stale(self, timeout: int = 900) -> bool:
        """Verifica se nó está inativo (15 min padrão)"""
        return time.time() - self.last_seen > timeout

@dataclass 
class DHTValue:
    """Valor armazenado no DHT"""
    key: str
    value: dict
    stored_at: float
    expires_at: float
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

@dataclass
class UserPresence:
    """Presença de usuário na rede"""
    user_id: str
    username: str
    endpoints: List[str]  # ["ip:port", "tunnel_url"]
    public_key: str
    last_seen: float
    reputation_score: float = 0.0
    
    def to_dht_value(self) -> dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'endpoints': self.endpoints,
            'public_key': self.public_key,
            'last_seen': self.last_seen,
            'reputation_score': self.reputation_score
        }
    
    @classmethod
    def from_dht_value(cls, data: dict):
        return cls(**data)

class KBucket:
    """K-bucket para tabela de roteamento Kademlia"""
    
    def __init__(self, k: int = 20):
        self.k = k  # Máximo de nós por bucket
        self.nodes: List[DHTNode] = []
        self.last_updated = time.time()
    
    def add_node(self, node: DHTNode) -> bool:
        """Adiciona nó ao bucket"""
        # Remove se já existe
        self.nodes = [n for n in self.nodes if n.node_id != node.node_id]
        
        if len(self.nodes) < self.k:
            self.nodes.append(node)
            self.last_updated = time.time()
            return True
        else:
            # Bucket cheio - verifica se algum nó está stale
            stale_nodes = [n for n in self.nodes if n.is_stale()]
            if stale_nodes:
                # Remove nó mais antigo
                self.nodes.remove(stale_nodes[0])
                self.nodes.append(node)
                self.last_updated = time.time()
                return True
            return False
    
    def get_nodes(self) -> List[DHTNode]:
        """Retorna nós ativos"""
        active_nodes = [n for n in self.nodes if not n.is_stale()]
        self.nodes = active_nodes  # Remove stale nodes
        return active_nodes
    
    def find_closest(self, target_id: str, count: int = None) -> List[DHTNode]:
        """Encontra nós mais próximos do target"""
        if count is None:
            count = self.k
            
        nodes = self.get_nodes()
        nodes.sort(key=lambda n: n.distance_to(target_id))
        return nodes[:count]

class RoutingTable:
    """Tabela de roteamento Kademlia"""
    
    def __init__(self, local_node_id: str, k: int = 20):
        self.local_node_id = local_node_id
        self.k = k
        self.buckets: List[KBucket] = [KBucket(k) for _ in range(160)]  # 160 bits
    
    def _get_bucket_index(self, node_id: str) -> int:
        """Calcula índice do bucket baseado na distância XOR"""
        if node_id == self.local_node_id:
            return 0
            
        distance = int(self.local_node_id, 16) ^ int(node_id, 16)
        if distance == 0:
            return 0
        return distance.bit_length() - 1
    
    def add_node(self, node: DHTNode) -> bool:
        """Adiciona nó à tabela de roteamento"""
        if node.node_id == self.local_node_id:
            return False
            
        bucket_index = self._get_bucket_index(node.node_id)
        return self.buckets[bucket_index].add_node(node)
    
    def find_closest_nodes(self, target_id: str, count: int = 20) -> List[DHTNode]:
        """Encontra nós mais próximos do target"""
        all_nodes = []
        
        # Coleta nós de todos os buckets
        for bucket in self.buckets:
            all_nodes.extend(bucket.get_nodes())
        
        # Ordena por distância XOR
        all_nodes.sort(key=lambda n: n.distance_to(target_id))
        return all_nodes[:count]
    
    def get_random_nodes(self, count: int = 20) -> List[DHTNode]:
        """Retorna nós aleatórios para bootstrap"""
        all_nodes = []
        for bucket in self.buckets:
            all_nodes.extend(bucket.get_nodes())
        
        random.shuffle(all_nodes)
        return all_nodes[:count]

class DHTProtocol:
    """Protocolo de comunicação DHT"""
    
    def __init__(self, dht_manager):
        self.dht_manager = dht_manager
        
    async def send_message(self, node: DHTNode, message: dict) -> Optional[dict]:
        """Envia mensagem para um nó"""
        try:
            # Simples HTTP request para compatibilidade com sistema atual
            import aiohttp
            
            url = f"http://{node.host}:{node.port}/dht"
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=message) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
                    
        except Exception as e:
            logger.debug(f"Failed to send DHT message to {node.address}: {e}")
            return None
    
    async def ping(self, node: DHTNode) -> bool:
        """Ping para verificar se nó está vivo"""
        message = {
            'type': 'PING',
            'sender': {
                'node_id': self.dht_manager.local_node.node_id,
                'host': self.dht_manager.local_node.host,
                'port': self.dht_manager.local_node.port
            }
        }
        
        response = await self.send_message(node, message)
        return response is not None and response.get('type') == 'PONG'
    
    async def find_node(self, node: DHTNode, target_id: str) -> List[DHTNode]:
        """FIND_NODE - busca nós próximos ao target"""
        message = {
            'type': 'FIND_NODE',
            'target': target_id,
            'sender': {
                'node_id': self.dht_manager.local_node.node_id,
                'host': self.dht_manager.local_node.host,
                'port': self.dht_manager.local_node.port
            }
        }
        
        response = await self.send_message(node, message)
        if response and response.get('type') == 'FOUND_NODES':
            nodes = []
            for node_data in response.get('nodes', []):
                try:
                    nodes.append(DHTNode(**node_data))
                except:
                    continue
            return nodes
        return []
    
    async def find_value(self, node: DHTNode, key: str) -> Tuple[Optional[dict], List[DHTNode]]:
        """FIND_VALUE - busca valor ou nós próximos"""
        message = {
            'type': 'FIND_VALUE',
            'key': key,
            'sender': {
                'node_id': self.dht_manager.local_node.node_id,
                'host': self.dht_manager.local_node.host,
                'port': self.dht_manager.local_node.port
            }
        }
        
        response = await self.send_message(node, message)
        if response:
            if response.get('type') == 'FOUND_VALUE':
                return response.get('value'), []
            elif response.get('type') == 'FOUND_NODES':
                nodes = []
                for node_data in response.get('nodes', []):
                    try:
                        nodes.append(DHTNode(**node_data))
                    except:
                        continue
                return None, nodes
        return None, []
    
    async def store(self, node: DHTNode, key: str, value: dict) -> bool:
        """STORE - armazena valor no nó"""
        message = {
            'type': 'STORE',
            'key': key,
            'value': value,
            'sender': {
                'node_id': self.dht_manager.local_node.node_id,
                'host': self.dht_manager.local_node.host,
                'port': self.dht_manager.local_node.port
            }
        }
        
        response = await self.send_message(node, message)
        return response is not None and response.get('type') == 'STORED'

class DecterumDHT:
    """DHT Manager principal para DECTERUM"""
    
    def __init__(self, local_node: DHTNode, bootstrap_nodes: List[str] = None):
        self.local_node = local_node
        self.routing_table = RoutingTable(local_node.node_id)
        self.storage: Dict[str, DHTValue] = {}
        self.protocol = DHTProtocol(self)
        self.is_running = False
        
        # Bootstrap nodes padrão
        self.bootstrap_nodes = bootstrap_nodes or [
            "dht1.decterum.network:8000",
            "dht2.decterum.network:8000", 
            "dht3.decterum.network:8000"
        ]
        
        # Configurações
        self.alpha = 3  # Paralelismo de busca
        self.k = 20     # Tamanho do bucket
        self.ttl = 3600  # TTL dos valores (1 hora)
        
        logger.info(f"DHT inicializado - Nó: {self.local_node.node_id[:8]}...")
    
    def generate_key(self, data: str) -> str:
        """Gera chave DHT (SHA-1 hex)"""
        return hashlib.sha1(data.encode()).hexdigest()
    
    async def start(self):
        """Inicia o DHT"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("🚀 Iniciando DHT...")
        
        # Bootstrap da rede
        await self.bootstrap()
        
        # Inicia tarefas de manutenção
        asyncio.create_task(self.maintenance_loop())
        
        logger.info("✅ DHT ativo!")
    
    async def stop(self):
        """Para o DHT"""
        self.is_running = False
        logger.info("🛑 DHT parado")
    
    async def bootstrap(self):
        """Bootstrap inicial da rede DHT"""
        logger.info("🔗 Fazendo bootstrap da rede DHT...")
        
        bootstrap_contacts = []
        
        # Converte bootstrap nodes para DHTNode
        for address in self.bootstrap_nodes:
            try:
                if ':' in address:
                    host, port = address.split(':')
                    port = int(port)
                else:
                    host, port = address, 8000
                
                # Gera ID temporário para bootstrap
                temp_id = self.generate_key(f"{host}:{port}")
                node = DHTNode(temp_id, host, port)
                bootstrap_contacts.append(node)
                
            except Exception as e:
                logger.warning(f"Bootstrap node inválido {address}: {e}")
        
        # Tenta conectar com bootstrap nodes
        connected_count = 0
        for node in bootstrap_contacts:
            if await self.protocol.ping(node):
                self.routing_table.add_node(node)
                connected_count += 1
                logger.info(f"✅ Conectado ao bootstrap: {node.host}:{node.port}")
        
        if connected_count == 0:
            logger.warning("⚠️ Nenhum bootstrap node disponível - modo standalone")
            return
        
        # Busca nós próximos ao nosso ID
        await self.lookup_nodes(self.local_node.node_id)
        
        logger.info(f"🌐 Bootstrap completo - {connected_count} conexões iniciais")
    
    async def lookup_nodes(self, target_id: str) -> List[DHTNode]:
        """Busca iterativa de nós (algoritmo Kademlia)"""
        # Nós mais próximos conhecidos
        closest_nodes = self.routing_table.find_closest_nodes(target_id, self.k)
        
        if not closest_nodes:
            return []
        
        queried = set()
        to_query = set(closest_nodes[:self.alpha])
        
        while to_query:
            # Query paralelo
            current_batch = list(to_query)
            to_query.clear()
            
            tasks = []
            for node in current_batch:
                if node.node_id not in queried:
                    tasks.append(self.protocol.find_node(node, target_id))
                    queried.add(node.node_id)
            
            if not tasks:
                break
            
            # Executa queries em paralelo
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Processa resultados
            for i, result in enumerate(results):
                if isinstance(result, list):
                    for new_node in result:
                        # Adiciona à tabela de roteamento
                        self.routing_table.add_node(new_node)
                        
                        # Adiciona aos nós mais próximos se for melhor
                        current_closest = [n for n in closest_nodes if not n.is_stale()]
                        current_closest.append(new_node)
                        current_closest.sort(key=lambda n: n.distance_to(target_id))
                        closest_nodes = current_closest[:self.k]
                        
                        # Adiciona à próxima batch se não foi consultado
                        if (new_node.node_id not in queried and 
                            len(to_query) < self.alpha):
                            to_query.add(new_node)
        
        return closest_nodes
    
    async def store_value(self, key: str, value: dict, ttl: int = None) -> bool:
        """Armazena valor na rede DHT"""
        if ttl is None:
            ttl = self.ttl
        
        # Encontra nós responsáveis pela chave
        closest_nodes = await self.lookup_nodes(key)
        
        if not closest_nodes:
            logger.warning(f"Nenhum nó encontrado para armazenar chave: {key}")
            return False
        
        # Armazena nos nós mais próximos
        store_tasks = []
        for node in closest_nodes[:self.k]:
            store_tasks.append(self.protocol.store(node, key, value))
        
        results = await asyncio.gather(*store_tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        
        # Também armazena localmente
        expires_at = time.time() + ttl
        self.storage[key] = DHTValue(key, value, time.time(), expires_at)
        
        logger.info(f"📦 Valor armazenado - Chave: {key[:8]}... em {success_count + 1} nós")
        return success_count > 0
    
    async def get_value(self, key: str) -> Optional[dict]:
        """Busca valor na rede DHT"""
        # Verifica storage local primeiro
        if key in self.storage and not self.storage[key].is_expired():
            logger.debug(f"🎯 Valor encontrado localmente: {key[:8]}...")
            return self.storage[key].value
        
        # Busca na rede
        closest_nodes = self.routing_table.find_closest_nodes(key, self.k)
        
        if not closest_nodes:
            return None
        
        # Query paralelo
        tasks = []
        for node in closest_nodes[:self.alpha]:
            tasks.append(self.protocol.find_value(node, key))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa resultados
        for result in results:
            if isinstance(result, tuple):
                value, nodes = result
                if value:
                    # Valor encontrado! Cache localmente
                    expires_at = time.time() + self.ttl
                    self.storage[key] = DHTValue(key, value, time.time(), expires_at)
                    logger.info(f"🎯 Valor encontrado na rede: {key[:8]}...")
                    return value
                
                # Adiciona novos nós descobertos
                for node in nodes:
                    self.routing_table.add_node(node)
        
        logger.debug(f"❌ Valor não encontrado: {key[:8]}...")
        return None
    
    async def announce_user_presence(self, user_presence: UserPresence) -> bool:
        """Anuncia presença do usuário na rede"""
        key = self.generate_key(f"user:{user_presence.user_id}")
        value = user_presence.to_dht_value()
        
        logger.info(f"📢 Anunciando presença: {user_presence.username} ({user_presence.user_id[:8]}...)")
        return await self.store_value(key, value, ttl=1800)  # 30 min TTL
    
    async def find_user(self, user_id: str) -> Optional[UserPresence]:
        """Busca usuário na rede DHT"""
        key = self.generate_key(f"user:{user_id}")
        value = await self.get_value(key)
        
        if value:
            try:
                return UserPresence.from_dht_value(value)
            except Exception as e:
                logger.error(f"Erro ao parsear presença do usuário: {e}")
        
        return None
    
    async def discover_users(self, limit: int = 100) -> List[UserPresence]:
        """Descobre usuários ativos na rede"""
        users = []
        
        # Busca em chaves aleatórias para descobrir usuários
        for _ in range(20):  # 20 tentativas
            random_key = self.generate_key(f"user:{random.randint(0, 2**160)}")
            closest_nodes = await self.lookup_nodes(random_key)
            
            # Verifica storage dos nós próximos
            for node in closest_nodes[:5]:
                # Aqui implementaríamos um método para listar chaves
                # Por simplicidade, pulamos por ora
                pass
        
        return users[:limit]
    
    async def maintenance_loop(self):
        """Loop de manutenção da rede"""
        while self.is_running:
            try:
                # Limpa valores expirados
                expired_keys = [k for k, v in self.storage.items() if v.is_expired()]
                for key in expired_keys:
                    del self.storage[key]
                
                # Refresh de buckets inativos
                for i, bucket in enumerate(self.routing_table.buckets):
                    if (time.time() - bucket.last_updated > 3600 and  # 1 hora
                        bucket.get_nodes()):
                        # Busca aleatória no range do bucket para refresh
                        random_id = f"{random.randint(0, 2**(i+1)):#040x}"[2:]
                        await self.lookup_nodes(random_id)
                
                # Re-anuncia presença se necessário
                # (isso seria feito pelo P2PNode)
                
                logger.debug("🔧 Manutenção DHT executada")
                
            except Exception as e:
                logger.error(f"Erro na manutenção DHT: {e}")
            
            # Aguarda 5 minutos
            await asyncio.sleep(300)
    
    def handle_dht_request(self, request: dict) -> dict:
        """Processa requisições DHT recebidas"""
        msg_type = request.get('type')
        sender_data = request.get('sender', {})
        
        # Adiciona sender à tabela de roteamento
        try:
            sender = DHTNode(**sender_data)
            self.routing_table.add_node(sender)
        except:
            pass
        
        if msg_type == 'PING':
            return {
                'type': 'PONG',
                'sender': {
                    'node_id': self.local_node.node_id,
                    'host': self.local_node.host,
                    'port': self.local_node.port
                }
            }
        
        elif msg_type == 'FIND_NODE':
            target = request.get('target')
            closest_nodes = self.routing_table.find_closest_nodes(target, self.k)
            
            return {
                'type': 'FOUND_NODES',
                'nodes': [asdict(node) for node in closest_nodes]
            }
        
        elif msg_type == 'FIND_VALUE':
            key = request.get('key')
            
            # Verifica se tem o valor
            if key in self.storage and not self.storage[key].is_expired():
                return {
                    'type': 'FOUND_VALUE',
                    'value': self.storage[key].value
                }
            
            # Retorna nós próximos
            closest_nodes = self.routing_table.find_closest_nodes(key, self.k)
            return {
                'type': 'FOUND_NODES', 
                'nodes': [asdict(node) for node in closest_nodes]
            }
        
        elif msg_type == 'STORE':
            key = request.get('key')
            value = request.get('value')
            
            if key and value:
                expires_at = time.time() + self.ttl
                self.storage[key] = DHTValue(key, value, time.time(), expires_at)
                
                return {
                    'type': 'STORED'
                }
        
        return {'type': 'ERROR', 'message': 'Unknown request type'}
    
    def get_network_stats(self) -> dict:
        """Estatísticas da rede DHT"""
        total_nodes = sum(len(bucket.get_nodes()) for bucket in self.routing_table.buckets)
        
        return {
            'local_node_id': self.local_node.node_id,
            'total_known_nodes': total_nodes,
            'stored_values': len(self.storage),
            'active_buckets': sum(1 for b in self.routing_table.buckets if b.get_nodes()),
            'is_running': self.is_running
        }