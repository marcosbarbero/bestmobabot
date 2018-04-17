"""
Arena hero selection logic.
"""

import math
from functools import reduce
from itertools import combinations, permutations
from operator import attrgetter, itemgetter
from typing import Callable, Iterable, List, Tuple, Optional, TypeVar

import numpy

from bestmobabot import constants
from bestmobabot.logger import logger
from bestmobabot.model import Model
from bestmobabot.responses import ArenaEnemy, GrandArenaEnemy, Hero

TArenaEnemy = TypeVar('TArenaEnemy', ArenaEnemy, GrandArenaEnemy)
T = TypeVar('T')
T1 = TypeVar('T1')
T2 = TypeVar('T2')


# Shared for both arenas.
# ----------------------------------------------------------------------------------------------------------------------

def filter_enemies(enemies: Iterable[TArenaEnemy], clan_id: Optional[str]) -> List[TArenaEnemy]:
    return [enemy for enemy in enemies if enemy.user is not None and not enemy.user.is_from_clan(clan_id)]


def naive_select_attackers(heroes: Iterable[Hero]) -> List[Hero]:
    """
    Selects the most powerful heroes.
    """
    return sorted(heroes, key=attrgetter('power'), reverse=True)[:constants.TEAM_SIZE]


# Enemy selection.
# ----------------------------------------------------------------------------------------------------------------------

def select_enemy(model: Model, enemies: Iterable[ArenaEnemy], heroes: Iterable[Hero]) -> Tuple[TArenaEnemy, List[Hero], float]:
    """
    Select enemy and attackers to maximise win probability.
    """
    # noinspection PyTypeChecker
    return max([(enemy, *model_select_attackers(model, heroes, enemy.heroes)) for enemy in enemies], key=itemgetter(2))


def select_grand_enemy(
    model: Model,
    enemies: Iterable[GrandArenaEnemy],
    heroes: Iterable[Hero],
) -> Tuple[GrandArenaEnemy, List[List[Hero]], float]:
    """
    Select enemy and attackers to maximise win probability.
    """
    # noinspection PyTypeChecker
    return max([(enemy, *model_select_grand_attackers(model, heroes, enemy.heroes)) for enemy in enemies], key=itemgetter(2))


# Attackers selection.
# ----------------------------------------------------------------------------------------------------------------------

def model_select_attackers(
    model: Model,
    heroes: Iterable[Hero],
    defenders: Iterable[Hero],
    verbose: bool = True,
) -> Tuple[List[Hero], float]:
    """
    Select attackers for the given enemy to maximise win probability.
    """
    attackers_list = [list(attackers) for attackers in combinations(heroes, constants.TEAM_SIZE)]
    x = numpy.array([make_team_features(attackers) for attackers in attackers_list]) - make_team_features(defenders)
    y: numpy.ndarray = model.estimator.predict_proba(x)[:, 1]
    index: int = y.argmax()
    if verbose:
        logger.debug(f'👊 Win probability: {100.0 * y[index]:.1f}%.')
    return attackers_list[index], y[index]


def model_select_grand_attackers(
    model: Model,
    heroes: Iterable[Hero],
    defenders_teams: Iterable[Iterable[Hero]],
) -> Tuple[List[List[Hero]], float]:
    """
    Select 3 teams of attackers for the given enemy to maximise win probability.
    It's not giving the best solution but it's fast enough.
    """

    defenders_teams = list(defenders_teams)
    selections: List[Tuple[List[List[Hero]], float]] = []

    # Try to form attackers teams in different order and maximise the final probability.
    for order in permutations(range(3)):
        used_heroes = set()
        attackers_teams: List[List[Hero]] = [[], [], []]
        probabilities: List[float] = [0.0, 0.0, 0.0]
        for i in order:
            heroes_left = [hero for hero in heroes if hero.id not in used_heroes]
            attackers, probabilities[i] = model_select_attackers(model, heroes_left, defenders_teams[i], verbose=False)
            attackers_teams[i] = attackers
            used_heroes.update(attacker.id for attacker in attackers)
        p1, p2, p3 = probabilities
        p = p1 * p2 * p3 + p1 * p2 * (1.0 - p3) + p2 * p3 * (1.0 - p1) + p1 * p3 * (1.0 - p2)
        selections.append((attackers_teams, p))

    # Choose best selection.
    attackers_teams, probability = max(selections, key=itemgetter(1))

    logger.debug(f'👊 Win probability: {100.0 * probability:.1f}%.')
    return attackers_teams, probability


# Features construction.
# ----------------------------------------------------------------------------------------------------------------------

def set_heroes_model(model: Model, heroes: Iterable[Hero]):
    """
    Initialize heroes features.
    """
    for hero in heroes:
        hero.set_model(model)


def make_team_features(heroes: Iterable[Hero]) -> numpy.ndarray:
    """
    Build model features for the specified heroes.
    """
    # noinspection PyTypeChecker
    return reduce(numpy.add, (hero.features for hero in heroes))


# Utilities.
# ----------------------------------------------------------------------------------------------------------------------

def secretary_max(items: Iterable[T1], n: int, key: Optional[Callable[[T1], T2]] = None) -> Tuple[T1, T2]:
    """
    Select best item while lazily iterating over the items.
    https://en.wikipedia.org/wiki/Secretary_problem#Deriving_the_optimal_policy
    """
    key = key or (lambda item: item)
    # We want to look at each item only once.
    iterator = iter((item, key(item)) for item in items)
    r = int(n / math.e) + 1
    # Skip first (r - 1) items and remember the maximum.
    _, max_key = max((next(iterator) for _ in range(r - 1)), key=itemgetter(1), default=(None, None))
    # Find the first one that is better or the last one.
    for item, item_key in iterator:  # type: T1, T2
        if max_key is None or item_key > max_key:
            break
    # noinspection PyUnboundLocalVariable
    return item, item_key


def choose_multiple(items: Iterable[T], n: int, k: int) -> Iterable[Tuple[List[T], ...]]:
    """
    Choose n groups of size k.
    """
    if n == 0:
        yield ()
        return
    for head in choose_multiple(items, n - 1, k):
        used_keys = {item.id for sub_items in head for item in sub_items}
        for tail in combinations((item for item in items if item.id not in used_keys), k):
            yield (*head, [*tail])
