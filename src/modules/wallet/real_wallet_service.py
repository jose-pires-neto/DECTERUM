"""
Real DTC Wallet Service
Serviço da carteira com blockchain real
"""

import asyncio
import time
from typing import Dict, List, Optional
from ...blockchain.real_blockchain import DTCBlockchain, DTCWallet, DTCMiner, create_dtc_network_node
from ...blockchain.p2p_network import DTCNetworkNode


class RealDTCWalletService:
    """Serviço da carteira DTC com blockchain real"""

    def __init__(self, port: int = 9999):
        # Cria nó completo da rede DTC
        self.blockchain, self.wallet, self.miner = create_dtc_network_node(port)

        # Rede P2P
        self.p2p_node = DTCNetworkNode(self.blockchain, self.wallet, port)
        self.p2p_started = False

        # Controle de mineração
        self.auto_mining = True
        self.session_start_time = time.time()

    async def start_network(self):
        """Inicia a rede P2P"""
        if not self.p2p_started:
            await self.p2p_node.start_server()
            self.p2p_started = True

            # Inicia mineração automática
            if self.auto_mining:
                self.miner.start_mining()

    async def stop_network(self):
        """Para a rede P2P"""
        if self.p2p_started:
            self.miner.stop_mining()
            await self.p2p_node.stop()
            self.p2p_started = False

    def get_wallet_info(self) -> Dict:
        """Informações da carteira"""
        balance = self.blockchain.get_balance(self.wallet.address)
        transactions = self.get_transaction_history(limit=10)

        return {
            "address": self.wallet.address,
            "balance": balance,
            "recent_transactions": transactions,
            "blockchain_info": self.blockchain.get_chain_info(),
            "network_info": self.p2p_node.get_network_stats() if self.p2p_started else {},
            "mining_active": self.miner.is_mining
        }

    def send_dtc(self, recipient_address: str, amount: float) -> Dict:
        """Envia DTC para outro endereço"""
        try:
            # Verifica saldo
            current_balance = self.blockchain.get_balance(self.wallet.address)
            total_cost = amount + 0.001  # Taxa de transação

            if current_balance < total_cost:
                raise ValueError(f"Saldo insuficiente: {current_balance} < {total_cost}")

            # Cria transação
            transaction = self.wallet.create_transaction(recipient_address, amount, fee=0.001)

            # Adiciona à blockchain
            if self.blockchain.add_transaction(transaction):
                # Faz broadcast para a rede
                if self.p2p_started:
                    asyncio.create_task(self.p2p_node.broadcast_transaction(transaction))

                return {
                    "success": True,
                    "transaction_id": transaction.id,
                    "amount": amount,
                    "fee": 0.001,
                    "recipient": recipient_address
                }
            else:
                raise ValueError("Falha ao processar transação")

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def vote_badge(self, post_id: str, badge_type: str, post_author_address: str) -> Dict:
        """Vota em selo (0.01 DTC)"""
        try:
            vote_cost = 0.01
            current_balance = self.blockchain.get_balance(self.wallet.address)

            if current_balance < vote_cost + 0.001:  # Inclui taxa
                raise ValueError("Saldo insuficiente para votar em selo")

            # Cria transação com metadados
            transaction = self.wallet.create_transaction(
                recipient_address=post_author_address,
                amount=vote_cost,
                fee=0.001
            )

            # Adiciona metadados (seria armazenado fora da blockchain principal)
            transaction.metadata = {
                "type": "badge_vote",
                "post_id": post_id,
                "badge_type": badge_type
            }

            if self.blockchain.add_transaction(transaction):
                # Broadcast para rede
                if self.p2p_started:
                    asyncio.create_task(self.p2p_node.broadcast_transaction(transaction))

                return {
                    "success": True,
                    "transaction_id": transaction.id,
                    "amount_paid": vote_cost,
                    "badge_type": badge_type
                }
            else:
                raise ValueError("Falha ao processar voto")

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def send_stars(self, video_id: str, video_author_address: str, stars: int) -> Dict:
        """Envia estrelas (0.01 DTC por estrela)"""
        try:
            star_value = 0.01
            total_amount = stars * star_value
            current_balance = self.blockchain.get_balance(self.wallet.address)

            if current_balance < total_amount + 0.001:  # Inclui taxa
                raise ValueError("Saldo insuficiente para enviar estrelas")

            # Cria transação
            transaction = self.wallet.create_transaction(
                recipient_address=video_author_address,
                amount=total_amount,
                fee=0.001
            )

            # Metadados
            transaction.metadata = {
                "type": "star_donation",
                "video_id": video_id,
                "stars": stars,
                "star_value": star_value
            }

            if self.blockchain.add_transaction(transaction):
                # Broadcast para rede
                if self.p2p_started:
                    asyncio.create_task(self.p2p_node.broadcast_transaction(transaction))

                return {
                    "success": True,
                    "transaction_id": transaction.id,
                    "stars_sent": stars,
                    "amount_paid": total_amount
                }
            else:
                raise ValueError("Falha ao enviar estrelas")

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def claim_mining_reward(self, uptime_hours: float) -> Dict:
        """Reivindica recompensa por tempo online"""
        try:
            # Recompensa baseada no tempo (sem criar transação especial)
            # O sistema de mineração já recompensa automaticamente

            # Aqui podemos dar bônus adicional por uptime
            bonus_rate = 0.1  # 0.1 DTC por hora
            max_bonus = 5.0   # Máximo 5 DTC por sessão

            bonus_amount = min(uptime_hours * bonus_rate, max_bonus)

            if bonus_amount >= 0.01:  # Mínimo para valer a pena
                # Cria transação de bônus (do sistema)
                system_wallet = DTCWallet()  # Carteira temporária do sistema
                bonus_transaction = system_wallet.create_transaction(
                    recipient_address=self.wallet.address,
                    amount=bonus_amount,
                    fee=0.0
                )
                bonus_transaction.sender_address = "UPTIME_BONUS"

                if self.blockchain.add_transaction(bonus_transaction):
                    return {
                        "success": True,
                        "reward": bonus_amount,
                        "uptime_hours": uptime_hours,
                        "type": "uptime_bonus"
                    }

            return {
                "success": False,
                "error": "Tempo mínimo não atingido ou recompensa muito baixa"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_transaction_history(self, limit: int = 50) -> List[Dict]:
        """Histórico de transações da carteira"""
        transactions = []
        my_address = self.wallet.address

        # Busca em todos os blocos
        for block in reversed(self.blockchain.chain):
            for tx in block.transactions:
                if tx.sender_address == my_address or tx.recipient_address == my_address:
                    transactions.append({
                        "id": tx.id,
                        "sender": tx.sender_address,
                        "recipient": tx.recipient_address,
                        "amount": tx.amount,
                        "fee": tx.fee,
                        "timestamp": tx.timestamp,
                        "type": getattr(tx, 'metadata', {}).get('type', 'transfer'),
                        "block_index": block.index,
                        "is_received": tx.recipient_address == my_address
                    })

                if len(transactions) >= limit:
                    break

            if len(transactions) >= limit:
                break

        return transactions

    def get_mining_stats(self) -> Dict:
        """Estatísticas de mineração"""
        my_address = self.wallet.address
        blocks_mined = 0
        total_rewards = 0.0

        # Conta blocos minerados por este nó
        for block in self.blockchain.chain:
            if block.miner_address == my_address:
                blocks_mined += 1
                # Encontra transação de recompensa
                for tx in block.transactions:
                    if tx.recipient_address == my_address and tx.sender_address == "MINING_REWARD":
                        total_rewards += tx.amount

        return {
            "blocks_mined": blocks_mined,
            "total_mining_rewards": total_rewards,
            "current_difficulty": self.blockchain.difficulty,
            "mining_active": self.miner.is_mining,
            "blockchain_length": len(self.blockchain.chain),
            "pending_transactions": len(self.blockchain.pending_transactions)
        }

    def export_wallet(self) -> Dict:
        """Exporta dados da carteira para backup"""
        return {
            "address": self.wallet.address,
            "private_key_pem": self.wallet.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode(),
            "balance": self.blockchain.get_balance(self.wallet.address),
            "export_timestamp": time.time()
        }

    def get_address_for_qr(self) -> str:
        """Retorna endereço formatado para QR code"""
        return f"decterum:{self.wallet.address}"

    def validate_address(self, address: str) -> bool:
        """Valida formato de endereço DTC"""
        return (
            isinstance(address, str) and
            address.startswith("DTC") and
            len(address) == 37  # DTC + 34 caracteres
        )