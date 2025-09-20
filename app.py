#!/usr/bin/env python3
"""
DECTERUM - Sistema P2P Descentralizado CORRIGIDO
Backend com descoberta LAN real + DHT funcional
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
from network_discovery import DiscoveredPeer
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import base64
import logging

# Import do sistema de descoberta corrigido
try:
    from network_discovery import NetworkManager, DiscoveredPeer
    NETWORK_DISCOVERY_AVAILABLE = True
except ImportError:
    NETWORK_DISCOVERY_AVAILABLE = False
    print("⚠️ network_discovery.py não encontrado - usando descoberta básica")

# Import do DHT (mantém compatibilidade)
try:
    from dht_manager import DecterumDHT, DHTNode, UserPresence
    DHT_AVAILABLE = True
except ImportError:
    DHT_AVAILABLE = False
    print("⚠️ dht_manager.py não encontrado - DHT desabilitado")

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
    """Peer da rede (legado)"""
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
        """Verifica se cloudflared está instalado"""
        possible_paths = [
            'cloudflared',
            'cloudflared.exe',
            r'C:\Program Files\cloudflared\cloudflared.exe',
            r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
            os.path.expanduser('~\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\\cloudflared.exe'),
            './cloudflared.exe',
            './cloudflared'
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
        
        logger.warning("⚠️ Cloudflared não encontrado.")
        return None
            
    def setup_tunnel(self):
        """Configura e inicia o túnel Cloudflare"""
        cloudflared_path = self.check_cloudflared_installed()
        if not cloudflared_path:
            logger.warning("Cloudflare Tunnel não disponível - apenas acesso local")
            return None
        
        try:
            logger.info("🌐 Configurando túnel Cloudflare...")
            cmd = [
                cloudflared_path, 'tunnel', 
                '--url', f'http://localhost:{self.port}',
                '--no-autoupdate'
            ]
            
            self.tunnel_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Lê a saída do processo para obter URL
            tunnel_url_holder = {'url': None}
            def read_output(process, holder):
                try:
                    while True:
                        line = process.stderr.readline()
                        if not line:
                            break
                        logger.debug(f"Cloudflare: {line.strip()}")
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
            
            logger.warning("⚠️ Timeout configurando túnel Cloudflare")
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
                logger.info("🛑 Túnel Cloudflare parado")
                self.tunnel_process.wait(timeout=10)
            except Exception as e:
                logger.error(f"Erro parando túnel: {e}")
                try:
                    self.tunnel_process.kill()
                except:
                    pass
            finally:
                self.tunnel_process = None
                self.tunnel_url = None

class P2PDatabase:
    """Database para o sistema P2P"""
    
    def __init__(self, db_path: str = "decterum.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa database"""
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
        
        # Tabela de peers descobertos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discovered_peers (
                node_id TEXT PRIMARY KEY,
                host TEXT,
                port INTEGER,
                username TEXT,
                tunnel_url TEXT,
                discovery_method TEXT,
                last_seen REAL,
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
        logger.info("📊 Database inicializada")
    
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
        """Busca mensagens"""
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
    
    def save_discovered_peer(self, peer: DiscoveredPeer):
        """Salva peer descoberto"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO discovered_peers 
            (node_id, host, port, username, tunnel_url, discovery_method, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (peer.node_id, peer.host, peer.port, peer.username, 
              peer.tunnel_url, peer.discovery_method, peer.last_seen, 'online'))
        conn.commit()
        conn.close()
    
    def get_discovered_peers(self) -> List[Dict]:
        """Lista peers descobertos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM discovered_peers WHERE status = "online"')
        results = cursor.fetchall()
        conn.close()
        
        peers = []
        for row in results:
            peers.append({
                'node_id': row[0],
                'host': row[1],
                'port': row[2],
                'username': row[3],
                'tunnel_url': row[4],
                'discovery_method': row[5],
                'last_seen': row[6],
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
    """Nó P2P com descoberta corrigida"""
    
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
        
        # Sistema de descoberta de rede CORRIGIDO
        self.network_manager = None
        if NETWORK_DISCOVERY_AVAILABLE:
            user = self.db.get_user(self.current_user_id)
            self.network_manager = NetworkManager(
                self.node_id, 
                user['username'] if user else 'Unknown',
                port
            )
        
        # DHT (mantém compatibilidade)
        self.dht_enabled = os.getenv('DECTERUM_DHT_ENABLED', 'true').lower() == 'true' and DHT_AVAILABLE
        self.dht: Optional[DecterumDHT] = None
        self.dht_loop = None
        
        if self.dht_enabled:
            self.setup_dht()
        
        logger.info(f"🚀 Nó P2P iniciado: {self.node_id[:8]}... na porta {port}")
        if NETWORK_DISCOVERY_AVAILABLE:
            logger.info("📡 Sistema de descoberta LAN ativo")
        if self.dht_enabled:
            logger.info("🌐 DHT habilitado")
    
    def setup_dht(self):
        """Configura DHT (mantém compatibilidade)"""
        if not DHT_AVAILABLE:
            return
            
        try:
            local_ip = self.get_local_ip()
            dht_node = DHTNode(
                node_id=self.node_id,
                host=local_ip,
                port=self.port
            )
            
            # Bootstrap nodes serão corrigidos pelo NetworkManager
            bootstrap_nodes = []
            self.dht = DecterumDHT(dht_node, bootstrap_nodes)
            logger.info(f"🌐 DHT configurado - Nó: {self.node_id[:8]}...")
            
        except Exception as e:
            logger.error(f"Erro configurando DHT: {e}")
            self.dht_enabled = False
    
    def get_local_ip(self) -> str:
        """Detecta IP local"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def setup_cloudflare_tunnel(self):
        """Configura túnel Cloudflare"""
        tunnel_url = self.cloudflare.setup_tunnel()
        if tunnel_url:
            self.db.set_setting("tunnel_url", tunnel_url)
            return tunnel_url
        return None
    
    def discover_peers(self):
        """Descobre peers usando novo sistema"""
        if self.network_manager:
            # Força descoberta com novo sistema
            self.network_manager.force_discovery()
            
            # Atualiza database com peers descobertos
            discovered_peers = self.network_manager.get_all_peers()
            for peer in discovered_peers:
                self.db.save_discovered_peer(peer)
            
            logger.info(f"🔍 Descoberta concluída: {len(discovered_peers)} peers encontrados")
            return len(discovered_peers)
        else:
            # Fallback para descoberta básica
            logger.warning("📡 Sistema avançado indisponível - usando descoberta básica")
            return self.basic_discovery()
    
    def basic_discovery(self) -> int:
        """Descoberta básica de fallback"""
        local_ports = [8000, 8001, 8002, 8003, 8004]
        found_count = 0
        
        for port in local_ports:
            if port == self.port:
                continue
                
            try:
                response = requests.get(f"http://localhost:{port}/api/status", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Salva como peer descoberto
                    fake_peer = DiscoveredPeer(
                        node_id=data['node_id'],
                        host="localhost",
                        port=port,
                        username=data.get('username', 'Unknown'),
                        discovery_method="basic"
                    )
                    self.db.save_discovered_peer(fake_peer)
                    found_count += 1
            except:
                continue
        
        return found_count
    
    def send_message_to_user(self, recipient_id: str, message: Message) -> bool:
        """Envia mensagem para usuário específico"""
        # 1. Busca em peers descobertos
        peers = self.db.get_discovered_peers()
        for peer_data in peers:
            if peer_data['node_id'] == recipient_id:
                if self.send_message_to_peer_data(peer_data, message):
                    return True
        
        # 2. Busca via NetworkManager se disponível
        if self.network_manager:
            peer = self.network_manager.get_peer_by_id(recipient_id)
            if peer:
                peer_data = {
                    'node_id': peer.node_id,
                    'host': peer.host,
                    'port': peer.port,
                    'tunnel_url': peer.tunnel_url
                }
                if self.send_message_to_peer_data(peer_data, message):
                    return True
        
        # 3. DHT como último recurso
        if self.dht and self.dht_loop:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.find_user_via_dht(recipient_id, message), 
                    self.dht_loop
                )
                return future.result(timeout=10)
            except:
                pass
        
        logger.info(f"📤 Mensagem enfileirada para {recipient_id[:8]}...")
        return False
    
    async def find_user_via_dht(self, user_id: str, message: Message) -> bool:
        """Busca usuário via DHT e envia mensagem"""
        if not self.dht:
            return False
        
        try:
            presence = await self.dht.find_user(user_id)
            if presence:
                for endpoint in presence.endpoints:
                    if await self.try_send_to_endpoint(endpoint, message):
                        return True
        except Exception as e:
            logger.error(f"Erro enviando via DHT: {e}")
        
        return False
    
    async def try_send_to_endpoint(self, endpoint: str, message: Message) -> bool:
        """Tenta enviar mensagem para endpoint específico"""
        try:
            if endpoint.startswith('http'):
                url = f"{endpoint}/api/receive"
            else:
                url = f"http://{endpoint}/api/receive"
            
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=asdict(message)) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.debug(f"Falha enviando para {endpoint}: {e}")
            return False
    
    def send_message_to_peer_data(self, peer_data: Dict, message: Message) -> bool:
        """Envia mensagem para peer específico"""
        try:
            urls = []
            if peer_data.get('tunnel_url'):
                urls.append(f"{peer_data['tunnel_url']}/api/receive")
            urls.append(f"http://{peer_data['host']}:{peer_data['port']}/api/receive")
            
            payload = asdict(message)
            
            for url in urls:
                try:
                    response = requests.post(url, json=payload, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"✅ Mensagem enviada para {peer_data['node_id'][:8]}...")
                        return True
                except Exception as e:
                    logger.debug(f"Falha em {url}: {e}")
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False
    
    def add_manual_peer(self, host: str, port: int) -> bool:
        """Adiciona peer manualmente"""
        if self.network_manager:
            peer = self.network_manager.add_manual_peer(host, port)
            if peer:
                self.db.save_discovered_peer(peer)
                return True
        return False
    
    def background_tasks(self):
        """Tarefas em segundo plano"""
        discovery_timer = 0
        
        while self.is_running:
            try:
                # Descoberta a cada 120 segundos
                if discovery_timer >= 120:
                    self.discover_peers()
                    discovery_timer = 0
                
                time.sleep(1)
                discovery_timer += 1
                
            except Exception as e:
                logger.error(f"Erro em background: {e}")
                time.sleep(5)
    
    def start_background_tasks(self):
        """Inicia tarefas em segundo plano"""
        # Inicia sistema de descoberta
        if self.network_manager:
            self.network_manager.start()
        
        # Thread de background
        thread = threading.Thread(target=self.background_tasks, daemon=True)
        thread.start()
        
        # Configurar túnel Cloudflare
        tunnel_url = self.setup_cloudflare_tunnel()
        if tunnel_url:
            logger.info(f"🌐 Túnel Cloudflare: {tunnel_url}")
        else:
            logger.info("🏠 Modo local apenas")
        
        # Força descoberta inicial
        logger.info("🔍 Iniciando descoberta de peers...")
        self.discover_peers()

# Inicialização do FastAPI
app = FastAPI(title="DECTERUM P2P Fixed", version="2.2")

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
        if node.network_manager:
            node.network_manager.stop()
        if node.dht:
            await node.dht.stop()

@app.get("/")
async def home():
    """Serve a interface principal"""
    return FileResponse("static/index.html")

@app.get("/api/status")
async def get_status():
    """Status do nó"""
    user = node.db.get_user(node.current_user_id)
    peers = node.db.get_discovered_peers()
    tunnel_url = node.db.get_setting("tunnel_url")
    
    return {
        "node_id": node.node_id,
        "username": user['username'] if user else "Unknown",
        "port": node.port,
        "tunnel_url": tunnel_url or "",
        "peer_count": len(peers),
        "discovery_system": "advanced" if NETWORK_DISCOVERY_AVAILABLE else "basic",
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
        # Atualiza NetworkManager se disponível
        if node.network_manager:
            node.network_manager.username = username
    
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
    """Envia mensagem"""
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
    
    # Tentar enviar
    success = False
    if recipient_id:
        success = node.send_message_to_user(recipient_id, message)
    
    return {
        "success": True,
        "message_id": message.id,
        "delivered": success,
        "discovery_method": "advanced" if NETWORK_DISCOVERY_AVAILABLE else "basic"
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
    """Lista peers conectados"""
    peers = node.db.get_discovered_peers()
    return {"peers": peers}

@app.post("/api/discover")
async def discover_peers():
    """Força descoberta de peers"""
    peers_found = node.discover_peers()
    return {"peers_found": peers_found}

@app.post("/api/add-manual-peer")
async def add_manual_peer(data: dict):
    """Adiciona peer manualmente"""
    host = data.get('host', '').strip()
    port = data.get('port', 0)
    
    if not host or not port:
        raise HTTPException(status_code=400, detail="Host e porta obrigatórios")
    
    success = node.add_manual_peer(host, port)
    if success:
        return {"success": True, "message": "Peer adicionado com sucesso"}
    else:
        raise HTTPException(status_code=400, detail="Não foi possível conectar ao peer")

@app.get("/api/network-info")
async def get_network_info():
    """Informações da rede"""
    user = node.db.get_user(node.current_user_id)
    peers = node.db.get_discovered_peers()
    tunnel_url = node.db.get_setting("tunnel_url")
    
    # Estatísticas do NetworkManager
    network_stats = {}
    if node.network_manager:
        all_peers = node.network_manager.get_all_peers()
        network_stats = {
            "total_discovered": len(all_peers),
            "lan_peers": len([p for p in all_peers if p.discovery_method == "lan"]),
            "manual_peers": len([p for p in all_peers if p.discovery_method == "manual"]),
            "dht_peers": len([p for p in all_peers if p.discovery_method == "dht"])
        }
    
    return {
        "user_id": user['user_id'],
        "username": user['username'],
        "local_port": node.port,
        "tunnel_url": tunnel_url,
        "tunnel_active": bool(tunnel_url),
        "peers_connected": len(peers),
        "discovery_system": "advanced" if NETWORK_DISCOVERY_AVAILABLE else "basic",
        "network_stats": network_stats,
        "dht_enabled": node.dht_enabled,
        "network_status": "online"
    }

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info")