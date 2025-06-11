import asyncio
import json
from typing import Any
import websockets
from solana.rpc.api import Client
from solders.signature import Signature
from .logs_config import get_logger
import httpx


logger = get_logger()


from typing import TypedDict


class SplTokenBuy(TypedDict):
    buyer: str
    mint: str
    amount_received: float
    final_balance: float
    previous_balance: float
    decimals: int
    type: str
    token_name: str
    token_symbol: str


class WalletsMonitor:
    def __init__(
        self,
        wallet_addresses: list[str],
        output_queue: asyncio.Queue[SplTokenBuy],
        helius_api_key: str,
    ) -> None:
        self.wallet_addresses = wallet_addresses
        self._client = Client("https://api.mainnet-beta.solana.com")
        self._new_sig_queue: asyncio.Queue[str] = asyncio.Queue()
        self._output_queue = output_queue
        self._helius_url = "https://mainnet.helius-rpc.com/"
        self._helius_client = httpx.AsyncClient()
        self._helius_api_key = helius_api_key

        self._tasks: list[asyncio.Task[Any]] = []

    async def start(self) -> None:

        try:
            logger.info("🔔 Starting transaction monitor...")
            await self.main()

        except Exception as e:
            logger.error(f"Error in trx monitor. {e}", exc_info=True)
            await self.stop()
            return await self.start()

    async def stop(self) -> None:
        for task in self._tasks:
            if not task.cancelled() and not task.done():
                task.cancel()

    async def main(self) -> None:
        self._tasks.append(asyncio.create_task(self.monitor_wallet_transactions()))
        while True:
            trx_sig = await self._new_sig_queue.get()
            try:
                trx = await self.fetch_trx(trx_sig)
                res = await self.detect_token_buy_from_meta(
                    trx["meta"], self.wallet_addresses[0]
                )
                logger.info(res)

            except ValueError:
                continue

            except Exception as e:
                logger.error(f"Error in trx monitor. {e}", exc_info=True)

    async def fetch_trx(self, signature: str) -> dict[str, Any]:
        logger.info(f"\n🔍 Fetching details for {signature}")
        tx = self._client.get_transaction(
            Signature.from_string(signature),
            encoding="jsonParsed",
            max_supported_transaction_version=0,
        )

        if not tx.value:
            raise ValueError(
                f"❌ Transaction {signature} not found or not yet confirmed."
            )

        result = json.loads(tx.value.to_json())

        with open("last_trx.json", "w") as f:
            json.dump(result, f)

        return dict(result)

    async def monitor_wallet_transactions(self) -> None:
        uri = "wss://api.mainnet-beta.solana.com/"
        async with websockets.connect(uri) as websocket:
            subscription: dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": self.wallet_addresses},
                    {"commitment": "finalized"},
                ],
            }
            await websocket.send(json.dumps(subscription))
            logger.info(f"✅ Subscribed to wallets: {self.wallet_addresses}")

            while True:
                message = await websocket.recv()
                data = json.loads(message)
                result = data.get("params", {}).get("result", {})
                sig = result.get("value", {}).get("signature")
                if sig:
                    await self._new_sig_queue.put(sig)

    async def detect_token_buy_from_meta(
        self, meta: dict[str, Any], wallet: str
    ) -> SplTokenBuy | None:
        """
        Detects whether a wallet received a new SPL token (likely a buy) based on meta.
        Returns a dict with details if buy detected, else None.
        """
        try:
            # Token balance snapshots
            pre_balances = meta.get("preTokenBalances", [])
            post_balances = meta.get("postTokenBalances", [])

            # Map pre balances by (mint, owner)
            pre_map = {
                (pre["mint"], pre["owner"]): float(pre["uiTokenAmount"]["uiAmount"])
                for pre in pre_balances
            }

            # Check post balances to find tokens gained
            for post in post_balances:
                if post["owner"] != wallet:
                    continue  # Skip others

                mint = post["mint"]
                post_amt = float(post["uiTokenAmount"]["uiAmount"])
                decimals = post["uiTokenAmount"]["decimals"]

                key = (mint, wallet)
                pre_amt = pre_map.get(key, 0.0)

                if post_amt > pre_amt:
                    token_meta = await self.get_token_meta(mint)
                    return {
                        "buyer": wallet,
                        "mint": mint,
                        "amount_received": post_amt - pre_amt,
                        "final_balance": post_amt,
                        "previous_balance": pre_amt,
                        "decimals": decimals,
                        "type": "spl-token-buy",
                        "token_name": token_meta["name"],
                        "token_symbol": token_meta["symbol"],
                    }

            return None  # No token purchase detected

        except Exception as e:
            logger.error(f"[Token buy detection failed] {e}", exc_info=True)
            return None

    async def get_token_meta(self, token_address: str) -> dict[str, Any]:

        querystring = {"api-key": self._helius_api_key}

        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "getAsset",
            "params": {"id": token_address},
        }
        headers = {"Content-Type": "application/json"}

        response = await self._helius_client.request(
            "POST", self._helius_url, json=payload, headers=headers, params=querystring
        )

        return dict(response.json()["result"]["content"]["metadata"])
