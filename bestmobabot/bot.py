import heapq
from datetime import datetime, time
from operator import attrgetter
from time import sleep
from typing import Callable, Tuple

from bestmobabot.api import AlreadyError, Api, InvalidResponseError, InvalidSessionError
from bestmobabot.responses import *
from bestmobabot.utils import logger

TAction = Callable[..., Any]
TQueueItem = Tuple[datetime, int, TAction, Tuple]


class Bot:
    DEFAULT_INTERVAL = timedelta(days=1)
    FARM_MAIL_INTERVAL = timedelta(hours=6)
    ARENA_INTERVAL = timedelta(minutes=288)

    EXPEDITION_COLLECT_REWARD = ExpeditionStatus(2)
    EXPEDITION_FINISHED = ExpeditionStatus(3)

    QUEST_IN_PROGRESS = QuestState(1)
    QUEST_COLLECT_REWARD = QuestState(2)

    AS_SOON_AS_POSSIBLE = datetime.fromtimestamp(0, timezone.utc)

    @staticmethod
    def start(api: Api) -> 'Bot':
        return Bot(api, api.get_user_info())

    def __init__(self, api: Api, user_info: User):
        self.api = api
        self.user_info = user_info
        self.queue: List[TQueueItem] = []
        self.action_counter = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.api.__exit__(exc_type, exc_val, exc_tb)

    def run(self):
        logger.info('🤖 Scheduling initial actions.')

        # Stamina quests depend on player's time zone.
        self.schedule(self.alarm_time(time(hour=9, minute=30), self.user_info.time_zone), self.farm_quests)
        self.schedule(self.alarm_time(time(hour=14, minute=30), self.user_info.time_zone), self.farm_quests)
        self.schedule(self.alarm_time(time(hour=21, minute=30), self.user_info.time_zone), self.farm_quests)

        # Other quests are simultaneous for everyone. Day starts at 4:00 UTC.
        self.schedule(self.alarm_time(time(hour=3, minute=59), timezone.utc), self.farm_expeditions)
        self.schedule(self.alarm_time(time(hour=19, minute=39), timezone.utc, self.ARENA_INTERVAL), self.attack_arena)
        self.schedule(self.alarm_time(time(hour=8, minute=0), timezone.utc), self.farm_daily_bonus)
        self.schedule(self.alarm_time(time(hour=8, minute=15), timezone.utc), self.buy_chest)
        self.schedule(self.alarm_time(time(hour=8, minute=30), timezone.utc, self.FARM_MAIL_INTERVAL), self.farm_mail)
        self.schedule(self.alarm_time(time(hour=8, minute=45), timezone.utc), self.send_daily_gift)

        logger.info('🤖 Running action queue.')
        while self.queue:
            when, _, action, args = heapq.heappop(self.queue)  # type: TQueueItem
            sleep_timedelta = when - datetime.now(timezone.utc)
            sleep_duration = sleep_timedelta.total_seconds()
            if sleep_duration > 0.0:
                logger.info('💤 Next action %s%s in %s at %s', action.__name__, args, sleep_timedelta, when)
                sleep(sleep_duration)
            try:
                action(when, *args)
            except InvalidSessionError:
                logger.warning('😱 Invalid session.')
                self.api.authenticate()
                self.schedule(self.AS_SOON_AS_POSSIBLE, action, *args)
            except AlreadyError:
                logger.info('🤔 Already done.')
            except InvalidResponseError as e:
                logger.error('😱 API returned something bad: %s', e)
            except Exception as e:
                logger.error('😱 Uncaught error.', exc_info=e)

        logger.fatal('🏳 Action queue is empty.')

    @staticmethod
    def alarm_time(time_: time, time_zone: timezone, interval=DEFAULT_INTERVAL) -> datetime:
        now = datetime.now(time_zone).replace(microsecond=0)
        dt = now.replace(hour=time_.hour, minute=time_.minute, second=time_.second)
        while dt < now:
            dt += interval
        return dt

    def schedule(self, when: datetime, action: TAction, *args: Any):
        self.action_counter += 1
        when = when.astimezone()
        logger.debug('⏰ Schedule %s%s at %s', action.__name__, args, when)
        heapq.heappush(self.queue, (when, self.action_counter, action, args))

    def farm_daily_bonus(self, when: datetime):
        logger.info('💰 Farming daily bonus.')
        try:
            reward = self.api.farm_daily_bonus()
            logger.info('📈 %s', reward)
        finally:
            self.schedule(when + self.DEFAULT_INTERVAL, self.farm_daily_bonus)

    def farm_expeditions(self, when: datetime):
        logger.info('💰 Farming expeditions.')
        try:
            expeditions = self.api.list_expeditions()
            for expedition in expeditions:
                if expedition.status == self.EXPEDITION_COLLECT_REWARD:
                    reward = self.api.farm_expedition(expedition.id)
                    logger.info('📈 %s', reward)
        finally:
            self.schedule(when + self.DEFAULT_INTERVAL, self.farm_expeditions)

    def farm_quests(self, when: datetime):
        logger.info('💰 Farming quests.')
        try:
            self._farm_quests(self.api.get_all_quests())
        finally:
            self.schedule(when + self.DEFAULT_INTERVAL, self.farm_quests)

    def _farm_quests(self, quests: List[Quest]):
        for quest in quests:
            if quest.state == self.QUEST_COLLECT_REWARD:
                logger.info('📈 %s', self.api.farm_quest(quest.id))

    def farm_mail(self, when: datetime):
        logger.info('💰 Farming mail')
        try:
            letters = self.api.get_all_mail()
            if not letters:
                return
            rewards = self.api.farm_mail(int(letter.id) for letter in letters)
            for reward in rewards.values():
                logger.info('📈 %s', reward)
        finally:
            self.schedule(when + self.FARM_MAIL_INTERVAL, self.farm_mail)

    def buy_chest(self, when: datetime):
        logger.info('📦 Buy chest.')
        try:
            for reward in self.api.buy_chest():
                logger.info('📈 %s', reward)
        finally:
            self.schedule(when + self.DEFAULT_INTERVAL, self.buy_chest)

    def send_daily_gift(self, when: datetime):
        logger.info('🎁 Send daily gift.')
        try:
            self._farm_quests(self.api.send_daily_gift(['15664420', '209336881']))
        finally:
            self.schedule(when + self.DEFAULT_INTERVAL, self.send_daily_gift)

    def attack_arena(self, when: datetime):
        logger.info('👊 Attack arena.')
        try:
            enemy = min([
                enemy
                for enemy in self.api.find_arena_enemies()
                if not self.user_info.clan_id or self.user_info.clan_id != enemy.user.clan_id
            ], key=attrgetter('power'))
            heroes: List[Hero] = sorted(self.api.get_all_heroes(), key=attrgetter('power'), reverse=True)[:5]
            result, quests = self.api.attack_arena(enemy.user.id, [hero.id for hero in heroes])
            logger.info('👊 Win? %s', result.win)
            self._farm_quests(quests)
        finally:
            self.schedule(when + self.ARENA_INTERVAL, self.attack_arena)
