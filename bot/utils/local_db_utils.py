import pickle

from bot import bot, local_budb, local_enkadb, local_gdb, local_ndb, local_rdb

from .bot_utils import list_to_str
from .os_utils import file_exists


def load_local_db():
    if file_exists(local_rdb):
        with open(local_rdb, "rb") as file:
            local_dict = pickle.load(file)
        bot.rss_dict.update(local_dict)

    if file_exists(local_gdb):
        with open(local_gdb, "rb") as file:
            local_dict = pickle.load(file)
        bot.gift_dict.update(local_dict)

    if file_exists(local_budb):
        with open(local_budb, "rb") as file:
            local_b_users = pickle.load(file)
        for user in local_b_users:
            if user not in bot.banned:
                bot.banned.append(user)


def save2db_lcl2(db):
    if db is None:
        with open(local_budb, "wb") as file:
            pickle.dump(list_to_str(bot.banned), file)
    elif db == "rss":
        with open(local_rdb, "wb") as file:
            pickle.dump(bot.rss_dict, file)
    elif db == "gift":
        with open(local_gdb, "wb") as file:
            pickle.dump(bot.gift_dict, file)


def load_enka_db():
    if file_exists(local_enkadb):
        with open(local_enkadb, "rb") as file:
            local_dict = pickle.load(file)
        bot.enka_dict.update(local_dict)


def save_enka_db():
    with open(local_enkadb, "wb") as file:
        pickle.dump(bot.enka_dict, file)
