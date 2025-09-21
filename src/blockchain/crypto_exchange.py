"""
DTC Crypto Exchange System
Sistema de conversão DTC para outras criptomoedas
"""

import requests
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class ExchangeRate:
    """Taxa de câmbio entre criptomoedas"""
    from_currency: str
    to_currency: str
    rate: float
    timestamp: float
    source: str


class DTCCryptoExchange:
    """Sistema de conversão DTC"""

    def __init__(self):
        # Taxas base (será atualizado dinamicamente)
        self.base_rates = {
            "DTC_USD": 0.01,    # 1 DTC = $0.01 USD
            "DTC_BTC": 0.0000002,  # 1 DTC = 0.0000002 BTC
            "DTC_ETH": 0.000003,   # 1 DTC = 0.000003 ETH
            "DTC_BNB": 0.000025,   # 1 DTC = 0.000025 BNB
            "DTC_ADA": 0.01,       # 1 DTC = 0.01 ADA
            "DTC_USDT": 0.01,      # 1 DTC = 0.01 USDT
            "DTC_USDC": 0.01,      # 1 DTC = 0.01 USDC
        }

        # Cache de taxas
        self.rate_cache: Dict[str, ExchangeRate] = {}
        self.cache_duration = 300  # 5 minutos

        # Suporte a exchanges externas
        self.supported_exchanges = {
            "binance": {
                "url": "https://api.binance.com/api/v3/ticker/price",
                "active": True
            },
            "coinbase": {
                "url": "https://api.coinbase.com/v2/exchange-rates",
                "active": True
            },
            "coingecko": {
                "url": "https://api.coingecko.com/api/v3/simple/price",
                "active": True
            }
        }

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """Obtém taxa de câmbio entre duas moedas"""
        pair = f"{from_currency}_{to_currency}"

        # Verifica cache
        if pair in self.rate_cache:
            cached_rate = self.rate_cache[pair]
            if time.time() - cached_rate.timestamp < self.cache_duration:
                return cached_rate

        # Busca nova taxa
        rate = self._fetch_exchange_rate(from_currency, to_currency)
        if rate:
            self.rate_cache[pair] = rate
            return rate

        return None

    def _fetch_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """Busca taxa de câmbio"""
        pair = f"{from_currency}_{to_currency}"

        # Se é conversão DTC, usa taxa base
        if pair in self.base_rates:
            return ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=self.base_rates[pair],
                timestamp=time.time(),
                source="internal"
            )

        # Conversão inversa DTC
        inverse_pair = f"{to_currency}_{from_currency}"
        if inverse_pair in self.base_rates:
            return ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=1.0 / self.base_rates[inverse_pair],
                timestamp=time.time(),
                source="internal_inverse"
            )

        # Busca em APIs externas
        external_rate = self._fetch_external_rate(from_currency, to_currency)
        if external_rate:
            return external_rate

        return None

    def _fetch_external_rate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """Busca taxa em APIs externas"""
        try:
            # Tenta CoinGecko primeiro
            rate = self._fetch_coingecko_rate(from_currency, to_currency)
            if rate:
                return rate

            # Fallback para outras APIs
            # (implementação básica)
            return None

        except Exception as e:
            print(f"Erro buscando taxa externa: {e}")
            return None

    def _fetch_coingecko_rate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """Busca taxa no CoinGecko"""
        try:
            # Mapeamento de símbolos para IDs do CoinGecko
            coin_ids = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "BNB": "binancecoin",
                "ADA": "cardano",
                "USDT": "tether",
                "USDC": "usd-coin"
            }

            if from_currency not in coin_ids or to_currency not in coin_ids:
                return None

            from_id = coin_ids[from_currency]
            to_currency_lower = to_currency.lower()

            url = f"https://api.coingecko.com/api/v3/simple/price?ids={from_id}&vs_currencies={to_currency_lower}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if from_id in data and to_currency_lower in data[from_id]:
                    rate = float(data[from_id][to_currency_lower])
                    return ExchangeRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=rate,
                        timestamp=time.time(),
                        source="coingecko"
                    )

        except Exception as e:
            print(f"Erro no CoinGecko: {e}")

        return None

    def calculate_conversion(self, amount: float, from_currency: str, to_currency: str) -> Optional[Dict]:
        """Calcula conversão entre moedas"""
        if from_currency == to_currency:
            return {
                "amount_from": amount,
                "amount_to": amount,
                "rate": 1.0,
                "fee": 0.0,
                "total": amount
            }

        rate = self.get_exchange_rate(from_currency, to_currency)
        if not rate:
            return None

        # Calcula valores
        converted_amount = amount * rate.rate
        fee_percentage = 0.01  # 1% de taxa
        fee = converted_amount * fee_percentage
        total_received = converted_amount - fee

        return {
            "amount_from": amount,
            "amount_to": total_received,
            "gross_amount": converted_amount,
            "rate": rate.rate,
            "fee": fee,
            "fee_percentage": fee_percentage * 100,
            "total": total_received,
            "rate_source": rate.source,
            "rate_timestamp": rate.timestamp
        }

    def get_supported_currencies(self) -> List[str]:
        """Lista moedas suportadas"""
        return ["DTC", "BTC", "ETH", "BNB", "ADA", "USDT", "USDC", "USD"]

    def get_dtc_market_info(self) -> Dict:
        """Informações de mercado do DTC"""
        # Simula dados de mercado (em uma implementação real, seria baseado em volume/transações)
        return {
            "price_usd": self.base_rates["DTC_USD"],
            "price_btc": self.base_rates["DTC_BTC"],
            "market_cap_usd": self.base_rates["DTC_USD"] * 1000000,  # Simula supply de 1M
            "volume_24h": 50000,  # Volume simulado
            "change_24h": 0.05,   # +5% (simulado)
            "last_updated": time.time()
        }

    def create_conversion_order(self, amount: float, from_currency: str, to_currency: str,
                              user_address: str) -> Dict:
        """Cria ordem de conversão (simulada)"""
        conversion = self.calculate_conversion(amount, from_currency, to_currency)

        if not conversion:
            return {
                "success": False,
                "error": "Conversion not supported or rate unavailable"
            }

        # Em uma implementação real, isso seria processado via smart contracts
        # ou integração com exchanges reais
        order_id = f"conv_{int(time.time())}_{user_address[:8]}"

        return {
            "success": True,
            "order_id": order_id,
            "conversion_details": conversion,
            "status": "pending",
            "estimated_completion": time.time() + 300,  # 5 minutos
            "instructions": self._get_conversion_instructions(from_currency, to_currency)
        }

    def _get_conversion_instructions(self, from_currency: str, to_currency: str) -> List[str]:
        """Instruções para conversão"""
        if from_currency == "DTC":
            return [
                f"1. Send {from_currency} to the conversion pool",
                f"2. Wait for confirmation (1-3 blocks)",
                f"3. Receive {to_currency} in your external wallet",
                f"4. Transaction will be visible in your history"
            ]
        else:
            return [
                f"1. Send {from_currency} to our conversion address",
                f"2. Provide your DTC wallet address",
                f"3. Wait for network confirmations",
                f"4. Receive DTC in your wallet (automatic)"
            ]

    def update_base_rates(self, new_rates: Dict[str, float]):
        """Atualiza taxas base do DTC"""
        for pair, rate in new_rates.items():
            if pair in self.base_rates:
                self.base_rates[pair] = rate
                # Limpa cache relacionado
                if pair in self.rate_cache:
                    del self.rate_cache[pair]

    def get_conversion_history(self, user_address: str) -> List[Dict]:
        """Histórico de conversões do usuário (simulado)"""
        # Em implementação real, seria buscado do banco de dados
        return [
            {
                "order_id": "conv_1234567890_abcd1234",
                "from_currency": "DTC",
                "to_currency": "USDT",
                "amount_from": 100.0,
                "amount_to": 0.99,
                "rate": 0.01,
                "fee": 0.01,
                "status": "completed",
                "timestamp": time.time() - 86400,  # 1 dia atrás
                "tx_hash": "0xabcd1234..."
            }
        ]

    def estimate_network_fees(self, currency: str) -> Dict:
        """Estima taxas de rede para diferentes cryptos"""
        network_fees = {
            "BTC": {"fee": 0.0001, "unit": "BTC", "confirmation_time": "10-60 min"},
            "ETH": {"fee": 0.002, "unit": "ETH", "confirmation_time": "1-5 min"},
            "BNB": {"fee": 0.001, "unit": "BNB", "confirmation_time": "3-5 sec"},
            "ADA": {"fee": 0.17, "unit": "ADA", "confirmation_time": "20 sec"},
            "USDT": {"fee": 1.0, "unit": "USDT", "confirmation_time": "1-5 min"},
            "USDC": {"fee": 1.0, "unit": "USDC", "confirmation_time": "1-5 min"},
            "DTC": {"fee": 0.001, "unit": "DTC", "confirmation_time": "30 sec"}
        }

        return network_fees.get(currency, {"fee": 0, "unit": currency, "confirmation_time": "unknown"})


# Instância global
dtc_exchange = DTCCryptoExchange()