import hashlib
import json
import random
import re
import string
from typing import Any, Callable, Iterable, List, Optional, TypeVar

import requests

from bestmobabot.responses import *
from bestmobabot.utils import logger


class ApiError(Exception):
    def __init__(self, name: Optional[str], description: Optional[str]):
        super().__init__(name, description)
        self.name = name
        self.description = description


class AlreadyError(ApiError):
    pass


class InvalidSessionError(ApiError):
    pass


class NotEnoughError(ApiError):
    pass


class InvalidResponseError(ValueError):
    pass


class Api:
    GAME_URL = 'https://vk.com/app5327745'
    IFRAME_URL = 'https://i-heroes-vk.nextersglobal.com/iframe/vkontakte/iframe.new.php'
    API_URL = 'https://heroes-vk.nextersglobal.com/api/'
    USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'

    def __init__(self, remixsid: str):
        self.remixsid = remixsid
        self.auth_token: str = None
        self.user_id: str = None
        self.request_id: int = None
        self.session_id: str = None
        self.session = requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.session.__exit__(exc_type, exc_val, exc_tb)

    def authenticate(self):
        logger.info('🔑 Authenticating…')

        with requests.Session() as session:
            logger.debug('🌎 Loading game page on VK.com…')
            with session.get(Api.GAME_URL, cookies={'remixsid': self.remixsid}) as response:
                response.raise_for_status()
                app_page = response.text

            # Look for params variable in the script.
            match = re.search(r'var params\s?=\s?({[^\}]+\})', app_page)
            assert match, 'params not found'
            params = json.loads(match.group(1))
            for key, value in params.items():
                logger.debug('🔡 %s: %s', key, value)

            # Load the proxy page and look for Hero Wars authentication token.
            logger.debug('🌎 Authenticating in Hero Wars…')
            with session.get(Api.IFRAME_URL, params=params) as response:
                response.raise_for_status()
                iframe_new = response.text
            match = re.search(r'auth_key=([a-zA-Z0-9.\-]+)', iframe_new)
            assert match, f'authentication key is not found: {iframe_new}'
            self.auth_token = match.group(1)

        logger.info('🔑 Authentication token: %s', self.auth_token)
        self.user_id = str(params['viewer_id'])
        self.request_id = 0
        self.session_id = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(14))

    def new_request_id(self) -> int:
        self.request_id += 1
        return self.request_id

    def call(self, name: str, arguments: Optional[Dict[str, Any]] = None, verbose=False):
        request_id = str(self.new_request_id())
        logger.debug('🔔 #%s %s(%r)', request_id, name, arguments or {})

        calls = [{'ident': name, 'name': name, 'args': arguments or {}}]
        data = json.dumps({"session": None, "calls": calls})
        headers = {
            'User-Agent': self.USER_AGENT,
            'X-Auth-Application-Id': '5327745',
            'X-Auth-Network-Ident': 'vkontakte',
            'X-Auth-Session-Id': self.session_id,
            'X-Auth-Session-Key': '',
            'X-Auth-Token': self.auth_token,
            'X-Auth-User-Id': self.user_id,
            'X-Env-Library-Version': '1',
            'X-Env-Referrer': 'unknown',
            'X-Request-Id': request_id,
            'X-Requested-With': 'ShockwaveFlash / 28.0.0.126',
            'X-Server-Time': '0',
        }
        if self.request_id == 1:
            headers['X-Auth-Session-Init'] = '1'
        headers["X-Auth-Signature"] = self.sign_request(data, headers)

        with self.session.post(self.API_URL, data=data, headers=headers) as response:
            response.raise_for_status()
            try:
                result = response.json()
            except ValueError as e:
                result = {}  # just for PyCharm
                raise InvalidResponseError(response.text) from e
        if verbose:
            logger.debug('💬 %s', result)
        if 'results' in result:
            return result['results'][0]['result']['response']
        if 'error' in result:
            raise self.make_exception(result['error'])
        raise ValueError(result)

    @staticmethod
    def sign_request(data: str, headers: dict) -> str:
        fingerprint = ''.join(
            f'{key}={value}'
            for key, value in sorted(
                (key[6:].upper(), value)
                for key, value in headers.items()
                if key.startswith('X-Env')
            )
        )
        data = ':'.join((
            headers['X-Request-Id'],
            headers['X-Auth-Token'],
            headers['X-Auth-Session-Id'],
            data,
            fingerprint,
        )).encode('utf-8')
        return hashlib.md5(data).hexdigest()

    exception_classes = {
        'Already': AlreadyError,
        'common\\rpc\\exception\\InvalidSession': InvalidSessionError,
        'NotEnough': NotEnoughError,
    }

    @classmethod
    def make_exception(cls, error: Dict) -> 'ApiError':
        name = error.get('name')
        description = error.get('description')
        return cls.exception_classes.get(name, ApiError)(name, description)

    TKey = TypeVar('TKey')
    TNamedTuple = TypeVar('TNamedTuple')

    @staticmethod
    def parse_list(items: List[Dict], key: Callable[[Dict], TKey], parse: Callable[[Dict], TNamedTuple]) -> Dict[TKey, TNamedTuple]:
        return {key(item): parse(item) for item in items}

    @staticmethod
    def get_int_id(item: Dict) -> int:
        return int(item['id'])

    @staticmethod
    def get_str_id(item: Dict) -> str:
        return str(item['id'])

    def get_user_info(self) -> UserInfo:
        return UserInfo.parse(self.call('userGetInfo'))

    def farm_daily_bonus(self) -> Reward:
        return Reward.parse(self.call('dailyBonusFarm', {'vip': 0}))

    def list_expeditions(self) -> Dict[int, Expedition]:
        return self.parse_list(self.call('expeditionGet'), self.get_int_id, Expedition.parse)

    def farm_expedition(self, expedition_id: int) -> Reward:
        return Reward.parse(self.call('expeditionFarm', {'expeditionId': expedition_id}))

    def get_all_quests(self) -> Dict[int, Quest]:
        return self.parse_list(self.call('questGetAll'), self.get_int_id, Quest.parse)

    def farm_quest(self, quest_id: QuestId) -> Reward:
        return Reward.parse(self.call('questFarm', {'questId': quest_id}))

    def get_all_mail(self) -> Dict[str, Mail]:
        return self.parse_list(self.call('mailGetAll')['letters'], self.get_str_id, Mail.parse)

    def farm_mail(self, letter_ids: Iterable[int]) -> Dict[str, Reward]:
        response: Dict[str, Dict] = self.call('mailFarm', {'letterIds': list(letter_ids)})
        return {letter_id: Reward.parse(item) for letter_id, item in response.items()}
