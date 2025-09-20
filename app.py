#!/usr/bin/env python3
"""
DECTERUM - Sistema P2P Descentralizado com DHT Global
Backend otimizado com descoberta global via Kademlia DHT
"""

import uvicorn
import uuid
import threading
import time
import requests
import json
import hashlib
import sqlite3
import os
import sys
import asyncio
import subprocess
import signal
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import base64
import logging

# Import do DHT
from dht_manager import DecterumDHT, DHTNode, UserPresence

# Configuração de logging otimizada
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    """Peer da rede"""
    node_id: str
    host: str
    port: int
    tunnel_url: str
    last_seen: float
    status: str = "online"

class CloudflareManager:
    """Gerenciador do Cloudflare Tunnel"""
    
    def __init__(self, port: int):
        self.port = port
        self.tunnel_url = None
        self.tunnel_process = None
        
    def check_cloudflared_installed(self):
        """Verifica se cloudflared está instalado em diferentes localizações"""
        
        # Possíveis caminhos do cloudflared
        possible_paths = [
            'cloudflared',  # PATH padrão
            'cloudflared.exe',  # Windows com extensão
            r'C:\Program Files\cloudflared\cloudflared.exe',  # Instalação padrão
            r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
            os.path.expanduser('~\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\\cloudflared.exe'),
            './cloudflared.exe',  # Local
            './cloudflared'  # Local Unix
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info(f"✅ Cloudflared encontrado em: {path}")
                    return path
            except:
                continue
        
        # Tentar atualizar PATH e verificar novamente (Windows)
        if os.name == 'nt':
            try:
                logger.info("🔄 Tentando atualizar PATH do Windows...")
                # Força atualização das variáveis de ambiente
                subprocess.run(['refreshenv'], shell=True, timeout=5)
                
                # Tenta novamente após refresh
                result = subprocess.run(['cloudflared', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info("✅ Cloudflared encontrado após atualização do PATH")
                    return 'cloudflared'
            except:
                pass
        
        logger.warning("⚠ Cloudflared não encontrado em nenhum local.")
        return None
            
    def setup_tunnel(self):
        """Configura e inicia o túnel Cloudflare"""
        cloudflared_path = self.check_cloudflared_installed()
        if not cloudflared_path:
            logger.warning("Cloudflared não instalado. Use 'python setup_cloudflare.py' para instalar.")
            return None
        
        try:
            # Comando para túnel temporário
            logger.info("🌐 Configurando túnel Cloudflare...")
            cmd = [
                cloudflared_path, 'tunnel', 
                '--url', f'http://localhost:{self.port}',
                '--no-autoupdate'
            ]
            
            # Iniciar processo do túnel
            self.tunnel_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Ler a saída do processo em uma thread separada para evitar deadlock
            tunnel_url_holder = {'url': None}
            def read_output(process, holder):
                try:
                    while True:
                        line = process.stderr.readline()
                        if not line:
                            break
                        logger.info(f"Log do Cloudflare: {line.strip()}")
                        if 'trycloudflare.com' in line:
                            parts = line.split()
                            for part in parts:
                                if 'trycloudflare.com' in part and part.startswith('https://'):
                                    holder['url'] = part.replace('|', '').strip()
                                    logger.info(f"✅ Túnel Cloudflare ativo: {holder['url']}")
                                    return
                except Exception as e:
                    logger.error(f"Erro lendo saída do Cloudflare: {e}")

            output_thread = threading.Thread(target=read_output, args=(self.tunnel_process, tunnel_url_holder), daemon=True)
            output_thread.start()
            output_thread.join(timeout=30)

            if tunnel_url_holder['url']:
                self.tunnel_url = tunnel_url_holder['url']
                return self.tunnel_url
            
            logger.warning("⚠️ Não foi possível configurar túnel Cloudflare automaticamente (Timeout)")
            self.stop_tunnel()
            return None
            
        except Exception as e:
            logger.error(f"Erro configurando túnel: {e}")
            return None
    
    def stop_tunnel(self):
        """Para o túnel"""
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
                logger.info("🛑 Sinal de término enviado ao túnel Cloudflare.")
                self.tunnel_process.wait(timeout=10)
                logger.info("✅ Túnel Cloudflare parado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao parar o túnel: {e}")
                try:
                    self.tunnel_process.kill()
                    logger.info("⚠️ Processo do túnel forçado a parar.")
                except Exception as e:
                    logger.error(f"Erro ao forçar a parada do túnel: {e}")
            finally:
                self.tunnel_process = None
                self.tunnel_url = None

class P2PDatabase:
    """Database otimizada para o sistema P2P"""
    
    def __init__(self, db_path: str = "decterum.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa todas as tabelas necessárias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                public_key TEXT,
                private_key TEXT,
                created_at REAL,
                last_seen REAL,
                status TEXT DEFAULT 'online',
                avatar TEXT DEFAULT ''
            )
        ''')
        
        # Tabela de contatos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id TEXT,
                contact_id TEXT,
                username TEXT,
                added_at REAL,
                status TEXT DEFAULT 'offline',
                FOREIGN KEY (owner_id) REFERENCES users (user_id)
            )
        ''')
        
        # Tabela de mensagens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender_id TEXT,
                sender_username TEXT,
                recipient_id TEXT,
                content TEXT,
                timestamp REAL,
                message_type TEXT DEFAULT 'chat',
                delivered INTEGER DEFAULT 0,
                read_status INTEGER DEFAULT 0
            )
        ''')
        
        # Tabela de peers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS peers (
                node_id TEXT PRIMARY KEY,
                host TEXT,
                port INTEGER,
                tunnel_url TEXT,
                last_seen REAL,
                status TEXT DEFAULT 'online'
            )
        ''')
        
        # NOVA: Tabela de peers DHT descobertos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dht_peers (
                node_id TEXT PRIMARY KEY,
                host TEXT,
                port INTEGER,
                tunnel_url TEXT,
                last_seen REAL,
                reputation_score REAL DEFAULT 0.0,
                discovery_method TEXT DEFAULT 'dht',
                status TEXT DEFAULT 'online'
            )
        ''')
        
        # Tabela de configurações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("📊 Database inicializada com suporte DHT")
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Busca usuário por ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'user_id': result[0],
                'username': result[1],
                'public_key': result[2],
                'private_key': result[3],
                'created_at': result[4],
                'last_seen': result[5],
                'status': result[6],
                'avatar': result[7]
            }
        return None
    
    def create_user(self, username: str) -> str:
        """Cria novo usuário"""
        user_id = str(uuid.uuid4())
        key = Fernet.generate_key()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, public_key, private_key, created_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, key.decode(), key.decode(), time.time(), time.time()))
        conn.commit()
        conn.close()
        
        return user_id
    
    def update_user(self, user_id: str, username: str = None, status: str = None):
        """Atualiza dados do usuário"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if username:
            cursor.execute('UPDATE users SET username = ?, last_seen = ? WHERE user_id = ?', 
                          (username, time.time(), user_id))
        
        if status:
            cursor.execute('UPDATE users SET status = ?, last_seen = ? WHERE user_id = ?', 
                          (status, time.time(), user_id))
        
        conn.commit()
        conn.close()
    
    def add_contact(self, owner_id: str, contact_id: str, username: str):
        """Adiciona contato"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO contacts (owner_id, contact_id, username, added_at)
            VALUES (?, ?, ?, ?)
        ''', (owner_id, contact_id, username, time.time()))
        conn.commit()
        conn.close()
    
    def get_contacts(self, owner_id: str) -> List[Dict]:
        """Lista contatos do usuário"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM contacts WHERE owner_id = ?', (owner_id,))
        results = cursor.fetchall()
        conn.close()
        
        contacts = []
        for row in results:
            contacts.append({
                'contact_id': row[2],
                'username': row[3],
                'added_at': row[4],
                'status': row[5]
            })
        return contacts
    
    def save_message(self, message: Message):
        """Salva mensagem"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO messages 
            (id, sender_id, sender_username, recipient_id, content, timestamp, message_type, delivered, read_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (message.id, message.sender_id, message.sender_username, message.recipient_id,
              message.content, message.timestamp, message.message_type, 
              int(message.delivered), int(message.read)))
        conn.commit()
        conn.close()
    
    def get_messages(self, user_id: str, contact_id: str = None, limit: int = 100) -> List[Dict]:
        """Busca mensagens (geral ou por contato)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if contact_id:
            cursor.execute('''
                SELECT * FROM messages 
                WHERE (sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?)
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, contact_id, contact_id, user_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM messages 
                WHERE sender_id = ? OR recipient_id = ?
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in results:
            messages.append({
                'id': row[0],
                'sender_id': row[1],
                'sender_username': row[2],
                'recipient_id': row[3],
                'content': row[4],
                'timestamp': row[5],
                'message_type': row[6],
                'delivered': bool(row[7]),
                'read': bool(row[8]),
                'formatted_time': datetime.fromtimestamp(row[5]).strftime("%H:%M")
            })
        return messages[::-1]  # Ordem cronológica
    
    def save_peer(self, peer: Peer):
        """Salva peer (método legado)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO peers (node_id, host, port, tunnel_url, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (peer.node_id, peer.host, peer.port, peer.tunnel_url, peer.last_seen, peer.status))
        conn.commit()
        conn.close()
    
    def save_dht_peer(self, node_id: str, host: str, port: int, tunnel_url: str = "", reputation: float = 0.0):
        """Salva peer descoberto via DHT"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO dht_peers 
            (node_id, host, port, tunnel_url, last_seen, reputation_score, discovery_method, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (node_id, host, port, tunnel_url, time.time(), reputation, 'dht', 'online'))
        conn.commit()
        conn.close()
    
    def get_peers(self) -> List[Dict]:
        """Lista peers online (legado + DHT)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # União de peers legados e DHT
        cursor.execute('''
            SELECT node_id, host, port, tunnel_url, last_seen, 'legacy' as discovery
            FROM peers WHERE status = "online"
            UNION
            SELECT node_id, host, port, tunnel_url, last_seen, discovery_method
            FROM dht_peers WHERE status = "online"
        ''')
        results = cursor.fetchall()
        conn.close()
        
        peers = []
        for row in results:
            peers.append({
                'node_id': row[0],
                'host': row[1],
                'port': row[2],
                'tunnel_url': row[3],
                'last_seen': row[4],
                'discovery_method': row[5]
            })
        return peers
    
    def get_dht_peers(self) -> List[Dict]:
        """Lista apenas peers descobertos via DHT"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM dht_peers WHERE status = "online"')
        results = cursor.fetchall()
        conn.close()
        
        peers = []
        for row in results:
            peers.append({
                'node_id': row[0],
                'host': row[1],
                'port': row[2],
                'tunnel_url': row[3],
                'last_seen': row[4],
                'reputation_score': row[5],
                'discovery_method': row[6],
                'status': row[7]
            })
        return peers
    
    def set_setting(self, key: str, value: str):
        """Salva configuração"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()
    
    def get_setting(self, key: str) -> Optional[str]:
        """Busca configuração"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

class P2PNode:
    """Nó P2P otimizado com DHT"""
    
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
            # Primeiro uso - criar usuário
            username = f"user_{uuid.uuid4().hex[:8]}"
            self.current_user_id = self.db.create_user(username)
            self.db.set_setting("current_user_id", self.current_user_id)
        
        self.node_id = self.current_user_id
        
        # NOVO: DHT Manager
        self.dht_enabled = os.getenv('DECTERUM_DHT_ENABLED', 'true').lower() == 'true'
        self.dht: Optional[DecterumDHT] = None
        self.dht_loop = None
        
        if self.dht_enabled:
            self.setup_dht()
        
        logger.info(f"🚀 Nó P2P iniciado: {self.node_id[:8]}... na porta {port}")
        if self.dht_enabled:
            logger.info("🌐 DHT habilitado - Descoberta global ativa")
    
    def setup_dht(self):
        """Configura DHT"""
        try:
            # Detecta IP local para DHT
            local_ip = self.get_local_ip()
            
            # Cria nó DHT local
            dht_node = DHTNode(
                node_id=self.node_id,
                host=local_ip,
                port=self.port
            )
            
            # Bootstrap nodes (você pode adicionar seus próprios)
            bootstrap_nodes = [
                "bootstrap1.decterum.network:8000",
                "bootstrap2.decterum.network:8000"
            ]
            
            # Inicializa DHT
            self.dht = DecterumDHT(dht_node, bootstrap_nodes)
            logger.info(f"🌐 DHT configurado - Nó: {self.node_id[:8]}... IP: {local_ip}")
            
        except Exception as e:
            logger.error(f"Erro configurando DHT: {e}")
            self.dht_enabled = False
    
    def get_local_ip(self) -> str:
        """Detecta IP local"""
        try:
            # Conecta a um endereço externo para descobrir IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    async def start_dht(self):
        """Inicia DHT de forma assíncrona"""
        if not self.dht_enabled or not self.dht:
            return
        
        try:
            await self.dht.start()
            
            # Anuncia presença inicial
            await self.announce_presence()
            
            # Inicia anúncios periódicos
            asyncio.create_task(self.periodic_presence_announcements())
            
            logger.info("✅ DHT iniciado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro iniciando DHT: {e}")
    
    async def announce_presence(self):
        """Anuncia presença na rede DHT"""
        if not self.dht:
            return
        
        try:
            user = self.db.get_user(self.current_user_id)
            if not user:
                return
            
            # Monta endpoints disponíveis
            endpoints = [f"{self.get_local_ip()}:{self.port}"]
            
            tunnel_url = self.db.get_setting("tunnel_url")
            if tunnel_url:
                endpoints.append(tunnel_url)
            
            # Cria presença
            presence = UserPresence(
                user_id=self.current_user_id,
                username=user['username'],
                endpoints=endpoints,
                public_key=user['public_key'],
                last_seen=time.time(),
                reputation_score=0.0  # TODO: Implementar sistema de reputação
            )
            
            # Anuncia na rede
            success = await self.dht.announce_user_presence(presence)
            if success:
                logger.info(f"📢 Presença anunciada: {user['username']}")
            
        except Exception as e:
            logger.error(f"Erro anunciando presença: {e}")
    
    async def periodic_presence_announcements(self):
        """Anuncia presença periodicamente"""
        while self.is_running and self.dht:
            try:
                await asyncio.sleep(1800)  # 30 minutos
                await self.announce_presence()
            except Exception as e:
                logger.error(f"Erro no anúncio periódico: {e}")
    
    async def find_user_via_dht(self, user_id: str) -> Optional[UserPresence]:
        """Busca usuário via DHT"""
        if not self.dht:
            return None
        
        try:
            presence = await self.dht.find_user(user_id)
            if presence:
                # Salva como peer DHT
                for endpoint in presence.endpoints:
                    if ':' in endpoint and not endpoint.startswith('http'):
                        # Endpoint local (ip:port)
                        host, port = endpoint.split(':')
                        self.db.save_dht_peer(
                            user_id, host, int(port), 
                            tunnel_url="", reputation=presence.reputation_score
                        )
                    else:
                        # Endpoint túnel
                        self.db.save_dht_peer(
                            user_id, "unknown", 0, 
                            tunnel_url=endpoint, reputation=presence.reputation_score
                        )
                
                logger.info(f"🎯 Usuário encontrado via DHT: {presence.username}")
            
            return presence
            
        except Exception as e:
            logger.error(f"Erro buscando usuário via DHT: {e}")
            return None
    
    def setup_cloudflare_tunnel(self):
        """Configura túnel Cloudflare"""
        tunnel_url = self.cloudflare.setup_tunnel()
        if tunnel_url:
            self.db.set_setting("tunnel_url", tunnel_url)
            return tunnel_url
        return None
    
    def discover_peers(self):
        """Descobre peers na rede local e remota"""
        # Descoberta local (mantém método original)
        local_ports = [8000, 8001, 8002, 8003, 8004]
        found_count = 0
        
        for port in local_ports:
            if port == self.port:
                continue
                
            try:
                response = requests.get(f"http://localhost:{port}/api/status", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    peer = Peer(
                        node_id=data['node_id'],
                        host="localhost",
                        port=port,
                        tunnel_url=data.get('tunnel_url', ''),
                        last_seen=time.time()
                    )
                    self.db.save_peer(peer)
                    found_count += 1
            except:
                continue
        
        if found_count > 0:
            logger.info(f"🔍 Descobertos {found_count} peers locais")
    
    async def send_message_to_user(self, recipient_id: str, message: Message) -> bool:
        """Envia mensagem (local + DHT)"""
        # 1. Tenta método atual (peers conhecidos)
        peers = self.db.get_peers()
        for peer in peers:
            if peer['node_id'] == recipient_id:
                if self.send_message_to_peer_data(peer, message):
                    return True
        
        # 2. NOVO: Busca via DHT se não encontrou localmente
        if self.dht:
            try:
                presence = await self.find_user_via_dht(recipient_id)
                if presence:
                    # Tenta conectar usando endpoints do DHT
                    for endpoint in presence.endpoints:
                        if await self.try_send_to_endpoint(endpoint, message):
                            return True
            except Exception as e:
                logger.error(f"Erro enviando via DHT: {e}")
        
        # 3. Enfileira para entrega futura
        logger.info(f"📤 Mensagem enfileirada para {recipient_id[:8]}...")
        return False
    
    def send_message_to_peer_data(self, peer_data: Dict, message: Message) -> bool:
        """Envia mensagem para peer específico"""
        try:
            # Tentar túnel primeiro, depois local
            urls = []
            if peer_data.get('tunnel_url'):
                urls.append(f"{peer_data['tunnel_url']}/api/receive")
            urls.append(f"http://{peer_data['host']}:{peer_data['port']}/api/receive")
            
            payload = asdict(message)
            
            for url in urls:
                try:
                    response = requests.post(url, json=payload, timeout=5)
                    if response.status_code == 200:
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False
    
    async def try_send_to_endpoint(self, endpoint: str, message: Message) -> bool:
        """Tenta enviar mensagem para endpoint específico"""
        try:
            if endpoint.startswith('http'):
                # Túnel URL
                url = f"{endpoint}/api/receive"
            else:
                # IP:Port local
                url = f"http://{endpoint}/api/receive"
            
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=asdict(message)) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.debug(f"Falha enviando para {endpoint}: {e}")
            return False
    
    def broadcast_message(self, message: Message) -> int:
        """Envia mensagem para todos os peers"""
        peers = self.db.get_peers()
        success_count = 0
        
        for peer in peers:
            if self.send_message_to_peer_data(peer, message):
                success_count += 1
        
        return success_count
    
    def background_tasks(self):
        """Tarefas em segundo plano otimizadas"""
        discovery_timer = 0
        
        while self.is_running:
            try:
                # Descoberta a cada 60 segundos
                if discovery_timer >= 60:
                    self.discover_peers()
                    discovery_timer = 0
                
                time.sleep(1)
                discovery_timer += 1
                
            except Exception as e:
                logger.error(f"Erro em background: {e}")
                time.sleep(5)
    
    def start_background_tasks(self):
        """Inicia tarefas em segundo plano"""
        thread = threading.Thread(target=self.background_tasks, daemon=True)
        thread.start()
        
        # Configurar túnel Cloudflare
        tunnel_url = self.setup_cloudflare_tunnel()
        if tunnel_url:
            logger.info(f"🌐 Túnel Cloudflare configurado: {tunnel_url}")
        else:
            logger.info("🏠 Usando apenas acesso local")
        
        # NOVO: Inicia DHT de forma assíncrona
        if self.dht_enabled and self.dht:
            self.dht_loop = asyncio.new_event_loop()
            
            def run_dht():
                asyncio.set_event_loop(self.dht_loop)
                self.dht_loop.run_until_complete(self.start_dht())
                self.dht_loop.run_forever()
            
            dht_thread = threading.Thread(target=run_dht, daemon=True)
            dht_thread.start()

# Inicialização do FastAPI
app = FastAPI(title="DECTERUM P2P with DHT", version="2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Variável global para o nó
node: Optional[P2PNode] = None

@app.on_event("startup")
async def startup():
    global node
    port = 8000
    
    # Obter porta da linha de comando
    if "--port" in sys.argv:
        try:
            port_index = sys.argv.index("--port") + 1
            port = int(sys.argv[port_index])
        except:
            pass
    
    node = P2PNode(port)
    node.start_background_tasks()
    logger.info(f"🚀 DECTERUM rodando na porta {port}")

@app.on_event("shutdown")
async def shutdown():
    global node
    if node:
        if node.cloudflare:
            node.cloudflare.stop_tunnel()
        if node.dht:
            await node.dht.stop()

# NOVO: Endpoint DHT
@app.post("/dht")
async def handle_dht_request(request: Request):
    """Processa requisições DHT"""
    if not node or not node.dht:
        raise HTTPException(status_code=503, detail="DHT não disponível")
    
    try:
        data = await request.json()
        response = node.dht.handle_dht_request(data)
        return response
    except Exception as e:
        logger.error(f"Erro processando requisição DHT: {e}")
        return {"type": "ERROR", "message": str(e)}

@app.get("/")
async def home():
    """Serve a interface principal"""
    return FileResponse("static/index.html")

# API Endpoints (mantém todos os originais)
@app.get("/api/status")
async def get_status():
    """Status do nó"""
    user = node.db.get_user(node.current_user_id)
    peers = node.db.get_peers()
    tunnel_url = node.db.get_setting("tunnel_url")
    
    return {
        "node_id": node.node_id,
        "username": user['username'] if user else "Unknown",
        "port": node.port,
        "tunnel_url": tunnel_url or "",
        "peer_count": len(peers),
        "dht_enabled": node.dht_enabled,
        "status": "online"
    }

@app.get("/api/user")
async def get_current_user():
    """Dados do usuário atual"""
    user = node.db.get_user(node.current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    tunnel_url = node.db.get_setting("tunnel_url")
    
    return {
        "user_id": user['user_id'],
        "username": user['username'],
        "avatar": user['avatar'],
        "status": user['status'],
        "tunnel_url": tunnel_url or "",
        "local_url": f"http://localhost:{node.port}"
    }

@app.post("/api/user")
async def update_user(data: dict):
    """Atualiza dados do usuário"""
    username = data.get('username', '').strip()
    status = data.get('status', '').strip()
    
    if username:
        node.db.update_user(node.current_user_id, username=username)
        # Re-anuncia presença no DHT com novo username
        if node.dht:
            asyncio.create_task(node.announce_presence())
    
    if status:
        node.db.update_user(node.current_user_id, status=status)
    
    return {"success": True}

@app.get("/api/contacts")
async def get_contacts():
    """Lista contatos"""
    contacts = node.db.get_contacts(node.current_user_id)
    return {"contacts": contacts}

@app.post("/api/contacts")
async def add_contact(data: dict):
    """Adiciona contato"""
    contact_id = data.get('contact_id', '').strip()
    username = data.get('username', '').strip()
    
    if not contact_id or not username:
        raise HTTPException(status_code=400, detail="ID e username obrigatórios")
    
    if contact_id == node.current_user_id:
        raise HTTPException(status_code=400, detail="Não é possível adicionar você mesmo")
    
    node.db.add_contact(node.current_user_id, contact_id, username)
    return {"success": True}

@app.get("/api/messages")
async def get_messages(contact_id: str = None, limit: int = 100):
    """Lista mensagens"""
    messages = node.db.get_messages(node.current_user_id, contact_id, limit)
    return {"messages": messages}

@app.post("/api/send")
async def send_message(data: dict):
    """Envia mensagem (com suporte DHT)"""
    content = data.get('content', '').strip()
    recipient_id = data.get('recipient_id', '').strip()
    
    if not content:
        raise HTTPException(status_code=400, detail="Conteúdo obrigatório")
    
    user = node.db.get_user(node.current_user_id)
    message = Message(
        id=str(uuid.uuid4()),
        sender_id=node.current_user_id,
        sender_username=user['username'],
        recipient_id=recipient_id,
        content=content,
        timestamp=time.time()
    )
    
    # Salvar localmente SEMPRE
    node.db.save_message(message)
    
    # Tentar enviar (local + DHT)
    success = False
    if recipient_id:
        # NOVO: Envio com suporte DHT
        if node.dht_loop and node.dht:
            # Executa busca DHT de forma assíncrona
            future = asyncio.run_coroutine_threadsafe(
                node.send_message_to_user(recipient_id, message), 
                node.dht_loop
            )
            try:
                success = future.result(timeout=10)
            except:
                success = False
        
        # Fallback para método tradicional
        if not success:
            peers = node.db.get_peers()
            for peer in peers:
                if peer['node_id'] == recipient_id:
                    success = node.send_message_to_peer_data(peer, message)
                    break
    else:
        # Broadcast
        success = node.broadcast_message(message) > 0
    
    return {
        "success": True,
        "message_id": message.id,
        "delivered_via_dht": success and node.dht_enabled,
        "sent_to": 1 if success else 0
    }

@app.post("/api/receive")
async def receive_message(message_data: dict):
    """Recebe mensagem de outro nó"""
    try:
        message = Message(**message_data)
        node.db.save_message(message)
        logger.info(f"📨 Mensagem recebida de {message.sender_username}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Erro ao receber mensagem: {e}")
        raise HTTPException(status_code=400, detail="Erro ao processar mensagem")

@app.get("/api/peers")
async def get_peers():
    """Lista peers conectados (local + DHT)"""
    peers = node.db.get_peers()
    return {"peers": peers}

@app.post("/api/discover")
async def discover_peers():
    """Força descoberta de peers (local + DHT)"""
    # Descoberta local
    node.discover_peers()
    
    # NOVO: Força refresh do DHT
    if node.dht and node.dht_loop:
        try:
            # Executa lookup aleatório para refresh
            random_id = str(uuid.uuid4())
            future = asyncio.run_coroutine_threadsafe(
                node.dht.lookup_nodes(node.dht.generate_key(random_id)),
                node.dht_loop
            )
            future.result(timeout=5)
        except:
            pass
    
    peers = node.db.get_peers()
    return {"peers_found": len(peers)}

@app.get("/api/network-info")
async def get_network_info():
    """Informações da rede (incluindo DHT)"""
    user = node.db.get_user(node.current_user_id)
    peers = node.db.get_peers()
    dht_peers = node.db.get_dht_peers()
    tunnel_url = node.db.get_setting("tunnel_url")
    
    # Estatísticas DHT
    dht_stats = {}
    if node.dht:
        dht_stats = node.dht.get_network_stats()
    
    return {
        "user_id": user['user_id'],
        "username": user['username'],
        "local_port": node.port,
        "tunnel_url": tunnel_url,
        "tunnel_active": bool(tunnel_url),
        "peers_connected": len(peers),
        "dht_peers": len(dht_peers),
        "dht_enabled": node.dht_enabled,
        "dht_stats": dht_stats,
        "network_status": "online"
    }

# NOVO: Endpoints específicos do DHT
@app.get("/api/dht/status")
async def get_dht_status():
    """Status detalhado do DHT"""
    if not node.dht_enabled or not node.dht:
        return {"enabled": False, "error": "DHT não habilitado"}
    
    stats = node.dht.get_network_stats()
    return {
        "enabled": True,
        "running": node.dht.is_running,
        "stats": stats
    }

@app.post("/api/dht/find-user")
async def find_user_dht(data: dict):
    """Busca usuário via DHT"""
    user_id = data.get('user_id', '').strip()
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id obrigatório")
    
    if not node.dht_enabled or not node.dht or not node.dht_loop:
        raise HTTPException(status_code=503, detail="DHT não disponível")
    
    try:
        # Executa busca DHT
        future = asyncio.run_coroutine_threadsafe(
            node.find_user_via_dht(user_id),
            node.dht_loop
        )
        presence = future.result(timeout=10)
        
        if presence:
            return {
                "found": True,
                "user": {
                    "user_id": presence.user_id,
                    "username": presence.username,
                    "endpoints": presence.endpoints,
                    "last_seen": presence.last_seen,
                    "reputation_score": presence.reputation_score
                }
            }
        else:
            return {"found": False}
            
    except Exception as e:
        logger.error(f"Erro buscando usuário via DHT: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na busca DHT: {str(e)}")

@app.post("/api/dht/announce")
async def announce_presence_dht():
    """Força anúncio de presença no DHT"""
    if not node.dht_enabled or not node.dht or not node.dht_loop:
        raise HTTPException(status_code=503, detail="DHT não disponível")
    
    try:
        future = asyncio.run_coroutine_threadsafe(
            node.announce_presence(),
            node.dht_loop
        )
        future.result(timeout=5)
        
        return {"success": True, "message": "Presença anunciada"}
        
    except Exception as e:
        logger.error(f"Erro anunciando presença: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no anúncio: {str(e)}")

@app.get("/api/dht/discover-users")
async def discover_users_dht(limit: int = 20):
    """Descobre usuários ativos via DHT"""
    if not node.dht_enabled or not node.dht or not node.dht_loop:
        raise HTTPException(status_code=503, detail="DHT não disponível")
    
    try:
        future = asyncio.run_coroutine_threadsafe(
            node.dht.discover_users(limit),
            node.dht_loop
        )
        users = future.result(timeout=15)
        
        return {
            "users": [
                {
                    "user_id": user.user_id,
                    "username": user.username,
                    "endpoints": user.endpoints,
                    "last_seen": user.last_seen,
                    "reputation_score": user.reputation_score
                }
                for user in users
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro descobrindo usuários: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na descoberta: {str(e)}")

# Endpoint para parar o túnel (mantido)
@app.post("/api/stop-tunnel")
async def stop_tunnel_endpoint():
    global node
    if node and node.cloudflare and node.cloudflare.tunnel_process:
        node.cloudflare.stop_tunnel()
        return {"success": True, "message": "Túnel parado."}
    return {"success": False, "message": "Túnel não estava ativo."}

if __name__ == "__main__":
    # Adiciona importação necessária no topo do arquivo
    import socket
    
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info")