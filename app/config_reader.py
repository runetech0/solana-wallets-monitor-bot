from dataclasses import dataclass

import toml

_CONFIG_FILE = 'config.toml'
_CONFIG_DATA = toml.load(_CONFIG_FILE)

@dataclass
class TWITTER:
    API_KEY: str = ''
    API_KEY_SECRET: str = ''
    API_ACCESS_TOKEN: str = ''
    API_ACCESS_TOKEN_SECRET: str = ''

@dataclass
class HELIUS:
    API_KEY: str = ''

class Config:
    TWITTER: 'TWITTER'
    HELIUS: 'HELIUS'

    @classmethod
    def load(cls) -> None:
        cls.TWITTER = TWITTER(
            API_KEY=_CONFIG_DATA['TWITTER']['API_KEY'],
            API_KEY_SECRET=_CONFIG_DATA['TWITTER']['API_KEY_SECRET'],
            API_ACCESS_TOKEN=_CONFIG_DATA['TWITTER']['API_ACCESS_TOKEN'],
            API_ACCESS_TOKEN_SECRET=_CONFIG_DATA['TWITTER']['API_ACCESS_TOKEN_SECRET']
        )
        cls.HELIUS = HELIUS(
            API_KEY=_CONFIG_DATA['HELIUS']['API_KEY']
        )

Config.load()
