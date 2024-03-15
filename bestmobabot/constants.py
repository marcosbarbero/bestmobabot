from datetime import timedelta
from typing import Dict

# General.
from bestmobabot.enums import DungeonUnitType, LibraryTitanElement

API_TIMEOUT = 10.0
NODEJS_TIMEOUT = 30
DATABASE_NAME = 'db.sqlite3'
ANALYTICS_URL = 'https://www.google-analytics.com/collect'
ANALYTICS_TID = 'UA-65034198-7'
IP_URL = 'https://ipinfo.io/ip'
USER_AGENT = 'titanhunters/119300020 CFNetwork/1492.0.1 Darwin/23.3.0'  # noqa

# Fundamental constants.
TEAM_SIZE = 5  # heroes
N_GRAND_TEAMS = 3
N_GRAND_HEROES = N_GRAND_TEAMS * TEAM_SIZE  # heroes

# Chests control.
MAX_OPEN_ARTIFACT_CHESTS = 10

# Tower control.
TOWER_IGNORED_BUFF_IDS = {13, 14, 15, 17, 18, 19, 23}  # These buffs require a hero ID.

# Arena model training control.
MODEL_SCORING = 'accuracy'
MODEL_SCORING_ALPHA = 0.95
MODEL_N_SPLITS = 5
MODEL_N_ESTIMATORS_CHOICES = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 90, 100]
MODEL_PARAM_GRID = {
    'n_estimators': MODEL_N_ESTIMATORS_CHOICES,
}
MODEL_N_LAST_BATTLES = 20000

# Arena retries.
ARENA_MIN_PROBABILITY = 0.5
ARENA_RETRY_INTERVAL = timedelta(hours=1)

# Raids.
RAID_N_HEROIC_TRIES = 3
RAID_N_STARS = 3

# Offers.
OFFER_FARMED_TYPES = ('dailyReward',)

# Shops.
SHOP_IDS = ('1', '4', '5', '6', '8', '9', '10', '11')

# Logging.
LOGURU_FORMAT = ' '.join((
    '<green>{time:MMM DD HH:mm:ss}</green>',
    '<level>[{level:.1}]</level>',
    '<level>{message}</level>',
))
LOGURU_TELEGRAM_FORMAT = '{message}'
VERBOSITY_LEVELS = {
    0: 'INFO',
    1: 'DEBUG',
}

# FIXME: obtain from the resources: `LIB_ENUM_HEROCOLOR_1`.
COLORS: Dict[int, str] = {
    1: 'White',
     2: 'Green',
     3: 'Green+1',
     4: 'Blue',
     5: 'Blue+1',
     6: 'Blue+2',
     7: 'Purple',
     8: 'Purple+1',
     9: 'Purple+2',
     10: 'Purple+3',
     11: 'Orange',
     12: 'Orange+1',
     13: 'Orange+2',
     14: 'Orange+3',
     15: 'Orange+4',
}

TITAN_ELEMENTS = {
    DungeonUnitType.EARTH: LibraryTitanElement.EARTH,
    DungeonUnitType.FIRE: LibraryTitanElement.FIRE,
    DungeonUnitType.WATER: LibraryTitanElement.WATER,
}
