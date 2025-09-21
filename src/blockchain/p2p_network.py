"""
DTC P2P Network Implementation
Rede peer-to-peer para sincronização do blockchain DTC
"""

import asyncio
import json
import time
import threading
from typing import Dict, List, Set, Optional
import websockets
import websockets.server
from websockets.exceptions import ConnectionClosed
import logging
from .real_blockchain import DTCBlockchain, DTCBlock, DTCTransaction, DTCWallet

logger = logging.getLogger(__name__)


class DTCNetworkNode:
    """Nó da rede P2P do blockchain DTC"""

    def __init__(self, blockchain: DTCBlockchain, wallet: DTCWallet, port: int = 9999):
        self.blockchain = blockchain
        self.wallet = wallet
        self.port = port
        self.host = "127.0.0.1"
        self.peers: Set[str] = set()
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.server = None
        self.is_running = False

        # Descoberta de rede
        self.known_peers = [
            "127.0.0.1:9999",
            "127.0.0.1:10000",
            "127.0.0.1:10001",
            "127.0.0.1:10002"
        ]

    async def start_server(self):
        """Inicia o servidor P2P"""
        try:
            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            self.is_running = True

            logger.info(f"🌐 Servidor DTC iniciado em {self.host}:{self.port}")

            # Conecta a peers conhecidos
            await self.connect_to_peers()

            # Inicia sincronização periódica
            asyncio.create_task(self.periodic_sync())

        except Exception as e:
            logger.error(f"Erro iniciando servidor: {e}")

    async def handle_connection(self, websocket, path):
        """Gerencia conexões WebSocket de outros nós"""
        peer_address = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"🤝 Nova conexão de {peer_address}")

        self.connections[peer_address] = websocket
        self.peers.add(peer_address)

        try:
            # Envia handshake
            await self.send_handshake(websocket)

            # Escuta mensagens
            async for message in websocket:
                await self.handle_message(websocket, message)

        except ConnectionClosed:
            logger.info(f"🔌 Conexão fechada: {peer_address}")
        except Exception as e:
            logger.error(f"Erro na conexão {peer_address}: {e}")
        finally:
            # Remove conexão
            if peer_address in self.connections:
                del self.connections[peer_address]
            self.peers.discard(peer_address)

    async def connect_to_peers(self):
        """Conecta a peers conhecidos"""
        for peer in self.known_peers:
            if peer != f"{self.host}:{self.port}":  # Não conecta em si mesmo
                asyncio.create_task(self.connect_to_peer(peer))

    async def connect_to_peer(self, peer_address: str):
        """Conecta a um peer específico"""
        try:
            host, port = peer_address.split(':')
            uri = f"ws://{host}:{port}"

            websocket = await websockets.connect(uri)
            self.connections[peer_address] = websocket
            self.peers.add(peer_address)

            logger.info(f"🔗 Conectado ao peer {peer_address}")

            # Envia handshake
            await self.send_handshake(websocket)

            # Escuta mensagens deste peer
            async for message in websocket:
                await self.handle_message(websocket, message)

        except Exception as e:
            logger.debug(f"Não foi possível conectar a {peer_address}: {e}")

    async def send_handshake(self, websocket):
        """Envia handshake inicial"""
        handshake = {
            "type": "handshake",
            "node_address": self.wallet.address,
            "blockchain_length": len(self.blockchain.chain),
            "latest_hash": self.blockchain.get_latest_block().hash,
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(handshake))

    async def handle_message(self, websocket, message_str: str):
        """Processa mensagens recebidas"""
        try:
            message = json.loads(message_str)
            msg_type = message.get("type")

            if msg_type == "handshake":
                await self.handle_handshake(websocket, message)
            elif msg_type == "request_blockchain":
                await self.handle_blockchain_request(websocket)
            elif msg_type == "blockchain_data":
                await self.handle_blockchain_data(message)
            elif msg_type == "new_block":
                await self.handle_new_block(message)
            elif msg_type == "new_transaction":
                await self.handle_new_transaction(message)
            elif msg_type == "sync_request":
                await self.handle_sync_request(websocket, message)

        except Exception as e:
            logger.error(f"Erro processando mensagem: {e}")

    async def handle_handshake(self, websocket, message):
        """Processa handshake de outros nós"""
        peer_length = message.get("blockchain_length", 0)
        our_length = len(self.blockchain.chain)

        logger.info(f"🤝 Handshake recebido - Blocos: eles={peer_length}, nós={our_length}")

        # Se o peer tem blockchain mais longo, solicita sincronização
        if peer_length > our_length:
            await self.request_blockchain_sync(websocket)

    async def request_blockchain_sync(self, websocket):
        """Solicita sincronização do blockchain"""
        request = {
            "type": "request_blockchain",
            "from_block": len(self.blockchain.chain),
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(request))

    async def handle_blockchain_request(self, websocket):
        """Responde solicitação de blockchain"""
        blockchain_data = {
            "type": "blockchain_data",
            "chain": [self.serialize_block(block) for block in self.blockchain.chain],
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(blockchain_data))

    async def handle_blockchain_data(self, message):
        """Processa dados de blockchain recebidos"""
        try:
            received_chain = message.get("chain", [])

            if len(received_chain) > len(self.blockchain.chain):
                # Valida e substitui blockchain se válido
                if self.validate_received_chain(received_chain):
                    self.blockchain.chain = [self.deserialize_block(block_data) for block_data in received_chain]
                    self.blockchain.recalculate_balances()
                    logger.info(f"✅ Blockchain sincronizado! Novos blocos: {len(received_chain)}")
                else:
                    logger.warning("❌ Blockchain recebido é inválido")

        except Exception as e:
            logger.error(f"Erro sincronizando blockchain: {e}")

    async def handle_new_block(self, message):
        """Processa novo bloco recebido"""
        try:
            block_data = message.get("block")
            new_block = self.deserialize_block(block_data)

            # Valida o novo bloco
            if self.validate_new_block(new_block):
                self.blockchain.chain.append(new_block)
                self.blockchain.update_balances(new_block)
                logger.info(f"✅ Novo bloco aceito: {new_block.index}")

                # Rebroadcast para outros peers
                await self.broadcast_block(new_block, exclude_sender=True)
            else:
                logger.warning(f"❌ Bloco inválido rejeitado: {new_block.index}")

        except Exception as e:
            logger.error(f"Erro processando novo bloco: {e}")

    async def handle_new_transaction(self, message):
        """Processa nova transação recebida"""
        try:
            tx_data = message.get("transaction")
            transaction = self.deserialize_transaction(tx_data)

            # Adiciona à pool de pendentes
            if self.blockchain.add_transaction(transaction):
                logger.info(f"📝 Nova transação aceita: {transaction.id[:8]}...")

                # Rebroadcast para outros peers
                await self.broadcast_transaction(transaction)
            else:
                logger.warning(f"❌ Transação rejeitada: {transaction.id[:8]}...")

        except Exception as e:
            logger.error(f"Erro processando transação: {e}")

    async def broadcast_block(self, block: DTCBlock, exclude_sender: bool = False):
        """Faz broadcast de um novo bloco"""
        message = {
            "type": "new_block",
            "block": self.serialize_block(block),
            "timestamp": time.time()
        }

        await self.broadcast_to_peers(message)
        logger.info(f"📡 Bloco {block.index} enviado para {len(self.peers)} peers")

    async def broadcast_transaction(self, transaction: DTCTransaction):
        """Faz broadcast de uma nova transação"""
        message = {
            "type": "new_transaction",
            "transaction": self.serialize_transaction(transaction),
            "timestamp": time.time()
        }

        await self.broadcast_to_peers(message)

    async def broadcast_to_peers(self, message: Dict):
        """Envia mensagem para todos os peers conectados"""
        if not self.connections:
            return

        message_str = json.dumps(message)

        # Envia para todos os peers
        tasks = []
        for peer_addr, websocket in self.connections.items():
            tasks.append(self.safe_send(websocket, message_str, peer_addr))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def safe_send(self, websocket, message: str, peer_addr: str):
        """Envia mensagem de forma segura"""
        try:
            await websocket.send(message)
        except Exception as e:
            logger.warning(f"Erro enviando para {peer_addr}: {e}")
            # Remove conexão com problema
            if peer_addr in self.connections:
                del self.connections[peer_addr]
            self.peers.discard(peer_addr)

    async def periodic_sync(self):
        """Sincronização periódica com a rede"""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Sincroniza a cada 30 segundos

                if self.connections:
                    # Solicita status de alguns peers
                    for peer_addr, websocket in list(self.connections.items())[:3]:
                        sync_request = {
                            "type": "sync_request",
                            "our_length": len(self.blockchain.chain),
                            "timestamp": time.time()
                        }
                        await self.safe_send(websocket, json.dumps(sync_request), peer_addr)

            except Exception as e:
                logger.error(f"Erro na sincronização periódica: {e}")

    def serialize_block(self, block: DTCBlock) -> Dict:
        """Serializa bloco para JSON"""
        return {
            "index": block.index,
            "timestamp": block.timestamp,
            "transactions": [self.serialize_transaction(tx) for tx in block.transactions],
            "previous_hash": block.previous_hash,
            "nonce": block.nonce,
            "hash": block.hash,
            "miner_address": block.miner_address,
            "difficulty": block.difficulty
        }

    def deserialize_block(self, block_data: Dict) -> DTCBlock:
        """Deserializa bloco do JSON"""
        return DTCBlock(
            index=block_data["index"],
            timestamp=block_data["timestamp"],
            transactions=[self.deserialize_transaction(tx) for tx in block_data["transactions"]],
            previous_hash=block_data["previous_hash"],
            nonce=block_data["nonce"],
            hash=block_data["hash"],
            miner_address=block_data["miner_address"],
            difficulty=block_data["difficulty"]
        )

    def serialize_transaction(self, transaction: DTCTransaction) -> Dict:
        """Serializa transação para JSON"""
        return transaction.to_dict()

    def deserialize_transaction(self, tx_data: Dict) -> DTCTransaction:
        """Deserializa transação do JSON"""
        return DTCTransaction(**tx_data)

    def validate_received_chain(self, chain_data: List[Dict]) -> bool:
        """Valida blockchain recebido"""
        try:
            # Reconstrói e valida a chain
            temp_blockchain = DTCBlockchain(self.wallet.address)
            temp_blockchain.chain = [self.deserialize_block(block_data) for block_data in chain_data]
            return temp_blockchain.validate_chain()
        except Exception as e:
            logger.error(f"Erro validando blockchain: {e}")
            return False

    def validate_new_block(self, block: DTCBlock) -> bool:
        """Valida um novo bloco"""
        try:
            # Verifica índice sequencial
            if block.index != len(self.blockchain.chain):
                return False

            # Verifica hash anterior
            if block.previous_hash != self.blockchain.get_latest_block().hash:
                return False

            # Verifica proof-of-work
            if not block.hash.startswith("0" * block.difficulty):
                return False

            # Verifica hash do bloco
            if block.hash != block.calculate_hash():
                return False

            return True
        except Exception as e:
            logger.error(f"Erro validando bloco: {e}")
            return False

    async def stop(self):
        """Para o nó P2P"""
        self.is_running = False

        # Fecha conexões
        for websocket in self.connections.values():
            await websocket.close()

        # Para servidor
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("🛑 Nó P2P parado")

    def get_network_stats(self) -> Dict:
        """Estatísticas da rede"""
        return {
            "connected_peers": len(self.peers),
            "active_connections": len(self.connections),
            "blockchain_length": len(self.blockchain.chain),
            "pending_transactions": len(self.blockchain.pending_transactions),
            "our_address": self.wallet.address,
            "our_balance": self.blockchain.get_balance(self.wallet.address)
        }