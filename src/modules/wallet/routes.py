from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from ...blockchain.dtc_blockchain import DTCBlockchain
import time
import uuid

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


def setup_wallet_routes(blockchain: DTCBlockchain, node) -> APIRouter:
    """Configura as rotas da carteira DTC"""

    @router.get("/info")
    async def get_wallet_info() -> Dict:
        """Obtém informações da carteira"""
        try:
            user_id = node.current_user_id
            balance = blockchain.get_balance(user_id)
            transactions = blockchain.get_user_transactions(user_id, limit=10)

            return {
                "user_id": user_id,
                "balance": balance,
                "recent_transactions": transactions
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/send")
    async def send_dtc(data: Dict[str, Any]) -> Dict:
        """Envia DTC para outro usuário"""
        try:
            recipient = data.get('recipient')
            amount = float(data.get('amount', 0))

            if not recipient or amount <= 0:
                raise HTTPException(status_code=400, detail="Recipient and amount are required")

            if amount < 0.001:
                raise HTTPException(status_code=400, detail="Minimum amount is 0.001 DTC")

            transaction = blockchain.create_transaction(
                sender=node.current_user_id,
                recipient=recipient,
                amount=amount,
                transaction_type="transfer",
                metadata={"manual_transfer": True}
            )

            return {
                "success": True,
                "transaction_id": transaction.id,
                "message": f"Sent {amount} DTC to {recipient}"
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/badge-vote")
    async def vote_badge(data: Dict[str, Any]) -> Dict:
        """Vota em um selo (custando 0.01 DTC)"""
        try:
            post_id = data.get('post_id')
            badge_type = data.get('badge_type')
            post_author = data.get('post_author')

            if not all([post_id, badge_type, post_author]):
                raise HTTPException(status_code=400, detail="post_id, badge_type and post_author are required")

            vote_cost = 0.01

            transaction = blockchain.create_transaction(
                sender=node.current_user_id,
                recipient=post_author,
                amount=vote_cost,
                transaction_type="badge_vote",
                metadata={
                    "post_id": post_id,
                    "badge_type": badge_type
                }
            )

            return {
                "success": True,
                "transaction_id": transaction.id,
                "amount_paid": vote_cost,
                "message": f"Badge vote successful! {post_author} earned {vote_cost} DTC"
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/star-donation")
    async def send_stars(data: Dict[str, Any]) -> Dict:
        """Envia estrelas para criador de vídeo (0.01 DTC por estrela)"""
        try:
            video_id = data.get('video_id')
            video_author = data.get('video_author')
            stars = int(data.get('stars', 0))

            if not all([video_id, video_author]) or stars <= 0:
                raise HTTPException(status_code=400, detail="video_id, video_author and stars are required")

            if stars > 1000:  # Limite máximo por doação
                raise HTTPException(status_code=400, detail="Maximum 1000 stars per donation")

            star_value = 0.01
            total_amount = stars * star_value

            transaction = blockchain.create_transaction(
                sender=node.current_user_id,
                recipient=video_author,
                amount=total_amount,
                transaction_type="star_donation",
                metadata={
                    "video_id": video_id,
                    "stars": stars,
                    "star_value": star_value
                }
            )

            return {
                "success": True,
                "transaction_id": transaction.id,
                "stars_sent": stars,
                "amount_paid": total_amount,
                "message": f"Sent {stars} stars ({total_amount} DTC) to {video_author}"
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/exchange-rates")
    async def get_exchange_rates() -> Dict:
        """Obtém taxas de câmbio simuladas do DTC"""
        try:
            # Simular taxa de câmbio baseada no supply total
            total_supply = blockchain.get_total_supply()
            base_rate = max(0.001, 1.0 / (total_supply + 1000))  # Taxa base inversamente proporcional ao supply

            return {
                "DTC": {
                    "USD": round(base_rate, 6),
                    "EUR": round(base_rate * 0.85, 6),
                    "BRL": round(base_rate * 5.2, 6),
                    "BTC": round(base_rate * 0.000025, 8)
                },
                "last_updated": blockchain.get_current_timestamp(),
                "total_supply": total_supply,
                "market_cap_usd": round(total_supply * base_rate, 2)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/transactions")
    async def get_transactions(limit: int = 50) -> Dict:
        """Obtém histórico de transações"""
        try:
            transactions = blockchain.get_user_transactions(node.current_user_id, limit)
            return {"transactions": transactions}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/claim-mining-reward")
    async def claim_mining_reward(data: Dict[str, Any]) -> Dict:
        """Reivindica recompensa por tempo online"""
        try:
            uptime_hours = float(data.get('uptime_hours', 0))

            if uptime_hours < 0.1:  # Mínimo 6 minutos
                raise HTTPException(status_code=400, detail="Minimum uptime is 6 minutes")

            reward = blockchain.give_mining_reward(node.current_user_id, uptime_hours)

            return {
                "success": True,
                "reward": reward,
                "uptime_hours": uptime_hours,
                "message": f"Mining reward: {reward} DTC for {uptime_hours:.1f}h uptime"
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/mining-status")
    async def get_mining_status() -> Dict:
        """Obtém status da mineração"""
        try:
            # Simular detecção de hardware (CPU cores, RAM)
            import psutil

            cpu_count = psutil.cpu_count()
            memory_gb = round(psutil.virtual_memory().total / (1024**3), 1)
            cpu_percent = psutil.cpu_percent(interval=1)

            # Calcular dificuldade baseada no hardware
            hardware_score = min(cpu_count * 0.1 + memory_gb * 0.01, 1.0)

            return {
                "hardware_info": {
                    "cpu_cores": cpu_count,
                    "memory_gb": memory_gb,
                    "cpu_usage": cpu_percent,
                    "hardware_score": hardware_score
                },
                "mining_enabled": False,  # Por padrão desabilitado
                "estimated_daily_reward": round(hardware_score * 0.1, 4),  # Recompensa conservadora
                "power_consumption_warning": cpu_count > 4 or memory_gb < 4
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/enable-mining")
    async def enable_mining(data: Dict[str, Any]) -> Dict:
        """Ativa mineração opcional (usuário deve confirmar)"""
        try:
            user_confirmed = data.get('user_confirmed', False)

            if not user_confirmed:
                raise HTTPException(status_code=400, detail="User must confirm mining activation")

            # Simular ativação de mineração
            # IMPORTANTE: Implementar controles de CPU para não sobrecarregar o sistema
            return {
                "success": True,
                "message": "Mining enabled with hardware-appropriate difficulty",
                "warning": "Mining will use available CPU resources. You can disable it anytime."
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/disable-mining")
    async def disable_mining() -> Dict:
        """Desativa mineração"""
        try:
            return {
                "success": True,
                "message": "Mining disabled successfully"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/convert")
    async def convert_crypto(data: Dict[str, Any]) -> Dict:
        """Converte DTC para outras criptomoedas (simulado)"""
        try:
            amount = float(data.get('amount', 0))
            from_currency = data.get('from_currency', 'DTC')
            to_currency = data.get('to_currency', 'USDT')

            if amount <= 0 or from_currency != 'DTC':
                raise HTTPException(status_code=400, detail="Invalid conversion parameters")

            # Verificar saldo
            user_balance = blockchain.get_balance(node.current_user_id)
            if amount > user_balance:
                raise HTTPException(status_code=400, detail="Insufficient balance")

            # Taxas de conversão simuladas
            exchange_rates = {
                'USDT': 0.01,
                'USDC': 0.01,
                'BTC': 0.0000002,
                'ETH': 0.000003,
                'BNB': 0.000025,
                'ADA': 0.01
            }

            if to_currency not in exchange_rates:
                raise HTTPException(status_code=400, detail="Unsupported currency")

            rate = exchange_rates[to_currency]
            gross_amount = amount * rate
            exchange_fee = gross_amount * 0.01  # 1% fee
            final_amount = gross_amount - exchange_fee

            # Simular processo de conversão (deduze do saldo DTC)
            blockchain.create_transaction(
                sender=node.current_user_id,
                recipient="EXCHANGE_BRIDGE",
                amount=amount,
                transaction_type="crypto_conversion",
                metadata={
                    "to_currency": to_currency,
                    "rate": rate,
                    "final_amount": final_amount,
                    "exchange_fee": exchange_fee
                }
            )

            # Gerar ID de ordem simulado
            order_id = f"CONV-{int(time.time())}-{str(uuid.uuid4())[:8]}"

            return {
                "success": True,
                "order_id": order_id,
                "converted_amount": final_amount,
                "to_currency": to_currency,
                "exchange_rate": rate,
                "exchange_fee": exchange_fee,
                "message": f"Conversion order created. You will receive ~{final_amount:.6f} {to_currency}",
                "note": "This is a simulation. In production, this would integrate with real exchanges."
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/conversion-orders")
    async def get_conversion_orders() -> Dict:
        """Obtém histórico de ordens de conversão"""
        try:
            transactions = blockchain.get_user_transactions(node.current_user_id, limit=100)

            conversion_orders = []
            for tx in transactions:
                if tx.get('transaction_type') == 'crypto_conversion':
                    conversion_orders.append({
                        "order_id": f"CONV-{int(tx['timestamp'])}-{tx['id'][:8]}",
                        "from_amount": tx['amount'],
                        "from_currency": "DTC",
                        "to_currency": tx['metadata'].get('to_currency', 'Unknown'),
                        "to_amount": tx['metadata'].get('final_amount', 0),
                        "status": "completed",  # Simulado
                        "timestamp": tx['timestamp']
                    })

            return {"orders": conversion_orders}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router