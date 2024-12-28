import random  # autoflake: skip_file

from .gi_utils import get_all_wep, get_rate_up_weapons


def get_wish_rarity(pity):
    ch_5_str = 0.6
    ch_4_str = 5.1
    ch_3_str = 94.3

    if pity.last_5 >= 74 and pity.last_5 < 90:
        boost = (pity.last_5 - 73) * 6
        ch_3_str -= boost
        ch_5_str += boost

    if pity.last_5 == 90:
        ch_5_str = 100
        ch_4_str = 0
        ch_3_str = 0
    elif pity.last_4 == 10 or (pity.last_5 == 89 and pity.last_4 == 9):
        ch_5_str = 0
        ch_4_str = 100
        ch_3_str = 0

    rarities = [3, 4, 5]
    weight = [ch_3_str, ch_4_str, ch_5_str]
    return random.choices(rarities, weights=weight, k=1)[0]


def get_4_star_type():
    type_ = ["character", "weapon"]
    weight = [65, 33]
    return random.choices(type_, weights=weight, k=1)[0]


def get_4_star_rate_up(pity):
    rate_u = 50
    stnd = 50
    if pity.r4_rate_up:
        rate_u = 100
        stnd = 0
    type_ = [True, False]
    weight = [rate_u, stnd]
    return random.choices(type_, weights=weight, k=1)[0]


class Wishes:
    def __init__(self):
        self.pity = self.Pity()
        self.pulls = []
        self.total_pulls = 0

    class Pity:
        def __init__(self):
            self.last_5 = 0
            self.last_4 = 0
            self.r4_rate_up = None

        def update(self):
            self.last_5 += 1
            self.last_4 += 1
            if self.r4_rate_up is not None:
                self.r4_rate_up = not self.r4_rate_up



async def pull(wish: Wish, multi=False):
    if not multi:
        wish.pity.update()
        rarity = get_wish_rarity(wish.pity)
        if rarity == 3:
            weapons = await get_all_wep(rarity)
            weapon = random.choice(weapons)
            return weapon
        if rarity == 4:
            type_ = get_4_star_type()
            weapons = await get_all_wep(rarity)
            
            
