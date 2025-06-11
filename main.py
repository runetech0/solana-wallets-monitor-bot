from app.logs_config import get_logger
from app.wallet_mon import WalletsMonitor, SplTokenBuy
from app import io, gvs
import asyncio
from tweepy import Client  # type: ignore
from app.config_reader import Config
from app import constants


logger = get_logger()


def prepare_tweet_content(buy_info: SplTokenBuy) -> str:
    text = open(gvs.TWEET_CONTENT_FILE).read().strip()
    text = text.replace(constants.COIN_ADDRESS_PLACEHOLDER, buy_info["mint"])
    text = text.replace(
        constants.COIN_AMOUNT_PLACEHOLDER, str(buy_info["amount_received"])
    )

    text = text.replace(constants.COIN_NAME_PLACEHOLDER, buy_info["token_name"])
    text = text.replace(constants.COIN_SYMBOL_PLACEHOLDER, buy_info["token_symbol"])
    text = text.replace(constants.BUYER_WALLET_ADDRESS_PLACEHOLDER, buy_info["buyer"])

    return text


async def main() -> None:

    if not any(
        [
            Config.TWITTER.API_KEY,
            Config.TWITTER.API_KEY_SECRET,
            Config.TWITTER.API_ACCESS_TOKEN,
            Config.TWITTER.API_ACCESS_TOKEN_SECRET,
        ]
    ):
        return logger.error("Incomplete or missing Twitter API Keys in config.toml")

    tweet_content_template = (
        open(gvs.TWEET_CONTENT_FILE, mode="r", encoding="UTF-8").read().strip()
    )
    if not tweet_content_template:
        return logger.error(f"No tweet content available in {gvs.TWEET_CONTENT_FILE}")

    if not (wallets := io.read_txt_lines(gvs.WALLETS_FILE)):
        return logger.error(f"No wallets in {gvs.WALLETS_FILE}")

    twitter_client = Client(
        consumer_key=Config.TWITTER.API_KEY,
        consumer_secret=Config.TWITTER.API_KEY_SECRET,
        access_token=Config.TWITTER.API_ACCESS_TOKEN,
        access_token_secret=Config.TWITTER.API_ACCESS_TOKEN_SECRET,
    )

    try:

        me = await twitter_client.get_me()  # type: ignore
        logger.info(f"User logged-in as {me}")

    except Exception as e:
        return logger.error(f"User failed to login to twitter. {e}", exc_info=True)

    queue: asyncio.Queue[SplTokenBuy] = asyncio.Queue()
    wallets_mon = WalletsMonitor(
        wallet_addresses=wallets,
        output_queue=queue,
        helius_api_key=Config.HELIUS.API_KEY,
    )

    async def queue_handler() -> None:
        while True:
            new_buy = await queue.get()
            logger.info(f"New buy detected from a target user. {new_buy}")
            try:
                text = prepare_tweet_content(new_buy)
                logger.info("Posting bought token address in tweet ...")
                created = await twitter_client.create_tweet(text=text)  # type: ignore
                logger.info(f"Tweet posted successfully. {created}")

            except Exception as e:
                logger.error(f"Error posting tweet to twitter. {e}", exc_info=True)

    async with asyncio.TaskGroup() as gp:
        gp.create_task(wallets_mon.start())
        gp.create_task(queue_handler())


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

    finally:
        input("Press 'Enter' to close the bot!")
        input("Press 'Enter' once again to close the bot!")
        input("Press 'Enter' last-time to close the bot!")
