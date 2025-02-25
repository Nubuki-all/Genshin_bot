import asyncio
import time
import uuid
from inspect import getdoc

from bs4 import BeautifulSoup

from bot.config import bot
from bot.utils.bot_utils import (
    get_date_from_ts,
    get_json,
    get_text,
    get_timestamp,
    split_list_in_half,
    time_formatter,
)
from bot.utils.db_utils import save2db2
from bot.utils.gi_utils import (
    enka_update,
    fetch_random_boss,
    fetch_random_character,
    fetch_weapon_detail,
    get_challenge_image,
    get_character_image,
    get_character_info_fallback,
    get_enka_card,
    get_enka_card2,
    get_enka_card3,
    get_enka_profile,
    get_enka_profile2,
    get_gi_info,
)
from bot.utils.log_utils import logger
from bot.utils.msg_utils import (
    chat_is_allowed,
    clean_reply,
    construct_msg_and_evt,
    get_args,
    get_msg_from_codes,
    get_user_info,
    sanitize_text,
    user_is_allowed,
    user_is_privileged,
)
from bot.utils.os_utils import s_remove
from bot.utils.sudo_button_utils import create_sudo_button, wait_for_button_response


async def enka_handler(event, args, client):
    """
    Get a players's character build card from enka
    Requires character build for the specified uid to be public

    Arguments:
        uid/@mention: {genshin player uid} (Required)
        -c or --card or --character {character name}*: use quotes if the name has spaces eg:- "Hu tao"; Also supports lookups
        -cs or --cards or --characters {characters} same as -c but for multiple characters; delimited by commas
        -t <int> {template}: card generation template; currently only two templates exist; default 1
    Flags:
        -v2: Get cards in new template
        -v3: Get cards in (another) new template
        -d or --dump: Dump all character build from the given uid
        -ls or --list: List all currently showcased characters
        -p or --profile: To get player card instead (v3 not supported)
        -f or --delete: Forget your uid
        -s or --save: Remember your uid
        -huid or --hide_uid: Hide uid in card
        --no_top: Remove akasha ranking from card
        --update: update library

    Examples:
    123454697855 -c "Hu tao" -v2 --hide_uid
        - retrieves the current build for Hu tao from the given uid with uid hidden while using the new template
    123456789 -p -v3
        - retrieves profile card using the new template for the given uid
    12345678900 -c xq
        - retrieves the current build for whatever matches the character name provided; in this case Xingqui
    *Now supports last three digits of character id too
    """
    error = None
    status = None
    user = event.from_user.id
    if not user_is_privileged(user):
        if not chat_is_allowed(event):
            return
        if not user_is_allowed(user):
            return await event.react("⛔")
    try:
        arg, unknown = get_args(
            ["--hide_uid", "store_true"],
            ["--no_top", "store_false"],
            ["--update", "store_true"],
            "-c",
            "-cs",
            "--card",
            "--cards",
            "--character",
            "--characters",
            ["-d", "store_true"],
            ["--dump", "store_true"],
            ["-huid", "store_true"],
            ["-p", "store_true"],
            ["--profile", "store_true"],
            ["-v2", "store_true"],
            ["-v3", "store_true"],
            ["-ls", "store_true"],
            ["--list", "store_true"],
            ["-s", "store_true"],
            ["--save", "store_true"],
            ["-f", "store_true"],
            ["--delete", "store_true"],
            "-t",
            to_parse=args or str(),
            get_unknown=True,
        )
        unknowns = unknown.split()
        invalid = str()
        mention = str()
        uid = None
        for unkwn in unknowns:
            if unkwn.isdigit() and not uid:
                uid = unkwn
                continue
            elif (unkwn.startswith("@") and unkwn[1:].isdigit()) and not mention:
                mention = unkwn
                continue
            invalid += f"{unkwn} "
        invalid = invalid.rstrip()
        card = arg.c or arg.card or arg.character
        cards = arg.cs or arg.cards or arg.characters
        dump = arg.d or arg.dump
        hide_uid = arg.huid or arg.hide_uid
        list_ = arg.ls or arg.list
        prof = arg.p or arg.profile
        akasha = arg.no_top
        reply = event.reply_to_message
        delete = arg.f or arg.delete
        save = arg.s or arg.save
        vital_args = bool(card or cards or dump or prof or list_)
        if arg.update:
            u_reply = await event.reply("*Updating enka assets…*")
            await enka_update()
            if not vital_args:
                return await u_reply.edit("Updated enka assets.")
            await u_reply.delete()
        if mention and uid:
            await event.reply("Ignoring your mention…")
        elif mention:
            mentioned = await get_user_info(mention[1:])
            not_found_err = "*No idea who {} is.*"
            if not mentioned.Found:
                return await event.reply(not_found_err.format(mention))
        if uid and save:
            will_save = True
            if bot.user_dict.get(user, {}).get("genshin_uid") == uid:
                await event.reply(f"*Warning:* This uid has already been saved")
                will_save = False
            elif prev_uid := bot.user_dict.get(user, {}).get("genshin_uid"):
                await event.reply(
                    f"*Info:* Overwriting previously saved uid: {prev_uid} with: {uid}…"
                )
            if will_save:
                bot.user_dict.setdefault(user, {}).update(genshin_uid=uid)
                await save2db2(bot.user_dict, "users")
                await event.reply("*Saved your uid successfully!*")
            if not vital_args:
                return
        if not uid:
            uid = bot.user_dict.get((mention[1:] or user), {}).get("genshin_uid", None)
        if delete:
            if not (saved_uid := bot.user_dict.get(user, {}).get("genshin_uid")):
                await event.reply("*No saved uid was found to delete!*")
            else:
                bot.user_dict.setdefault(user, {}).update(genshin_uid=None)
                await save2db2(bot.user_dict, "users")
                await event.reply(f"*Saved UID: {saved_uid} has been deleted!*")
            if not vital_args:
                return
        if uid and not vital_args:
            if invalid:
                await event.reply(f"*{invalid}?*")
            await enka_button_handler(event, uid, client)
            return
        if not vital_args:
            return await event.reply(getdoc(enka_handler))
        if not uid:
            if invalid:
                await event.reply(f"*{invalid}?*")
            if mention:
                err_msg = f"*Error:* {mention} hasn't saved their uid!"
            else:
                err_msg = "*Please supply a UID*"
            return await event.reply(err_msg)
        if invalid:
            await event.reply(f"*Warning:* No idea what '{invalid}' means.")
        if arg.t not in ("1", "2"):
            arg.t = 1
        profile, error = await get_enka_profile(uid)
        if error:
            result = profile
            return
        if list_:
            characters = list_characters(profile.characters.character_name)
            await event.reply(characters)
            if not (card or cards or dump or prof):
                return
        status_msg = "*Fetching card(s)"
        status_msg += f" for {mentioned.PushName}" if mention else str()
        status_msg += ", Please Wait…*"
        status = await event.reply(status_msg)
        if prof:
            cprofile, error = (
                await get_enka_profile(uid, card=True, template=arg.t, huid=hide_uid)
                if not arg.v2
                else await get_enka_profile2(uid, huid=hide_uid)
            )
            if error:
                return
            caption = f"{profile.player.name}'s profile"
            file_name = caption + ".png"
            path = "enka/" + file_name
            cprofile.card.save(path)
            await clean_reply(
                event, reply, "reply_photo", photo=path, caption=f"*{caption}*"
            )
            return s_remove(path)
        if card:
            info = await get_gi_info(query=card)
            if not info:
                (
                    await status.edit(
                        f"Character with name; *{card}* not found.\nTrying workaround…"
                    )
                    if not card.isdigit()
                    else None
                )
                info = (
                    await get_character_info_fallback(card)
                    if card.casefold() != "traveler"
                    else info
                )
            if not info:
                return await event.reply(
                    f"*Character not found.*\nYou searched for {card}.\nNot what you searched for?\nTry again with double quotes"
                )
            char_id = info.get("id")
            if arg.v2:
                result, error = await get_enka_card2(uid, char_id, hide_uid)
            elif arg.v3:
                result, error = await get_enka_card3(uid, char_id, hide_uid)
            else:
                result, error = await get_enka_card(
                    uid, char_id, akasha=akasha, huid=hide_uid, template=arg.t
                )
            if error:
                return
            caption = f"{profile.player.name}'s current {info.get('name')} build"
            file_name = caption + ".png"
            path = "enka/" + file_name
            if not result.card:
                error = True
                characters = list_characters(profile.characters.character_name)
                result = f"*{card} not found in showcase!*"
                result += f"\n\n{characters}" if characters else str()
                return
            result.card[0].card.save(path)
            await clean_reply(
                event, reply, "reply_photo", photo=path, caption=f"*{caption}*"
            )
            return s_remove(path)
        if cards:
            ids = str()
            errors = str()
            for name in cards.split(","):
                name = name.strip()
                info = await get_gi_info(query=name)
                info = (
                    await get_character_info_fallback(name)
                    if not info and name.casefold() != "traveler"
                    else info
                )
                if not info:
                    errors += f"{name}, "
                    continue
                char_id = info.get("id")
                ids += f"{char_id},"
            errors = errors.strip(", ")
            error_txt = f"*Character(s) not found.*\nYou searched for {errors}.\nNot what you searched for?\nTry again with double quotes"
            if not ids:
                return await event.reply(error_txt)
            ids = ids.strip(",")
            if arg.v2:
                result, error = await get_enka_card2(uid, ids, huid=hide_uid)
            elif arg.v3:
                result, error = await get_enka_card3(uid, ids, huid=hide_uid)
            else:
                result, error = await get_enka_card(
                    uid, ids, akasha=akasha, huid=hide_uid, template=arg.t
                )
            if error:
                return

            if errors:
                await event.reply(error_txt)

            if not result.card:
                error = True
                characters = list_characters(profile.characters.character_name)
                result = f"*{cards} not found in showcase!*"
                result += f"\n\n{characters}" if characters else str()
                return
            return await send_multi_cards(event, reply, result, profile)
        if dump:
            if arg.v2:
                result, error = await get_enka_card2(uid, str(), huid=hide_uid)
            elif arg.v3:
                result, error = await get_enka_card3(uid, str(), huid=hide_uid)
            else:
                result, error = await get_enka_card(
                    uid, None, akasha=akasha, huid=hide_uid, template=arg.t
                )
            if error:
                return
            return await send_multi_cards(event, reply, result, profile)
    except Exception:
        await logger(Exception)
        await event.react("❌")
    finally:
        if status:
            await status.delete()
        if error:
            return await event.reply(f"*Error:*\n{result or error}")


async def send_multi_cards(event, reply, results, profile):
    chain = event
    for card in results.card:
        # print(card.name)  # best debugger?
        caption = f"{profile.player.name}'s current {card.name} build"
        file_name = caption + ".png"
        path = "enka/" + file_name
        card.card.save(path)
        chain = await clean_reply(
            chain, reply, "reply_photo", photo=path, caption=f"*{caption}*"
        )
        reply = None
        await asyncio.sleep(3)
        s_remove(path)


def list_characters(characters):
    msg = "*List of Characters in Showcase:*\n"
    for character in characters:
        msg += f"*⁍* {character}\n"
    return msg


async def enka_button_handler(event, uid, client):
    profile, error = await get_enka_profile(uid)
    if error:
        return await event.reply(f"*Error:*\n{profile or error}")
    button_dict = {}
    button_dict2 = {}
    characters = profile.characters.character_name
    characters2 = []
    user = event.from_user.id
    if len(characters) > 12:
        characters, characters2 = split_list_in_half(characters)
    for char_name in characters:
        if not char_name:
            continue
        button_dict.update({uuid.uuid4(): [char_name, char_name]})
    cfm_btn = "confirm_button"
    cfm_btn_txt = "Next" if characters2 else "Done"
    button_dict.update({uuid.uuid4(): [cfm_btn_txt, cfm_btn]})
    for char_name in characters2:
        if not char_name:
            continue
        button_dict2.update({uuid.uuid4(): [char_name, char_name]})
    if button_dict2:
        button_dict2.update({uuid.uuid4(): ["Done", cfm_btn]})
    title = "Select the characters you want to fetch cards for and click Next/Done."
    poll_msg_, msg_id = await create_sudo_button(
        title, button_dict, event.chat.jid, user, 2, cfm_btn_txt
    )
    poll_msg = construct_msg_and_evt(
        event.chat.id, bot.me.JID.User, msg_id, None, event.chat.server, poll_msg_
    )
    if not (results := await wait_for_button_response(msg_id)):
        return await event.reply("yikes.")
    await poll_msg.delete()
    sel_char = str()
    for result in results:
        char = button_dict.get(result)[1]
        if char == cfm_btn:
            continue
        sel_char += char + ","
    if button_dict2:
        poll_msg_, msg_id = await create_sudo_button(
            title, button_dict2, event.chat.jid, user, 2, "Done"
        )
        poll_msg = construct_msg_and_evt(
            event.chat.id, bot.me.JID.User, msg_id, None, event.chat.server, poll_msg_
        )
        if not (results := await wait_for_button_response(msg_id)):
            return await event.reply("yikes.")
        await poll_msg.delete()
        for result in results:
            char = button_dict2.get(result)[1]
            if char == cfm_btn:
                continue
            sel_char += char + ","
    if not sel_char:
        return await event.reply(getdoc(enka_handler))
    else:
        sel_char = sel_char.rstrip(",")
    return await enka_handler(event, f"--characters {sel_char}", client)


async def weapon_handler(event, args, client):
    """
    Fetch specified genshin weapon details;
    Args:
        Name of weapon.
    """
    status = None
    user = event.from_user.id
    if not user_is_privileged(user):
        if not chat_is_allowed(event):
            return
        if not user_is_allowed(user):
            return await event.react("⛔")
    try:
        reply = event.reply_to_message
        status = await event.reply(f"*Fetching weapon details for {args}…*")
        weapon = await get_gi_info("weapons", args)
        if not weapon:
            await status.edit(f"*Weapon not found.*\nYou searched for *{args}*.")
            status = None
            return
        weapon_stats = await get_gi_info("weapons", args, stats=True)
        await status.edit(f"*Building weapon card for {weapon.get('name')}…*")
        pic, caption = await fetch_weapon_detail(weapon, weapon_stats)
        await clean_reply(event, reply, "reply_photo", photo=pic, caption=caption)
    except Exception as e:
        await logger(Exception)
        await event.react("❌")
        await status.edit(f"*Error:*\n{e}")
        status = None
    finally:
        if status:
            await asyncio.sleep(5)
            await status.delete()


async def manage_autogift_chat(event, args, client):
    user = event.from_user.id
    if not user_is_privileged(user):
        return await event.react("🚫")
    try:
        msg = str()
        arg = args.split(maxsplit=1)
        if len(arg) == 1:
            if arg[0] != "-get":
                return
            if not bot.gift_dict["chats"]:
                msg = "No chat set!"
                return
            msg = list_to_str(bot.gift_dict["chats"], sep=", ")
            return
        else:
            if not arg[0] in ("-add", "-rm"):
                return
        if arg[1] == ".":
            arg[1] = f"{event.chat.id}:{event.chat.server}"
        elif arg[1].casefold() == "default":
            arg[1] = None
        if arg[0] == "-add":
            if arg[1] in bot.gift_dict["chats"]:
                msg = "*Chat already added!*"
                return
            bot.gift_dict["chats"].append(arg[1])
            await save2db2(bot.gift_dict, "gift")
            msg = f"*{arg[1] or 'default'}* has been added."
            return
        if arg[0] == "-rm":
            if not arg[1] in bot.gift_dict["chats"]:
                msg = "*Given chat was never added!*"
                return
            bot.gift_dict["chats"].remove(arg[1])
            await save2db2(bot.gift_dict, "gift")
            msg = f"*{arg[1] or 'default'}* has been removed."
            return
    except Exception:
        await logger(Exception)
        await event.react("❌")
    finally:
        if msg:
            await event.reply(msg)


async def getgiftcodes(event, args, client):
    """
    Fetches a lastest genshin giftcodes
    Uses hoyo-codes.seria.moe

    Arguments:
        -add
        -rm
        -get
     add, remove and get chats for auto giftcodes
    """
    if args:
        return await manage_autogift_chat(event, args, client)
    user = event.from_user.id
    if not user_is_privileged(user):
        if not chat_is_allowed(event):
            return
        if not user_is_allowed(user):
            return await event.react("⛔")
    link = "https://hoyo-codes.seria.moe/codes?game=genshin"
    try:
        reply = await event.reply("*Fetching latest giftcodes…*")
        result = await get_json(link)
        msg = get_msg_from_codes(result.get("codes"))
        await event.reply(msg)
        await asyncio.sleep(5)
        await reply.delete()
    except Exception as e:
        await logger(Exception)
        return await event.reply(f"*Error:*\n{e}")


async def send_verbose_event(event_list, event, reply):
    chain = event
    for e in event_list:
        await event.send_typing_status()
        name = list(e.keys())[0]
        dict_ = e.get(name)
        if dict_["end_time"] < time.time():
            continue
        link = dict_.get("link")
        msg = f"*{dict_['name']}*"
        msg += f"\n\n*Type:* {dict_['type_name']}"
        if desc := dict_.get("description"):
            if "\\n" in desc:
                desc = desc.encode().decode("unicode_escape")
        msg += f"\n\n*Description:* {desc}" if desc else str()
        msg += (
            f"\n\n*Rewards:* {get_rewards(dict_['rewards'])}"
            if get_rewards(dict_.get("rewards", []))
            else str()
        )
        msg += f"\n\n*Start date:* {get_date_from_ts(dict_['start_time'])}"
        msg += f"\n*End date:* {get_date_from_ts(dict_['end_time'])}"
        if dict_.get("upcoming") or dict_["start_time"] > time.time():
            strt = "Starts in:"
            tl = dict_["start_time"] - time.time()
        else:
            strt = "Time left:"
            tl = dict_["end_time"] - time.time()
        msg += f"\n\n*{strt}* *{time_formatter(tl)}*"
        await event.send_typing_status(False)
        if link:
            chain = await clean_reply(
                chain,
                reply,
                "reply_photo",
                photo=link,
                caption=msg,
            )
        else:
            chain = await clean_reply(chain, reply, "reply", msg)
        reply = None
        await asyncio.sleep(3)


async def get_events(event, args, client):
    """
    Get a list of current and upcoming genshin events
    Argument:
        -v: Get events with images
    """
    status = None
    user = event.from_user.id
    if not user_is_privileged(user):
        if not chat_is_allowed(event):
            return
        if not user_is_allowed(user):
            return await event.react("⛔")
    try:
        status = await event.reply("*Fetching events…*")
        api = "https://api.ennead.cc/mihoyo/genshin/calendar"
        link = "https://genshin-impact.fandom.com/wiki/Event"
        await event.send_typing_status()
        response = await get_gi_info(get=api)
        events = response.get("events")
        web = await get_text(link)
        soup = BeautifulSoup(web, "html.parser")
        tables = soup.find_all("table", class_="wikitable sortable")
        current_list = []
        upcoming_list = []
        event_list = []
        temp_dict = {}
        # Build initially event list
        if events:
            for event_ in events:
                event_list.append({event_.get("name"): event_})

        # Get Current Events
        items = tables[0].find_all("td")
        for item in items:
            if value := item.find("img"):
                temp_dict.update({"name": item.getText()})
                link = value.get("src", str())
                if link.startswith("data"):
                    link = value.get("data-src", str())
                if link:
                    index = link.find(".png")
                    link = link[: index + 4]
                temp_dict.update({"link": link})
            elif value := item.get("data-sort-value"):
                svalue = get_timestamp(value[: len(value) // 2])
                evalue = get_timestamp(value[len(value) // 2 :])
                temp_dict.update({"start_time": svalue})
                temp_dict.update({"end_time": evalue})
            else:
                value = item.getText()
                temp_dict.update({"type_name": value})
                current_list.append({temp_dict.get("name"): temp_dict})
                temp_dict = {}

        # Get Upcoming Events
        items = tables[1].find_all("td")
        for item in items:
            if value := item.find("img"):
                temp_dict.update({"name": value.get("alt")})
                link = value.get("src", str())
                if link.startswith("data"):
                    link = value.get("data-src", str())
                if link:
                    index = link.find(".png")
                    link = link[: index + 4]
                temp_dict.update({"link": link})
            elif value := item.get("data-sort-value"):
                svalue = get_timestamp(value[: len(value) // 2])
                evalue = get_timestamp(value[len(value) // 2 :])
                temp_dict.update({"start_time": svalue})
                temp_dict.update({"end_time": evalue})
            else:
                value = item.getText()
                temp_dict.update({"type_name": value, "upcoming": True})
                upcoming_list.append({temp_dict.get("name"): temp_dict})
                temp_dict = {}

        # Compare and combine events from different sources
        for e in event_list:
            name = list(e.keys())[0]
            for l in upcoming_list:
                if wiki_ver := l.get(name):
                    if e[name].get("end_time"):
                        wiki_ver.pop("upcoming")
                    e[name].update(wiki_ver)
                    continue
            for c in current_list:
                if wiki_ver := c.get(name):
                    e[name].update(wiki_ver)
                    continue

        for c in current_list:
            name = list(c.keys())[0]
            present = False
            for e in event_list:
                if e.get(name):
                    present = True
            if not present:
                event_list.append(c)

        await event.send_typing_status(False)
        await status.edit("*Listing Current & Upcoming Events…*")

        if args == "-v":
            return await send_verbose_event(event_list, event, event.reply_to_message)

        await event.send_typing_status()
        msg = "*List of Current & Upcoming Events:*"
        for e in event_list:
            name = list(e.keys())[0]
            dict_ = e.get(name)
            if dict_["end_time"] < time.time():
                continue
            msg += f"\n\n*⁍ {dict_['name']}*"
            msg += f"\n*Type:* {dict_['type_name']}"
            if desc := dict_.get("description"):
                if "\\n" in desc:
                    desc = desc.encode().decode("unicode_escape")
            msg += f"\n{desc}" if desc else str()
            msg += (
                f"\n*Rewards:* {get_rewards(dict_['rewards'])}"
                if get_rewards(dict_.get("rewards", []))
                else str()
            )
            msg += f"\nStart date: {get_date_from_ts(dict_['start_time'])}"
            msg += f"\nEnd date: {get_date_from_ts(dict_['end_time'])}"
            if dict_.get("upcoming") or dict_["start_time"] > time.time():
                strt = "Starts in:"
                tl = dict_["start_time"] - time.time()
            else:
                strt = "Time left:"
                tl = dict_["end_time"] - time.time()
            msg += f"\n*{strt}* *{time_formatter(tl)}*"
        await event.send_typing_status(False)
        await event.reply(msg)
    except Exception:
        await logger(Exception)
        await event.react("❌")
        await status.edit(f"*Error:*\n{e}")
        status = None
    finally:
        if status:
            await asyncio.sleep(3)
            await status.delete()


def get_stuff(name):
    msg = str()
    for thing in something:
        msg += thing[name]
        msg += ", "
    return msg.strip(", ")


def get_rewards(rewards):
    msg = str()
    for reward in rewards:
        msg += reward["name"]
        msg += f" x {reward['amount']}" if reward["amount"] else str()
        msg += ", "
    return msg.strip(", ")


async def random_challenge(event, args, client):
    """
    Generates a completely random boss challenge;
    Argument:
        A character to guarantee inclusion in challenge.
    """
    e = None
    spec_char = None
    status = None
    user = event.from_user.id
    if not user_is_privileged(user):
        if not chat_is_allowed(event):
            return
        if not user_is_allowed(user):
            return await event.react("⛔")
    try:
        reply = event.reply_to_message
        status = await event.reply(
            "*Generating random challenge:*\nFetching random boss…"
        )
        boss = await fetch_random_boss()
        if not boss:
            e = "Couldn't fetch boss"
            return
        boss_name = boss["data"]["name"]
        await status.edit(
            f"*Generating random challenge:*\nFetching random boss: *{boss_name}*\nFetching random characters…"
        )
        if args:
            spec_char = await get_gi_info(query=args)
            if not spec_char:
                await event.reply(f"*Character with name '{args}' not found.*")
                await status.edit("*Retrying…*")
                return await random_challenge(event, None, client)
            other_chars = await fetch_random_character(3, exclude=spec_char)
            (characters := [spec_char]).extend(other_chars)
        else:
            characters = await fetch_random_character()
        if not characters:
            e = "Couldn't fetch characters"
            return
        func_list = []
        await status.edit(
            f"*Generating random challenge:*\nFetching random boss: *{boss_name}*\nFetching random characters images…"
        )
        for character in characters:
            image = character["images"]["filename_icon"]
            text = character["name"]
            rarity = character["rarity"]
            element = (
                character["elementText"] if character["elementText"] != "None" else None
            )
            func = get_character_image(image, text, rarity, element=element)
            func_list.append(func)
        characters_img = await asyncio.gather(*func_list)
        await status.edit(f"*Generating random challenge card…*")
        boss_type = boss["data"]["type"]
        icon = boss["data"]["icon"]
        boss_spec = boss["data"]["specialName"]
        if boss["data"]["tips"]:
            tutorial_desc = list(boss["data"]["tips"].values())[0]["description"]
            tutorial_desc = sanitize_text(tutorial_desc, truncate=False)
            tutorial_img = list(boss["data"]["tips"].values())[0]["images"][0]
        else:
            tutorial_desc = None
            tutorial_img = None
        final_img = await get_challenge_image(
            icon, tutorial_img, characters_img, boss_name, bottom_text="Challengers"
        )
        if not final_img:
            e = "Couldn't generate card"
            return

        caption = f"*Boss name:* {boss_name}"
        caption += f"\n*{boss_spec}*"
        caption += f"\n*Boss type:* {boss_type.rstrip('s') if not boss_type.endswith('ss') else boss_type}"
        if tutorial_desc:
            caption += f"\n> {tutorial_desc}"
        caption += f"\n\n"
        caption += f"*Allowed characters:*"
        for character in characters:
            caption += f"\n*⁍* {character['name']}"
            if spec_char and spec_char["name"] == character["name"]:
                caption += " _(fixed)_"
        caption += "\n\n*Rules:*"
        caption += "\n*1.* Characters can only be substituted for another when you don't have that character."
        caption += "\n*2.* Only a character can be substituted. if you don't have two or more of the randomized characters, try again."
        caption += "\n*3.* The substitute must share the same element and the same or lower rarity as the substituted character."
        caption += "\n*Good luck!*"
        await clean_reply(event, reply, "reply_photo", photo=final_img, caption=caption)
    except Exception as err:
        await logger(Exception)
        await event.react("❌")
        await status.edit(f"*Error:*\n{err}")
        status = None
    finally:
        if e:
            await event.reply(e)
        if status:
            await asyncio.sleep(3)
            await status.delete()
