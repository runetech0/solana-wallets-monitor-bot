


# Solana-wallets-monitor-bot


The bot to monitor solana wallets for new token buys and post tweet as soon as the new buy is detected!


## Setup Instructions

*   Install python v3.11+.
*   Install required modules using `pip install -r requirements.txt` command.
*   Rename sample-config.toml file to config.toml.
*   Enter you Twitter Access Keys in config.toml file.
*   Run the once using command `python main.py` and it should auto create an input folder with txt files in it.
*   Go to input/tweet-content.txt and put the Tweet content you want to be posted whenever there's a new buy alert is detected. Make sure to type __ADDRESS__ in the tweet content template as a place-holder for the actuall token address to be replaced by the bot. 
*   Enter the target solana wallets to be monitored in input/wallets.txt file. One wallet address per line.
*   Finally, run the bot and it should be good to go.
*   In case of issues, contact on [Telegram](https://t.me/runetech).




Telegram: [@runetech](https://t.me/runetech)