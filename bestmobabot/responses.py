from datetime import timedelta, timezone
from typing import Any, Dict, List, NamedTuple, Optional

from bestmobabot.types import *


class Response(NamedTuple):
    quests: 'Quests'
    payload: Any

    @staticmethod
    def parse(item: Dict) -> 'Response':
        return Response(
            payload=item['response'],
            quests=list(map(Quest.parse, item.get('quests', []))),
        )


class User(NamedTuple):
    id: UserID
    name: str
    time_zone: timezone
    clan_id: ClanID

    @staticmethod
    def parse(item: Dict) -> 'User':
        return User(
            id=UserID(str(item['id'])),
            name=item['name'],
            time_zone=timezone(timedelta(hours=item.get('timeZone', 0))),
            clan_id=ClanID(str(item.get('clanId'))),
        )


class Expedition(NamedTuple):
    id: ExpeditionID
    status: int

    @staticmethod
    def parse(item: Dict) -> 'Expedition':
        return Expedition(
            id=ExpeditionID(str(item['id'])),
            status=ExpeditionStatus(item['status']),
        )


class Reward(NamedTuple):
    stamina: Stamina
    gold: Gold
    experience: Experience
    consumable: Dict[str, int]
    star_money: StarMoney
    coin: Dict[str, str]
    hero_fragment: Dict[HeroID, int]

    @staticmethod
    def parse(item: Dict) -> 'Reward':
        return Reward(
            stamina=Stamina(item.get('stamina', 0)),
            gold=Gold(item.get('gold', 0)),
            experience=Experience(item.get('experience', 0)),
            consumable=item.get('consumable', {}),
            star_money=StarMoney(item.get('starmoney', 0)),
            coin=item.get('coin', {}),
            hero_fragment=item.get('fragmentHero', {}),
        )


class Quest(NamedTuple):
    id: QuestID
    state: QuestState
    progress: int
    reward: Reward

    @staticmethod
    def parse(item: Dict) -> 'Quest':
        return Quest(
            id=QuestID(str(item['id'])),
            state=QuestState(item['state']),
            progress=item['progress'],
            reward=Reward.parse(item['reward']),
        )


Quests = List[Quest]


class Letter(NamedTuple):
    id: LetterID

    @staticmethod
    def parse(item: Dict) -> 'Letter':
        return Letter(id=LetterID(str(item['id'])))


class Hero(NamedTuple):
    id: HeroID
    level: int
    color: int
    star: int
    power: Optional[int]

    @staticmethod
    def parse(item: Dict) -> 'Hero':
        return Hero(
            id=HeroID(str(item['id'])),
            level=item['level'],
            color=item['color'],
            star=item['star'],
            power=item.get('power'),
        )


class ArenaEnemy(NamedTuple):
    user_id: UserID
    place: str
    heroes: List[Hero]
    power: int
    user: User

    @staticmethod
    def parse(item: Dict) -> 'ArenaEnemy':
        return ArenaEnemy(
            user_id=UserID(str(item['userId'])),
            place=item['place'],
            heroes=list(map(Hero.parse, item['heroes'])),
            power=int(item['power']),
            user=User.parse(item['user']),
        )


class ArenaResult(NamedTuple):
    win: bool

    @staticmethod
    def parse(item: Dict) -> 'ArenaResult':
        return ArenaResult(
            win=item['win'],
        )
