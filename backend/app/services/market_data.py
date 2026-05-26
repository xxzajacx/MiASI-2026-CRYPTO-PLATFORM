"""Service for fetching and managing market data from Binance."""

import asyncio
import httpx
import logging
import hmac
import hashlib
import time
from typing import Dict, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class BinanceClient:
    """Service for interacting with Binance Spot and Futures APIs."""
    def __init__(self):
        self.base_url = settings.BINANCE_BASE_URL.strip("/")
        self.futures_url = "https://testnet.binancefuture.com"
        
        # Sanitize API credentials
        self.api_key = settings.BINANCE_API_KEY.strip() if settings.BINANCE_API_KEY else ""
        self.api_secret = settings.BINANCE_SECRET_KEY.strip() if settings.BINANCE_SECRET_KEY else ""
        
        self.headers = {"X-MBX-APIKEY": self.api_key} if self.api_key else {}
        self.symbols = [s.strip() for s in settings.TRACKED_SYMBOLS.split(",")]
        self.prices: Dict[str, float] = {}
        self.running = False

    def _generate_signature(self, query_string: str) -> str:
        """HMAC SHA256 signature for signed requests."""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    async def _signed_request(self, method: str, base_url: str, endpoint: str, params: dict = None) -> dict:
        """Execute a signed HTTP request to Binance."""
        if not self.api_key or "WKLEJ" in self.api_key:
            raise ValueError("Binance API key not configured")
            
        params = params or {}
        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = 5000
        
        # Sort parameters alphabetically as required by Binance
        sorted_items = sorted(params.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_items])
        signature = self._generate_signature(query_string)
        
        full_url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
        headers = {'X-MBX-APIKEY': self.api_key}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(full_url, headers=headers)
                else:
                    response = await client.post(full_url, headers=headers)
                
                if response.status_code == 401:
                    logger.error(f"Binance authentication failed (401) for {endpoint}. Check API keys and IP restrictions.")
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Binance API Error {e.response.status_code} on {endpoint}: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Network request failed: {e}")
                raise

    async def get_account_balance(self) -> dict:
        """Fetch balances and return them separated by Spot and Futures."""
        balances = {"SPOT": {}, "FUTURES": {}}
        
        # Fetch Spot Account Balance
        try:
            spot_data = await self._signed_request("GET", self.base_url, "/api/v3/account")
            for item in spot_data.get("balances", []):
                asset = item["asset"]
                free = float(item["free"])
                locked = float(item["locked"])
                if free + locked > 0:
                    balances["SPOT"][asset] = {"asset": asset, "free": free, "locked": locked, "total": free + locked, "type": "SPOT"}
        except Exception as e:
            logger.warning(f"Spot balance fetch failed: {e}")

        # Fetch Futures Account Balance
        try:
            futures_data = await self._signed_request("GET", self.futures_url, "/fapi/v2/account")
            for asset_data in futures_data.get("assets", []):
                asset = asset_data["asset"]
                wallet_balance = float(asset_data["walletBalance"])
                if wallet_balance != 0:
                    balances["FUTURES"][asset] = {"asset": asset, "free": wallet_balance, "locked": 0.0, "total": wallet_balance, "type": "FUTURES"}
        except Exception as e:
            logger.warning(f"Futures balance fetch failed: {e}")
            
        return balances

    async def transfer_asset(self, asset: str, amount: float, from_type: str, to_type: str) -> dict:
        """Transfer asset between SPOT and FUTURES using Binance Universal Transfer."""
        if from_type == "SPOT" and to_type == "FUTURES":
            transfer_type = "MAIN_UMFUTURE"
        elif from_type == "FUTURES" and to_type == "SPOT":
            transfer_type = "UMFUTURE_MAIN"
        else:
            raise ValueError(f"Unsupported transfer direction: {from_type} -> {to_type}")
            
        params = {
            "type": transfer_type,
            "asset": asset,
            "amount": amount
        }
        return await self._signed_request("POST", self.base_url, "/sapi/v1/asset/transfer", params)

    MIN_ORDER_SIZES = {
        "BTCUSDT": 0.001,
        "ETHUSDT": 0.001,
        "BNBUSDT": 0.01,
    }

    async def execute_trade(self, symbol: str, side: str, amount: float, leverage: int = 1) -> dict:
        """Route trade execution based on leverage (1x Spot, >1x Futures)."""
        # Adjust quantity precision based on asset rules
        if "BTC" in symbol:
            amount = round(amount, 3 if leverage > 1 else 6)
        elif "ETH" in symbol:
            amount = round(amount, 3 if leverage > 1 else 5)
        else:
            amount = round(amount, 2 if leverage > 1 else 4)

        # Validate minimum order requirements
        min_size = self.MIN_ORDER_SIZES.get(symbol, 0.001)
        if amount < min_size:
            raise ValueError(f"Quantity {amount} is below the required minimum of {min_size} {symbol.replace('USDT', '')}")

        if leverage <= 1:
            # Execute Spot Market Order
            params = {"symbol": symbol, "side": side.upper(), "type": "MARKET", "quantity": amount}
            return await self._signed_request("POST", self.base_url, "/api/v3/order", params)
        else:
            # Execute Futures Market Order
            try:
                # Update leverage before order execution
                await self._signed_request("POST", self.futures_url, "/fapi/v1/leverage", {"symbol": symbol, "leverage": leverage})
            except: 
                pass # Leverage might already be configured
            
            params = {"symbol": symbol, "side": side.upper(), "type": "MARKET", "quantity": amount}
            return await self._signed_request("POST", self.futures_url, "/fapi/v1/order", params)

    async def execute_market_buy(self, symbol: str, quantity: float) -> dict:
        """Execute a market BUY order on Binance Spot and return normalized result."""
        result = await self.execute_trade(symbol, "BUY", quantity, leverage=1)
        # Normalize response fields for the trading endpoint
        return {
            "order_id": result.get("orderId", 0),
            "symbol": result.get("symbol", symbol),
            "executed_qty": float(result.get("executedQty", quantity)),
            "cummulative_quote_qty": float(result.get("cummulativeQuoteQty", 0)),
            "fills": result.get("fills", []),
        }

    async def execute_market_sell(self, symbol: str, quantity: float) -> dict:
        """Execute a market SELL order on Binance Spot and return raw result."""
        return await self.execute_trade(symbol, "SELL", quantity, leverage=1)

    FALLBACK_URL = "https://api.binance.com"

    async def fetch_all_prices(self) -> dict:
        """Retrieve current ticker prices for tracked symbols.
        
        Tries the configured base URL first (e.g. demo API), then falls back
        to the public Binance API if that fails.
        """
        urls_to_try = [f"{self.base_url}/api/v3/ticker/price"]
        # Add public Binance API as fallback if base URL differs
        if "api.binance.com" not in self.base_url:
            urls_to_try.append(f"{self.FALLBACK_URL}/api/v3/ticker/price")

        last_error = None
        for url in urls_to_try:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    return {item["symbol"]: float(item["price"]) for item in data if not self.symbols or item["symbol"] in self.symbols}
            except Exception as e:
                last_error = e
                logger.warning(f"Price fetch failed from {url}: {e}")
                continue

        raise last_error or Exception("All price sources exhausted")

    async def refresh(self):
        """Update local price cache."""
        self.prices = await self.fetch_all_prices()

    async def get_all_prices(self) -> dict:
        """Retrieve all prices from cache, refreshing if empty."""
        if not self.prices: 
            await self.refresh()
        return self.prices

    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a specific symbol."""
        return self.prices.get(symbol)

    async def start_fetching_task(self):
        """Background task to continuously update market prices."""
        self.running = True
        while self.running:
            try: 
                await self.refresh()
            except Exception as e: 
                logger.error(f"Price update cycle failed: {e}")
            await asyncio.sleep(5)

# Singleton service instance
market_data_service = BinanceClient()
