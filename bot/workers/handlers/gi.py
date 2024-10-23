from bot.utils.gi_utils import enka_update, get_enka_card, get_enka_profile, get_gi_info
from bot.utils.log_utils import logger
from bot.utils.msg_utils import get_args


async def enka_handler(event, args):
    """
    Get a players's character build card from enka
    Requires character build for the specified uid to be public

    Arguments:
    uid: {genshin player uid} (Required)
    -c or --card {character name}: use quotes if the name has spaces eg:- "Hu tao"; Also supports lookups
    -t <int> {template}: card generation template; currently only two templates exist; default 1
    Flags:
    -p or --profile: To get player card instead
    --hide_uid: Hide uid in card
    --no_top: Remove akasha ranking from card
    --update: update library

    Examples:
    123454697855 -c "Hu tao" -t 2 --hide_uid
        - retrieves the current build for Hu tao from the given uid with uid hidden while using the second template
    123456789 -p -t 2
        - retrieves profile card using the second template for the given uid
    12345678900 -c xq
        - retrieves the current build for whatever matches the character name provided; in this case Xingqui
    """
    error = None
    try:
        arg, args = get_args(
            ["--hide_uid", "store_true"],
            ["--no_top", "store_false"],
            ["--update", "store_true"],
            "-c",
            "--card",
            ["-p", "store_true"],
            ["--profile", "store_true"],
            "-t",
            to_parse=args,
            get_unknown=True,
        )
        card = arg.c or arg.card
        prof = arg.p or arg.profile
        akasha = arg.no_top
        if arg.update:
            await enka_update()
            if not (card or prof):
                return await event.reply("Updated enka assets.")
        if not (card or prof):
            return await event.reply(f"```{enka_handler.__doc__}```")
        if arg.t not in ("1", "2"):
            arg.t = 1
        profile, error = await get_enka_profile(args)
        if error:
            return
        if prof:
            profile, error = await get_enka_profile(args, card=True, template=arg.t)
            if error:
                return
            caption = f"{profile.player.name}'s profile"
            file_name = caption + ".png"
            path = "enka/" + file_name
            profile.card.save(path)
            return await event.reply_file(path, file_name, f"*{caption}*")
        if card:
            info = await get_gi_info(card)
            if not info:
                return await event.reply(
                    f"*Character not found.*\nYou searched for {card}.\nNot what you searched for?\nTry again with double quotes"
                )
            char_id = info.get("id")
            result, error = await get_enka_card(
                args, char_id, akasha=akasha, huid=arg.hide_uid, template=arg.t
            )
            if error:
                return
            caption = f"{profile.player.name}'s {info.get('name')} current build"
            file_name = caption + ".png"
            path = "enka/" + file_name
            result.card[0].card.save(path)
            return await event.reply_file(path, file_name, f"*{caption}*")
    except Exception:
        await logger(Exception)
    finally:
        if error:
            return await event.reply(f"*Error:*\n{error}")
