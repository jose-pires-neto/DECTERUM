"""
DECTERUM Real Blockchain Implementation
Implementação de blockchain real com mineração proof-of-work
"""

import hashlib
import json
import time
import threading
import socket
import struct
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import uuid
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import base64


@dataclass
class DTCTransaction:
    """Transação DTC com assinatura criptográfica"""
    id: str
    sender_address: str
    recipient_address: str
    amount: float
    fee: float
    timestamp: float
    signature: str = ""
    public_key: str = ""

    def to_dict(self):
        return asdict(self)

    def get_hash(self) -> str:
        """Hash da transação para verificação"""
        tx_data = {
            'id': self.id,
            'sender_address': self.sender_address,
            'recipient_address': self.recipient_address,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp
        }
        return hashlib.sha256(json.dumps(tx_data, sort_keys=True).encode()).hexdigest()


@dataclass
class DTCBlock:
    """Bloco do blockchain DTC"""
    index: int
    timestamp: float
    transactions: List[DTCTransaction]
    previous_hash: str
    nonce: int = 0
    hash: str = ""
    miner_address: str = ""
    difficulty: int = 4

    def calculate_hash(self) -> str:
        """Calcula hash do bloco"""
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'miner_address': self.miner_address
        }
        return hashlib.sha256(json.dumps(block_data, sort_keys=True).encode()).hexdigest()

    def mine_block(self, difficulty: int) -> bool:
        """Minera o bloco usando Proof-of-Work"""
        target = "0" * difficulty
        start_time = time.time()

        print(f"⛏️  Minerando bloco {self.index} (dificuldade: {difficulty})...")

        while True:
            self.hash = self.calculate_hash()

            if self.hash.startswith(target):
                mining_time = time.time() - start_time
                print(f"✅ Bloco {self.index} minerado! Hash: {self.hash[:16]}... (Tempo: {mining_time:.2f}s)")
                return True

            self.nonce += 1

            # Limita tempo de mineração (evita travamento)
            if time.time() - start_time > 300:  # 5 minutos máximo
                return False


class DTCWallet:
    """Carteira criptográfica real para DTC"""

    def __init__(self):
        # Gera par de chaves RSA
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        self.address = self.generate_address()

    def generate_address(self) -> str:
        """Gera endereço da carteira baseado na chave pública"""
        public_bytes = self.public_key.public_bytes(
            encoding=Encoding.PEM,
            format=PublicFormat.SubjectPublicKeyInfo
        )
        # Hash duplo como Bitcoin
        sha256 = hashlib.sha256(public_bytes).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256)
        return "DTC" + ripemd160.hexdigest()[:34]  # Endereço DTC

    def sign_transaction(self, transaction: DTCTransaction) -> str:
        """Assina transação com chave privada"""
        tx_hash = transaction.get_hash()
        signature = self.private_key.sign(
            tx_hash.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode()

    def verify_signature(self, transaction: DTCTransaction) -> bool:
        """Verifica assinatura de uma transação"""
        try:
            # Decodifica chave pública
            public_key_bytes = base64.b64decode(transaction.public_key)
            public_key = serialization.load_pem_public_key(public_key_bytes)

            # Verifica assinatura
            signature = base64.b64decode(transaction.signature)
            tx_hash = transaction.get_hash()

            public_key.verify(
                signature,
                tx_hash.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    def create_transaction(self, recipient_address: str, amount: float, fee: float = 0.001) -> DTCTransaction:
        """Cria e assina uma transação"""
        transaction = DTCTransaction(
            id=str(uuid.uuid4()),
            sender_address=self.address,
            recipient_address=recipient_address,
            amount=amount,
            fee=fee,
            timestamp=time.time(),
            public_key=base64.b64encode(
                self.public_key.public_bytes(
                    encoding=Encoding.PEM,
                    format=PublicFormat.SubjectPublicKeyInfo
                )
            ).decode()
        )

        transaction.signature = self.sign_transaction(transaction)
        return transaction


class DTCBlockchain:
    """Blockchain real do DECTERUM Coin"""

    def __init__(self, node_address: str):
        self.chain: List[DTCBlock] = []
        self.pending_transactions: List[DTCTransaction] = []
        self.mining_reward = 50.0  # DTC por bloco
        self.difficulty = 4  # Dificuldade inicial
        self.target_block_time = 30  # 30 segundos por bloco
        self.node_address = node_address
        self.balances: Dict[str, float] = {}
        self.is_mining = False
        self.connected_nodes: List[str] = []

        # Cria bloco gênesis
        self.create_genesis_block()

    def create_genesis_block(self):
        """Cria o primeiro bloco do blockchain"""
        genesis_block = DTCBlock(
            index=0,
            timestamp=time.time(),
            transactions=[],
            previous_hash="0",
            miner_address="GENESIS",
            difficulty=self.difficulty
        )
        genesis_block.hash = genesis_block.calculate_hash()
        self.chain.append(genesis_block)
        print("🎯 Bloco Gênesis criado!")

    def get_latest_block(self) -> DTCBlock:
        """Retorna o último bloco"""
        return self.chain[-1]

    def add_transaction(self, transaction: DTCTransaction) -> bool:
        """Adiciona transação à pool de pendentes"""
        # Verifica assinatura
        wallet = DTCWallet()
        if not wallet.verify_signature(transaction):
            print(f"❌ Transação inválida: assinatura incorreta")
            return False

        # Verifica saldo (exceto para recompensas de mineração)
        if transaction.sender_address != "MINING_REWARD":
            sender_balance = self.get_balance(transaction.sender_address)
            if sender_balance < (transaction.amount + transaction.fee):
                print(f"❌ Saldo insuficiente: {sender_balance} < {transaction.amount + transaction.fee}")
                return False

        self.pending_transactions.append(transaction)
        print(f"📝 Transação adicionada: {transaction.amount} DTC de {transaction.sender_address[:10]}...")
        return True

    def mine_pending_transactions(self, miner_address: str) -> bool:
        """Minera as transações pendentes"""
        if self.is_mining:
            return False

        self.is_mining = True

        try:
            # Cria transação de recompensa
            reward_transaction = DTCTransaction(
                id=str(uuid.uuid4()),
                sender_address="MINING_REWARD",
                recipient_address=miner_address,
                amount=self.mining_reward,
                fee=0.0,
                timestamp=time.time()
            )

            # Coleta taxas das transações
            total_fees = sum(tx.fee for tx in self.pending_transactions)
            reward_transaction.amount += total_fees

            # Cria novo bloco
            block = DTCBlock(
                index=len(self.chain),
                timestamp=time.time(),
                transactions=self.pending_transactions + [reward_transaction],
                previous_hash=self.get_latest_block().hash,
                miner_address=miner_address,
                difficulty=self.difficulty
            )

            # Minera o bloco
            if block.mine_block(self.difficulty):
                self.chain.append(block)
                self.update_balances(block)
                self.pending_transactions = []
                self.adjust_difficulty()

                print(f"💰 Bloco minerado! Recompensa: {reward_transaction.amount} DTC")

                # Broadcast para outros nós
                self.broadcast_block(block)
                return True
            else:
                print("⏰ Tempo limite de mineração atingido")
                return False

        finally:
            self.is_mining = False

    def update_balances(self, block: DTCBlock):
        """Atualiza saldos após um novo bloco"""
        for transaction in block.transactions:
            # Deduz do remetente
            if transaction.sender_address != "MINING_REWARD":
                if transaction.sender_address not in self.balances:
                    self.balances[transaction.sender_address] = 0
                self.balances[transaction.sender_address] -= (transaction.amount + transaction.fee)

            # Adiciona ao destinatário
            if transaction.recipient_address not in self.balances:
                self.balances[transaction.recipient_address] = 0
            self.balances[transaction.recipient_address] += transaction.amount

    def get_balance(self, address: str) -> float:
        """Obtém saldo de um endereço"""
        return self.balances.get(address, 0.0)

    def adjust_difficulty(self):
        """Ajusta dificuldade baseado no tempo de mineração"""
        if len(self.chain) < 2:
            return

        # Calcula tempo médio dos últimos 10 blocos
        recent_blocks = self.chain[-10:] if len(self.chain) >= 10 else self.chain[1:]
        if len(recent_blocks) < 2:
            return

        total_time = recent_blocks[-1].timestamp - recent_blocks[0].timestamp
        avg_time = total_time / (len(recent_blocks) - 1)

        # Ajusta dificuldade
        if avg_time < self.target_block_time * 0.8:  # Muito rápido
            self.difficulty += 1
            print(f"📈 Dificuldade aumentada para {self.difficulty}")
        elif avg_time > self.target_block_time * 1.2:  # Muito lento
            self.difficulty = max(1, self.difficulty - 1)
            print(f"📉 Dificuldade diminuída para {self.difficulty}")

    def validate_chain(self) -> bool:
        """Valida toda a cadeia de blocos"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]

            # Verifica hash do bloco atual
            if current.hash != current.calculate_hash():
                return False

            # Verifica ligação com bloco anterior
            if current.previous_hash != previous.hash:
                return False

            # Verifica proof-of-work
            if not current.hash.startswith("0" * current.difficulty):
                return False

        return True

    def add_node(self, node_address: str):
        """Adiciona nó à rede"""
        if node_address not in self.connected_nodes:
            self.connected_nodes.append(node_address)
            print(f"🌐 Nó conectado: {node_address}")

    def broadcast_block(self, block: DTCBlock):
        """Broadcast do novo bloco para outros nós"""
        # TODO: Implementar comunicação P2P
        print(f"📡 Broadcasting bloco {block.index} para {len(self.connected_nodes)} nós")

    def get_chain_info(self) -> Dict:
        """Informações da blockchain"""
        return {
            "blocks": len(self.chain),
            "pending_transactions": len(self.pending_transactions),
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "total_supply": sum(self.balances.values()),
            "connected_nodes": len(self.connected_nodes)
        }


class DTCMiner:
    """Minerador automático"""

    def __init__(self, blockchain: DTCBlockchain, wallet: DTCWallet):
        self.blockchain = blockchain
        self.wallet = wallet
        self.is_mining = False
        self.mining_thread = None

    def start_mining(self):
        """Inicia mineração contínua"""
        if self.is_mining:
            return

        self.is_mining = True
        self.mining_thread = threading.Thread(target=self._mining_loop)
        self.mining_thread.start()
        print(f"⛏️  Mineração iniciada! Endereço: {self.wallet.address}")

    def stop_mining(self):
        """Para a mineração"""
        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join()
        print("🛑 Mineração parada")

    def _mining_loop(self):
        """Loop principal de mineração"""
        while self.is_mining:
            if len(self.blockchain.pending_transactions) >= 1:  # Minera com 1+ transação
                self.blockchain.mine_pending_transactions(self.wallet.address)

            time.sleep(5)  # Espera 5 segundos antes de tentar novamente


# Funções de utilidade
def create_dtc_network_node(port: int = 9999) -> Tuple[DTCBlockchain, DTCWallet, DTCMiner]:
    """Cria um nó completo da rede DTC"""
    wallet = DTCWallet()
    blockchain = DTCBlockchain(wallet.address)
    miner = DTCMiner(blockchain, wallet)

    print(f"🚀 Nó DTC criado!")
    print(f"📍 Endereço da carteira: {wallet.address}")
    print(f"🔗 Blockchain inicializado com {len(blockchain.chain)} blocos")

    return blockchain, wallet, miner