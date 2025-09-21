import sqlite3
import uuid
import time
import logging
from typing import Dict, List, Optional
from cryptography.fernet import Fernet
from datetime import datetime

logger = logging.getLogger(__name__)


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

        # Tabela de posts do feed
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feed_posts (
                id TEXT PRIMARY KEY,
                author_id TEXT,
                author_username TEXT,
                content TEXT,
                timestamp REAL,
                post_type TEXT DEFAULT 'text',
                parent_post_id TEXT,
                thread_level INTEGER DEFAULT 0,
                upvotes INTEGER DEFAULT 0,
                downvotes INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                shares_count INTEGER DEFAULT 0,
                weight_score REAL DEFAULT 1.0,
                is_pinned INTEGER DEFAULT 0,
                tags TEXT,
                metadata TEXT,
                FOREIGN KEY (author_id) REFERENCES users (user_id),
                FOREIGN KEY (parent_post_id) REFERENCES feed_posts (id)
            )
        ''')

        # Tabela de votos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feed_votes (
                id TEXT PRIMARY KEY,
                post_id TEXT,
                voter_id TEXT,
                voter_username TEXT,
                vote_type TEXT,
                vote_weight REAL DEFAULT 1.0,
                timestamp REAL,
                FOREIGN KEY (post_id) REFERENCES feed_posts (id),
                FOREIGN KEY (voter_id) REFERENCES users (user_id),
                UNIQUE(post_id, voter_id)
            )
        ''')

        # Tabela de selos comunitários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS community_badges (
                id TEXT PRIMARY KEY,
                post_id TEXT,
                badge_type TEXT,
                awarded_by TEXT,
                awarded_by_username TEXT,
                timestamp REAL,
                FOREIGN KEY (post_id) REFERENCES feed_posts (id),
                FOREIGN KEY (awarded_by) REFERENCES users (user_id)
            )
        ''')

        # Tabela de reputação dos usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_reputation (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                total_posts INTEGER DEFAULT 0,
                total_votes_received INTEGER DEFAULT 0,
                total_votes_given INTEGER DEFAULT 0,
                positive_votes_received INTEGER DEFAULT 0,
                badges_received INTEGER DEFAULT 0,
                engagement_score REAL DEFAULT 1.0,
                vote_weight REAL DEFAULT 1.0,
                reputation_level TEXT DEFAULT 'novato',
                last_updated REAL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Tabela de sub-threads
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sub_threads (
                id TEXT PRIMARY KEY,
                root_post_id TEXT,
                parent_thread_id TEXT,
                title TEXT,
                description TEXT,
                created_by TEXT,
                created_by_username TEXT,
                timestamp REAL,
                posts_count INTEGER DEFAULT 0,
                participants_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (root_post_id) REFERENCES feed_posts (id),
                FOREIGN KEY (parent_thread_id) REFERENCES sub_threads (id),
                FOREIGN KEY (created_by) REFERENCES users (user_id)
            )
        ''')

        # Índices para performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_posts_timestamp ON feed_posts(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_posts_author ON feed_posts(author_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_posts_parent ON feed_posts(parent_post_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_votes_post ON feed_votes(post_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_community_badges_post ON community_badges(post_id)')

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

    def save_message(self, message):
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
        return messages[::-1]

    def save_discovered_peer(self, peer):
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