


# Solana-wallets-monitor-bot


The bot to monitor solana wallets for new token buys and post tweet as soon as the new buy is detected!


## Setup Instructions

*   Install python v3.11+.
*   Install required python modules
```
pip install -r requirements.txt
```
*   Rename sample-config.toml file to config.toml.
*   Enter you Twitter Access Keys in config.toml file.
*   Run the once using command 
```
python main.py
``` 
*   It should auto create an input folder with txt files in it.
*   Go to input/tweet-content.txt and put the Tweet content you want to be posted whenever there's a new buy alert is detected.
*   Following is a list of place holders for the Tweet Template:
    ```

COIN_ADDRESS_PLACEHOLDER = "__COIN_ADDRESS__"
COIN_AMOUNT_PLACEHOLDER = "__COIN_AMOUNT__"
COIN_NAME_PLACEHOLDER = "__COIN_NAME__"
COIN_SYMBOL_PLACEHOLDER = "__COIN_SYMBOL__"
TOTLA_USD_PAID_PLACEHOLDER = "__TOTAL_USD_PAID__"
BUYER_WALLET_ADDRESS_PLACEHOLDER = "__BUYER_WALLET_ADDRESS__"
BUYER_NAME_PLACEHOLDER = "__BUYER_NAME___"

    
    ``` 
*   Enter the target solana wallets to be monitored in input/wallets.txt file. One wallet address per line.
*   Finally, run the bot and it should be good to go.
*   In case of issues, contact on [Telegram](https://t.me/runetech).




Telegram: [@runetech](https://t.me/runetech)