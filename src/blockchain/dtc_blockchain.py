import time
import json
import hashlib
import uuid
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class DTCTransaction:
    """Transação da DECTERUM Coin"""
    id: str
    sender: str
    recipient: str
    amount: float
    transaction_type: str  # 'transfer', 'badge_vote', 'star_donation', 'mining_reward'
    metadata: Dict = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self):
        return {
            'id': self.id,
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'transaction_type': self.transaction_type,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }


class DTCBlockchain:
    """Blockchain simplificado para DECTERUM Coin"""

    def __init__(self, database):
        self.db = database
        self.init_blockchain_tables()

    def init_blockchain_tables(self):
        """Inicializa tabelas do blockchain"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Tabela de transações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dtc_transactions (
                id TEXT PRIMARY KEY,
                sender TEXT,
                recipient TEXT,
                amount REAL,
                transaction_type TEXT,
                metadata TEXT,
                timestamp REAL,
                block_height INTEGER DEFAULT 0
            )
        ''')

        # Tabela de saldos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dtc_balances (
                user_id TEXT PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                last_updated REAL
            )
        ''')

        # Tabela de mineração/recompensas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dtc_mining_stats (
                user_id TEXT PRIMARY KEY,
                total_mined REAL DEFAULT 0.0,
                blocks_mined INTEGER DEFAULT 0,
                last_mining_reward REAL,
                uptime_hours REAL DEFAULT 0.0
            )
        ''')

        conn.commit()
        conn.close()

    def create_transaction(self, sender: str, recipient: str, amount: float,
                          transaction_type: str, metadata: Dict = None) -> DTCTransaction:
        """Cria uma nova transação"""
        transaction = DTCTransaction(
            id=str(uuid.uuid4()),
            sender=sender,
            recipient=recipient,
            amount=amount,
            transaction_type=transaction_type,
            metadata=metadata or {}
        )

        # Verifica saldo do remetente
        if sender != "NETWORK" and not self.has_sufficient_balance(sender, amount):
            raise ValueError("Saldo insuficiente")

        # Salva transação
        self.save_transaction(transaction)

        # Atualiza saldos
        self.update_balance(sender, -amount)
        self.update_balance(recipient, amount)

        return transaction

    def save_transaction(self, transaction: DTCTransaction):
        """Salva transação no banco"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO dtc_transactions
            (id, sender, recipient, amount, transaction_type, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction.id,
            transaction.sender,
            transaction.recipient,
            transaction.amount,
            transaction.transaction_type,
            json.dumps(transaction.metadata),
            transaction.timestamp
        ))

        conn.commit()
        conn.close()

    def get_balance(self, user_id: str) -> float:
        """Obtém saldo atual do usuário"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT balance FROM dtc_balances WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()

        return result[0] if result else 0.0

    def update_balance(self, user_id: str, amount_change: float):
        """Atualiza saldo do usuário"""
        if user_id == "NETWORK":
            return  # Sistema não tem saldo

        conn = self.db.get_connection()
        cursor = conn.cursor()

        current_balance = self.get_balance(user_id)
        new_balance = max(0, current_balance + amount_change)  # Não pode ficar negativo

        cursor.execute('''
            INSERT OR REPLACE INTO dtc_balances (user_id, balance, last_updated)
            VALUES (?, ?, ?)
        ''', (user_id, new_balance, time.time()))

        conn.commit()
        conn.close()

    def has_sufficient_balance(self, user_id: str, amount: float) -> bool:
        """Verifica se usuário tem saldo suficiente"""
        return self.get_balance(user_id) >= amount

    def get_user_transactions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Obtém transações do usuário"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM dtc_transactions
            WHERE sender = ? OR recipient = ?
            ORDER BY timestamp DESC LIMIT ?
        ''', (user_id, user_id, limit))

        results = cursor.fetchall()
        conn.close()

        transactions = []
        for row in results:
            transactions.append({
                'id': row[0],
                'sender': row[1],
                'recipient': row[2],
                'amount': row[3],
                'transaction_type': row[4],
                'metadata': json.loads(row[5]) if row[5] else {},
                'timestamp': row[6]
            })

        return transactions

    def give_initial_balance(self, user_id: str, amount: float = 100.0):
        """Dá saldo inicial para novo usuário"""
        if self.get_balance(user_id) == 0:
            self.create_transaction(
                sender="NETWORK",
                recipient=user_id,
                amount=amount,
                transaction_type="initial_grant",
                metadata={"reason": "Welcome bonus"}
            )

    def give_mining_reward(self, user_id: str, uptime_hours: float):
        """Recompensa por manter o nó online"""
        reward = min(uptime_hours * 0.1, 5.0)  # Máximo 5 DTC por sessão

        if reward > 0:
            self.create_transaction(
                sender="NETWORK",
                recipient=user_id,
                amount=reward,
                transaction_type="mining_reward",
                metadata={"uptime_hours": uptime_hours}
            )

            # Atualiza estatísticas de mineração
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO dtc_mining_stats
                (user_id, total_mined, blocks_mined, last_mining_reward, uptime_hours)
                VALUES (
                    ?,
                    COALESCE((SELECT total_mined FROM dtc_mining_stats WHERE user_id = ?), 0) + ?,
                    COALESCE((SELECT blocks_mined FROM dtc_mining_stats WHERE user_id = ?), 0) + 1,
                    ?,
                    ?
                )
            ''', (user_id, user_id, reward, user_id, reward, uptime_hours))

            conn.commit()
            conn.close()

        return reward

    def get_total_supply(self) -> float:
        """Obtém o supply total de DTC em circulação"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT SUM(balance) FROM dtc_balances WHERE balance > 0')
        result = cursor.fetchone()
        conn.close()

        return result[0] if result and result[0] else 0.0

    def get_current_timestamp(self) -> float:
        """Obtém timestamp atual"""
        return time.time()