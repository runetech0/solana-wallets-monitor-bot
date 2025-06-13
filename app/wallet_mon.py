import asyncio
import json
import os
from typing import Any
import websockets
from solana.rpc.api import Client
from solders.signature import Signature
from app.gvs import OUTPUT_DIR
from .logs_config import get_logger
import httpx
from solana.exceptions import SolanaRpcException


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
        wallet: str,
        output_queue: asyncio.Queue[SplTokenBuy],
        helius_api_key: str,
    ) -> None:
        self._wallet = wallet
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
            logger.debug("Waiting for new transaction signatures ...")
            trx_sig = await self._new_sig_queue.get()
            logger.info(f"New trx sig: {trx_sig}")
            try:
                trx = await self.fetch_trx(trx_sig)
                res = await self.detect_token_buy_from_meta(trx["meta"])
                logger.info(f"Token buy: {res}")
                if res:
                    await self._output_queue.put(res)

            except ValueError:
                continue

            except Exception as e:
                logger.error(f"Error in sig monitor. {e}", exc_info=True)

    async def fetch_trx(self, signature: str) -> dict[str, Any]:
        logger.info(f"\n🔍 Fetching details for {signature}")
        try:
            tx = self._client.get_transaction(
                Signature.from_string(signature),
                encoding="jsonParsed",
                max_supported_transaction_version=0,
            )

        except SolanaRpcException as e:
            logger.warning(f"Hitting rate limit resolving the sig. {e}", exc_info=True)
            return await self.fetch_trx(signature)

        if not tx.value:
            raise ValueError(
                f"❌ Transaction {signature} not found or not yet confirmed."
            )

        result = json.loads(tx.value.to_json())

        with open(
            os.path.join(OUTPUT_DIR, f"{self._wallet}_last_trx.json").__str__(), "w"
        ) as f:
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
                    {"mentions": [self._wallet]},
                    {"commitment": "finalized"},
                ],
            }
            await websocket.send(json.dumps(subscription))

            sub_done: bool = False
            while True:
                if sub_done:
                    logger.debug("Waiting for new messages ...")
                else:
                    logger.info(f"Subscribing the logs of {self._wallet!r} ...")
                message = await websocket.recv()
                data = json.loads(message)
                logger.debug(f"New message received: {data}")

                if not sub_done:
                    logger.debug("Subscription not done yet! Checking for sub ...")
                    if data.get("error", None):
                        return logger.error(
                            f"There was an error subscribing to the wallet: {self._wallet!r}",
                            exc_info=True,
                        )

                    else:
                        logger.info(f"✅ Subscribed to wallet: {self._wallet!r}.")
                        sub_done = True

                    continue

                try:
                    await self._handle_message(data)

                except Exception as e:
                    logger.error(
                        f"Error handling the message. Message: {data}, Error: {e}",
                        exc_info=True,
                    )

    async def _handle_message(self, data: dict[str, Any]) -> None:

        result = data.get("params", {}).get("result", {})
        sig = result.get("value", {}).get("signature")

        if sig:
            logger.debug(f"New transaction sig found: {sig}")
            await self._new_sig_queue.put(sig)

        else:
            logger.debug("New transaction sig not found in message!")

    async def detect_token_buy_from_meta(
        self, meta: dict[str, Any]
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
                if post["owner"] != self._wallet:
                    continue  # Skip others

                mint = post["mint"]
                post_amt = float(post["uiTokenAmount"]["uiAmount"])
                decimals = post["uiTokenAmount"]["decimals"]

                key = (mint, self._wallet)
                pre_amt = pre_map.get(key, 0.0)

                if post_amt > pre_amt:
                    token_meta = await self.get_token_meta(mint)
                    # token_meta = {"name": "Unknown", "symbol": "unknown"}
                    return {
                        "buyer": self._wallet,
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
