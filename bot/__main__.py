from bot.utils.os_utils import re_x

from . import (
    LOGS,
    ConnectedEv,
    DisconnectedEv,
    LoggedOutEv,
    MessageEv,
    NewAClient,
    PairStatusEv,
    asyncio,
    bot,
    conf,
    time,
    traceback,
)
from .startup.after import on_startup
from .utils.events import POLL, Event, event_handler, on_message
from .utils.os_utils import re_x
from .utils.sudo_button_utils import poll_as_button_handler
from .workers.handlers.dev import bash, eval_message, get_logs
from .workers.handlers.gi import (
    enka_handler,
    get_events,
    getgiftcodes,
    random_challenge,
    weapon_handler,
)
from .workers.handlers.manage import (
    ban,
    disable,
    enable,
    pause_handler,
    restart_handler,
    rss_handler,
    sudoers,
    unban,
    update_handler,
)
from .workers.handlers.stuff import getcmds, getmeme, hello, up
from .workers.handlers.wa import sanitize_url


@bot.client.event(ConnectedEv)
async def on_connected(_: NewAClient, __: ConnectedEv):
    bot.is_connected = True


@bot.client.event(PairStatusEv)
async def on_paired(_: NewAClient, __: PairStatusEv):
    LOGS.info(PairStatusEv)


@bot.client.event(LoggedOutEv)
async def on_logout(_: NewAClient, __: LoggedOutEv):
    LOGS.info("Bot has been logged out.")
    LOGS.info("Restarting…")
    time.sleep(10)
    re_x()


@bot.client.event(DisconnectedEv)
async def _(_: NewAClient, __: DisconnectedEv):
    if not bot.is_connected:
        LOGS.info("Restarting…")
        time.sleep(1)
        re_x()


@bot.register("start")
async def _(client: NewAClient, message: Event):
    await event_handler(message, hello)


@bot.register("pause")
async def _(client: NewAClient, message: Event):
    await event_handler(message, pause_handler)


@bot.register("logs")
async def _(client: NewAClient, message: Event):
    await event_handler(message, get_logs)


@bot.register("eval")
async def _(client: NewAClient, message: Event):
    await event_handler(message, eval_message, bot.client, require_args=True)


@bot.register("bash")
async def _(client: NewAClient, message: Event):
    await event_handler(message, bash, require_args=True)


@bot.register("enka")
async def _(client: NewAClient, message: Event):
    await event_handler(message, enka_handler, require_args=False)


@bot.register("weapon")
async def _(client: NewAClient, message: Event):
    await event_handler(message, weapon_handler, require_args=True)


@bot.register("meme")
async def _(client: NewAClient, message: Event):
    await event_handler(message, getmeme)


@bot.register("cmds")
async def _(client: NewAClient, message: Event):
    await event_handler(message, getcmds)


@bot.register("codes")
async def _(client: NewAClient, message: Event):
    await event_handler(message, getgiftcodes)


@bot.register("events")
async def _(client: NewAClient, message: Event):
    await event_handler(message, get_events)


@bot.register("sanitize")
async def _(client: NewAClient, message: Event):
    await event_handler(message, sanitize_url)


@bot.register("rchallenge")
async def _(client: NewAClient, message: Event):
    await event_handler(message, random_challenge)


@bot.register("rss")
async def _(client: NewAClient, message: Event):
    await event_handler(message, rss_handler, require_args=True)


@bot.register("ban")
async def _(client: NewAClient, message: Event):
    await event_handler(message, ban)


@bot.register("unban")
async def _(client: NewAClient, message: Event):
    await event_handler(message, unban)


@bot.register("ping")
async def _(client: NewAClient, message: Event):
    await event_handler(message, up)


@bot.register("update")
async def _(client: NewAClient, message: Event):
    await event_handler(message, update_handler)


@bot.register("restart")
async def _(client: NewAClient, message: Event):
    await event_handler(message, restart_handler)


@bot.register("sudo")
async def _(client: NewAClient, message: Event):
    await event_handler(message, sudoers, bot.client)


@bot.register("disable")
async def _(client: NewAClient, message: Event):
    await event_handler(message, disable, bot.client)


@bot.register("enable")
async def _(client: NewAClient, message: Event):
    await event_handler(message, enable, bot.client)


@bot.register(POLL)
async def _(client: NewAClient, message: Event):
    await poll_as_button_handler(message)


@bot.client.event(MessageEv)
async def _(client: NewAClient, message: MessageEv):
    await on_message(client, message)


########### Start ############


async def start_bot():
    try:
        asyncio.create_task(on_startup())
        (
            await bot.client.PairPhone(conf.PH_NUMBER, show_push_notification=True)
            if conf.PH_NUMBER
            else await bot.client.connect()
        )
        await bot.client.connect_task
    except Exception:
        LOGS.critical(traceback.format_exc())
        LOGS.critical("Cannot recover from error, exiting…")
        exit()


bot.client.event_loop.run_until_complete(start_bot())
