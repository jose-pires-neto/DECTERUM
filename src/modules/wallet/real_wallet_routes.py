"""
Real DTC Wallet Routes
Rotas para carteira com blockchain real
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from .real_wallet_service import RealDTCWalletService

router = APIRouter(prefix="/real-wallet", tags=["real-wallet"])

# Instância global do serviço (será inicializada no main.py)
wallet_service: RealDTCWalletService = None


def setup_real_wallet_routes(service: RealDTCWalletService) -> APIRouter:
    """Configura as rotas da carteira DTC real"""
    global wallet_service
    wallet_service = service

    @router.get("/info")
    async def get_wallet_info() -> Dict:
        """Obtém informações completas da carteira"""
        try:
            return wallet_service.get_wallet_info()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/send")
    async def send_dtc(data: Dict[str, Any]) -> Dict:
        """Envia DTC para outro endereço"""
        try:
            recipient = data.get('recipient')
            amount = float(data.get('amount', 0))

            if not recipient or amount <= 0:
                raise HTTPException(status_code=400, detail="Recipient and amount are required")

            if not wallet_service.validate_address(recipient):
                raise HTTPException(status_code=400, detail="Invalid recipient address format")

            if amount < 0.001:
                raise HTTPException(status_code=400, detail="Minimum amount is 0.001 DTC")

            result = wallet_service.send_dtc(recipient, amount)

            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=400, detail=result["error"])

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/badge-vote")
    async def vote_badge(data: Dict[str, Any]) -> Dict:
        """Vota em selo (0.01 DTC)"""
        try:
            post_id = data.get('post_id')
            badge_type = data.get('badge_type')
            post_author_address = data.get('post_author_address')

            if not all([post_id, badge_type, post_author_address]):
                raise HTTPException(
                    status_code=400,
                    detail="post_id, badge_type and post_author_address are required"
                )

            if not wallet_service.validate_address(post_author_address):
                raise HTTPException(status_code=400, detail="Invalid author address format")

            result = wallet_service.vote_badge(post_id, badge_type, post_author_address)

            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=400, detail=result["error"])

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/star-donation")
    async def send_stars(data: Dict[str, Any]) -> Dict:
        """Envia estrelas (0.01 DTC por estrela)"""
        try:
            video_id = data.get('video_id')
            video_author_address = data.get('video_author_address')
            stars = int(data.get('stars', 0))

            if not all([video_id, video_author_address]) or stars <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="video_id, video_author_address and stars are required"
                )

            if not wallet_service.validate_address(video_author_address):
                raise HTTPException(status_code=400, detail="Invalid author address format")

            if stars > 1000:  # Limite máximo
                raise HTTPException(status_code=400, detail="Maximum 1000 stars per donation")

            result = wallet_service.send_stars(video_id, video_author_address, stars)

            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=400, detail=result["error"])

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/claim-mining-reward")
    async def claim_mining_reward(data: Dict[str, Any]) -> Dict:
        """Reivindica recompensa por uptime"""
        try:
            uptime_hours = float(data.get('uptime_hours', 0))

            if uptime_hours < 0.1:  # Mínimo 6 minutos
                raise HTTPException(status_code=400, detail="Minimum uptime is 6 minutes")

            result = wallet_service.claim_mining_reward(uptime_hours)

            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=400, detail=result["error"])

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/transactions")
    async def get_transactions(limit: int = 50) -> Dict:
        """Histórico de transações"""
        try:
            transactions = wallet_service.get_transaction_history(limit)
            return {"transactions": transactions}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/mining-stats")
    async def get_mining_stats() -> Dict:
        """Estatísticas de mineração"""
        try:
            return wallet_service.get_mining_stats()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/blockchain-info")
    async def get_blockchain_info() -> Dict:
        """Informações do blockchain"""
        try:
            return wallet_service.blockchain.get_chain_info()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/network-stats")
    async def get_network_stats() -> Dict:
        """Estatísticas da rede P2P"""
        try:
            if wallet_service.p2p_started:
                return wallet_service.p2p_node.get_network_stats()
            else:
                return {"error": "P2P network not started"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/start-mining")
    async def start_mining() -> Dict:
        """Inicia mineração"""
        try:
            if not wallet_service.miner.is_mining:
                wallet_service.miner.start_mining()
                return {"success": True, "message": "Mining started"}
            else:
                return {"success": False, "message": "Mining already active"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/stop-mining")
    async def stop_mining() -> Dict:
        """Para mineração"""
        try:
            if wallet_service.miner.is_mining:
                wallet_service.miner.stop_mining()
                return {"success": True, "message": "Mining stopped"}
            else:
                return {"success": False, "message": "Mining not active"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/export")
    async def export_wallet() -> Dict:
        """Exporta carteira para backup"""
        try:
            export_data = wallet_service.export_wallet()
            return {
                "export_data": export_data,
                "warning": "Keep this data secure! It contains your private key."
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/qr-address")
    async def get_qr_address() -> Dict:
        """Endereço formatado para QR code"""
        try:
            qr_address = wallet_service.get_address_for_qr()
            return {
                "qr_data": qr_address,
                "address": wallet_service.wallet.address,
                "format": "decterum:address"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/validate-address")
    async def validate_address(data: Dict[str, Any]) -> Dict:
        """Valida endereço DTC"""
        try:
            address = data.get('address', '')
            is_valid = wallet_service.validate_address(address)
            return {
                "address": address,
                "is_valid": is_valid,
                "format": "DTC + 34 characters" if not is_valid else "Valid DTC address"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router