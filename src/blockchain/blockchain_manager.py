"""
Blockchain Manager
Gerencia escolha entre blockchain simples ou real
"""

import os
import asyncio
from typing import Optional
from .dtc_blockchain import DTCBlockchain as SimpleBlockchain
from .real_blockchain import DTCBlockchain as RealBlockchain, DTCWallet, DTCMiner
from .p2p_network import DTCNetworkNode
from .crypto_exchange import dtc_exchange


class BlockchainManager:
    """Gerenciador de blockchain para DECTERUM"""

    def __init__(self, database, use_real_blockchain: bool = False, port: int = 9999):
        self.database = database
        self.use_real_blockchain = use_real_blockchain
        self.port = port

        # Instâncias
        self.simple_blockchain: Optional[SimpleBlockchain] = None
        self.real_blockchain: Optional[RealBlockchain] = None
        self.wallet: Optional[DTCWallet] = None
        self.miner: Optional[DTCMiner] = None
        self.p2p_node: Optional[DTCNetworkNode] = None

        # Estado
        self.is_network_started = False
        self.mining_active = False

    def initialize(self, user_id: str):
        """Inicializa o blockchain escolhido"""
        if self.use_real_blockchain:
            self._initialize_real_blockchain(user_id)
        else:
            self._initialize_simple_blockchain()

        print(f"📚 Blockchain {'REAL' if self.use_real_blockchain else 'SIMPLES'} inicializado")

    def _initialize_simple_blockchain(self):
        """Inicializa blockchain simples"""
        self.simple_blockchain = SimpleBlockchain(self.database)

    def _initialize_real_blockchain(self, user_id: str):
        """Inicializa blockchain real"""
        self.wallet = DTCWallet()
        self.real_blockchain = RealBlockchain(self.wallet.address)
        self.miner = DTCMiner(self.real_blockchain, self.wallet)
        self.p2p_node = DTCNetworkNode(self.real_blockchain, self.wallet, self.port)

    async def start_network(self):
        """Inicia rede P2P (apenas para blockchain real)"""
        if self.use_real_blockchain and not self.is_network_started:
            await self.p2p_node.start_server()
            self.is_network_started = True
            print("🌐 Rede P2P iniciada")

            # Inicia mineração automática
            self.start_mining()

    async def stop_network(self):
        """Para rede P2P"""
        if self.use_real_blockchain and self.is_network_started:
            self.stop_mining()
            await self.p2p_node.stop()
            self.is_network_started = False
            print("🛑 Rede P2P parada")

    def start_mining(self):
        """Inicia mineração (apenas blockchain real)"""
        if self.use_real_blockchain and not self.mining_active:
            self.miner.start_mining()
            self.mining_active = True
            print("⛏️  Mineração iniciada")

    def stop_mining(self):
        """Para mineração"""
        if self.use_real_blockchain and self.mining_active:
            self.miner.stop_mining()
            self.mining_active = False
            print("🛑 Mineração parada")

    # Métodos unificados (funcionam com ambos os blockchains)

    def get_balance(self, user_id: str) -> float:
        """Obtém saldo (unificado)"""
        if self.use_real_blockchain:
            if user_id == "current_user" and self.wallet:
                return self.real_blockchain.get_balance(self.wallet.address)
            else:
                return self.real_blockchain.get_balance(user_id)
        else:
            return self.simple_blockchain.get_balance(user_id)

    def create_transaction(self, sender: str, recipient: str, amount: float,
                          transaction_type: str = "transfer", metadata: dict = None):
        """Cria transação (unificado)"""
        if self.use_real_blockchain:
            if sender == "current_user" and self.wallet:
                # Usuário atual usando carteira real
                transaction = self.wallet.create_transaction(recipient, amount)
                transaction.metadata = metadata or {}
                return self.real_blockchain.add_transaction(transaction)
            else:
                # Outras transações (sistema, etc.)
                # Para blockchain real, precisaria de carteira específica
                return False
        else:
            return self.simple_blockchain.create_transaction(
                sender, recipient, amount, transaction_type, metadata
            )

    def get_transactions(self, user_id: str, limit: int = 50) -> list:
        """Obtém transações (unificado)"""
        if self.use_real_blockchain:
            transactions = []
            address = self.wallet.address if user_id == "current_user" else user_id

            # Busca em todos os blocos
            for block in reversed(self.real_blockchain.chain):
                for tx in block.transactions:
                    if tx.sender_address == address or tx.recipient_address == address:
                        transactions.append({
                            "id": tx.id,
                            "sender": tx.sender_address,
                            "recipient": tx.recipient_address,
                            "amount": tx.amount,
                            "transaction_type": getattr(tx, 'metadata', {}).get('type', 'transfer'),
                            "timestamp": tx.timestamp,
                            "delivered": True,
                            "read": True
                        })

                if len(transactions) >= limit:
                    break

            return transactions[:limit]
        else:
            return self.simple_blockchain.get_user_transactions(user_id, limit)

    def give_initial_balance(self, user_id: str, amount: float = 100.0):
        """Dá saldo inicial (unificado)"""
        if self.use_real_blockchain:
            # No blockchain real, saldo inicial vem da mineração
            if user_id == "current_user" and self.wallet:
                # Força mineração de um bloco para dar saldo inicial
                if len(self.real_blockchain.chain) == 1:  # Apenas bloco gênesis
                    # Adiciona transação dummy para forçar mineração
                    dummy_tx = self.wallet.create_transaction(self.wallet.address, 0.001)
                    dummy_tx.sender_address = "INITIAL_GRANT"
                    dummy_tx.amount = amount
                    self.real_blockchain.add_transaction(dummy_tx)
        else:
            self.simple_blockchain.give_initial_balance(user_id, amount)

    def get_blockchain_info(self) -> dict:
        """Informações do blockchain (unificado)"""
        if self.use_real_blockchain:
            info = self.real_blockchain.get_chain_info()
            info.update({
                "type": "real",
                "wallet_address": self.wallet.address if self.wallet else None,
                "mining_active": self.mining_active,
                "network_active": self.is_network_started
            })
            return info
        else:
            return {
                "type": "simple",
                "blocks": len(self.simple_blockchain.get_user_transactions("system")),
                "pending_transactions": 0,
                "difficulty": "N/A",
                "mining_reward": "N/A"
            }

    def get_wallet_address(self) -> str:
        """Obtém endereço da carteira (para blockchain real)"""
        if self.use_real_blockchain and self.wallet:
            return self.wallet.address
        return "N/A"

    def export_wallet(self) -> dict:
        """Exporta carteira (blockchain real)"""
        if self.use_real_blockchain and self.wallet:
            from cryptography.hazmat.primitives import serialization
            return {
                "address": self.wallet.address,
                "private_key_pem": self.wallet.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ).decode(),
                "balance": self.get_balance("current_user"),
                "blockchain_type": "real"
            }
        return {"error": "Only available for real blockchain"}

    def get_exchange_rates(self) -> dict:
        """Obtém taxas de câmbio"""
        return {
            "DTC_USD": dtc_exchange.get_exchange_rate("DTC", "USD"),
            "DTC_BTC": dtc_exchange.get_exchange_rate("DTC", "BTC"),
            "DTC_ETH": dtc_exchange.get_exchange_rate("DTC", "ETH"),
            "market_info": dtc_exchange.get_dtc_market_info()
        }

    def calculate_conversion(self, amount: float, from_currency: str, to_currency: str) -> dict:
        """Calcula conversão de moedas"""
        return dtc_exchange.calculate_conversion(amount, from_currency, to_currency)

    def get_supported_currencies(self) -> list:
        """Lista moedas suportadas para conversão"""
        return dtc_exchange.get_supported_currencies()