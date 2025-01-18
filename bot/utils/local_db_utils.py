import pickle

from bot import bot, local_enkadb, local_gcdb, local_gdb, local_rdb, local_udb

from .os_utils import file_exists


def load_local_db():
    if file_exists(local_gdb):
        with open(local_gdb, "rb") as file:
            local_dict = pickle.load(file)
        bot.gift_dict.update(local_dict)

    if file_exists(local_gcdb):
        with open(local_gcdb, "rb") as file:
            local_dict = pickle.load(file)
        bot.group_dict.update(local_dict)

    if file_exists(local_rdb):
        with open(local_rdb, "rb") as file:
            local_dict = pickle.load(file)
        bot.rss_dict.update(local_dict)

    if file_exists(local_udb):
        with open(local_udb, "rb") as file:
            local_dict = pickle.load(file)
        bot.user_dict.update(local_dict)


def save2db_lcl2(db):
    if db == "gift":
        with open(local_gdb, "wb") as file:
            pickle.dump(bot.gift_dict, file)
    elif db == "groups":
        with open(local_rdb, "wb") as file:
            pickle.dump(bot.group_dict, file)
    elif db == "rss":
        with open(local_rdb, "wb") as file:
            pickle.dump(bot.rss_dict, file)
    elif db is "users":
        with open(local_udb, "wb") as file:
            pickle.dump(bot.user_dict, file)


def load_enka_db():
    if file_exists(local_enkadb):
        with open(local_enkadb, "rb") as file:
            local_dict = pickle.load(file)
        bot.enka_dict.update(local_dict)


def save_enka_db():
    with open(local_enkadb, "wb") as file:
        pickle.dump(bot.enka_dict, file)
