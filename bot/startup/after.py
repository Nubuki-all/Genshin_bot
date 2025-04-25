import signal

import aiohttp

from bot import Message, asyncio, bot, con_ind, conf, jid, sys, version_file
from bot.fun.emojis import enmoji, enmoji2
from bot.fun.quips import enquip2
from bot.utils.gi_utils import enka_update
from bot.utils.local_db_utils import save_enka_db
from bot.utils.log_utils import logger
from bot.utils.msg_utils import send_presence
from bot.utils.os_utils import file_exists, force_exit, touch
from bot.utils.rss_utils import scheduler


async def update_enka_assets():
    if bot.enka_dict.get("Updated"):
        return
    await logger(e=("=" * 30))
    await logger(e="Updating enka assets…")
    await logger(e=("=" * 30))
    await enka_update()
    bot.enka_dict.update({"Updated": True})
    save_enka_db()


async def onrestart():
    try:
        if sys.argv[1] == "restart":
            msg = "*Restarted!*"
        elif sys.argv[1].startswith("update"):
            s = sys.argv[1].split()[1]
            if s == "True":
                with open(version_file, "r") as file:
                    v = file.read()
                msg = f"*Updated to >>>* {v}"
            else:
                msg = "*No major update found!*\n" f"Bot restarted! {enmoji()}"
        else:
            return
        chat_id, msg_id, server = map(str, sys.argv[2].split(":"))
        await bot.client.edit_message(
            jid.build_jid(chat_id, server), msg_id, Message(conversation=msg)
        )
    except Exception:
        await logger(Exception)


async def onstart():
    text = "*Please restart me.*"
    i = conf.OWNER.split()[0]
    await bot.client.send_message(
        jid.build_jid(i),
        text,
    )


async def on_termination():
    try:
        dead_msg = f"*I'm* {enquip2()} {enmoji2()}"
        i = conf.OWNER.split()[0]
        await bot.client.send_message(
            jid.build_jid(i),
            dead_msg,
        )
    except Exception:
        pass
    # More cleanup code?
    await bot.requests.close()
    force_exit()
    # exit()


async def update_presence():
    while True:
        try:
            await send_presence()
            await asyncio.sleep(5)
            await send_presence(False)
        except Exception:
            pass
        await asyncio.sleep(300)


async def wait_for_client():
    while True:
        if await bot.client.is_logged_in:
            break
        await asyncio.sleep(0.5)


async def wait_on_client():
    while True:
        try:
            await onstart()
            break
        except Exception:
            pass
        await asyncio.sleep(1)


async def on_startup():
    try:
        bot.requests = aiohttp.ClientSession(loop=bot.loop)
        for signame in {"SIGINT", "SIGTERM", "SIGABRT"}:
            bot.loop.add_signal_handler(
                getattr(signal, signame),
                lambda: asyncio.create_task(on_termination()),
            )
        await update_enka_assets()
        if not file_exists(con_ind):
            await wait_on_client()
            touch(con_ind)
            await logger(e="Please Restart bot.")
            # re_x()
            bot.me = await bot.client.get_me()
            return
        else:
            await wait_for_client()
            scheduler.start()
        bot.me = await bot.client.get_me()
        if len(sys.argv) == 3:
            await onrestart()
        else:
            await asyncio.sleep(3)
            await onstart()
            # await logger(e="Please Restart bot.")
            # return
        asyncio.create_task(update_presence())
    except Exception:
        await logger(Exception)
