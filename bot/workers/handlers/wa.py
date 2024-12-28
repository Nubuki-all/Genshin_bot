import io
import random

import torch
from clean_links.clean import clean_url
from PIL import Image
from RealESRGAN import RealESRGAN
from urlextract import URLExtract

from bot.config import bot
from bot.fun.quips import enquip, enquip4
from bot.fun.stickers import ran_stick
from bot.utils.log_utils import logger
from bot.utils.msg_utils import (
    clean_reply,
    download_replied_media,
    get_args,
    pm_is_allowed,
    user_is_allowed,
    user_is_owner,
)


async def sticker_reply(event, args, client):
    """
    Sends a random sticker upon being tagged
    """
    try:
        if event.type != "text":
            return
        if not event.text.startswith("@"):
            return
        me = await bot.client.get_me()
        if not event.text.startswith("@" + me.JID.User):
            return
        await event.send_typing_status()
        random_sticker = ran_stick()
        await clean_reply(
            event,
            event.reply_to_message,
            "reply_sticker",
            random_sticker,
            quote=True,
            name=random.choice((enquip(), enquip4())),
            packname=me.PushName,
        )
        await event.send_typing_status(False)
    except Exception:
        await logger(Exception)


async def sanitize_url(event, args, client):
    """
    Checks and sanitizes all links in replied message

    Can also receive a link as argument
    """
    status_msg = None
    user = event.from_user.id
    if not user_is_owner(user):
        if not pm_is_allowed(event):
            return
        if not user_is_allowed(user):
            return
    try:
        if not (event.quoted_text or args):
            return await event.reply(f"{sanitize_url.__doc__}")
        status_msg = await event.reply("Please wait…")
        extractor = URLExtract()
        if event.quoted_text:
            msg = event.quoted_text
            urls = extractor.find_urls(msg)
            if not urls:
                return await event.reply(
                    f"*No link found in @{event.reply_to_message.from_user.id}'s message to sanitize*"
                )
            new_msg = msg
            sanitized_links = []
            for url in urls:
                sanitized_links.append(clean_url(url))
            for a, b in zip(urls, sanitized_links):
                new_msg = new_msg.replace(a, b)
            return await clean_reply(event, event.reply_to_message, "reply", new_msg)
        urls = extractor.find_urls(args)
        if not urls:
            return await event.reply(f"*No link found in your message to sanitize*")
        msg = "*Sanitized link(s):*"
        for url in urls:
            msg += f"\n\n{url}"
        return await clean_reply(event, event.reply_to_message, "reply", msg)
    except Exception:
        await logger(Exception)
    finally:
        if status_msg:
            await status_msg.delete()


async def stickerize_image(event, args, client):
    """
    Turns replied image to sticker.
    Args:
        Name of sticker
    """
    max_sticker_filesize = 512000
    user = event.from_user.id
    if not user_is_owner(user):
        if not pm_is_allowed(event):
            return
        if not user_is_allowed(user):
            return
    try:
        if args:
            arg, args = get_args(
                ["-f", "store_false"],
                to_parse=args,
                get_unknown=True,
            )
            forced = arg.f
        else:
            forced = True
        rate = ""
        trim = False
        m_type = "image"
        quoted_msg = event.quoted.quotedMessage
        if not quoted_msg.imageMessage.URL:
            if not quoted_msg.videoMessage.URL:
                return await event.reply("*Replied message is not an image.*")
            m_type = "video"
            if (seconds := quoted_msg.videoMessage.seconds) > 6:
                rate = max_sticker_filesize // 6
                trim = True if forced else False
            else:
                rate = max_sticker_filesize // seconds
            rate = f"{rate}k"
        forced = False if m_type == "image" else forced
        await event.send_typing_status()
        file = await download_replied_media(event.quoted, mtype=m_type)
        me = await bot.client.get_me()
        return await event.reply_sticker(
            file,
            quote=True,
            name=(args or random.choice((enquip(), enquip4()))),
            packname=me.PushName,
            animated=trim,
            bitrate=rate,
            enforce_not_broken=forced,
        )
        await event.send_typing_status(False)
    except Exception:
        await logger(Exception)


async def upscale_image(event, args, client):
    """
    Upscales replied image.
    Args:
        None yet.
    """
    status_msg = None
    user = event.from_user.id
    if not user_is_owner(user):
        if not pm_is_allowed(event):
            return
        if not user_is_allowed(user):
            return
    try:
        if bot.disable_cic:
            return await event.reply("*CPU heavy commands are currently disabled.*")
        quoted_msg = event.quoted.quotedMessage
        if not quoted_msg.imageMessage.URL:
            return await event.reply(
                "*Command can only be used when replying to an image.*"
            )
        status_msg = await event.reply("*Please wait…*")
        file = await download_replied_media(event.quoted, mtype="image")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model = RealESRGAN(device, scale=4)
        model.load_weights("weights/RealESRGAN_x4.pth", download=True)

        image = Image.open(io.BytesIO(file)).convert("RGB")
        sr_image = model.predict(image)
        output = io.BytesIO()
        sr_image.save(output, format="png")
        output.name = f"upscaled_image.png"
        await event.reply_photo(output.getvalue())
    except Exception as e:
        await logger(Exception)
        await status_msg.edit(f"*Error:*\n{e}")
        status_msg = None
    finally:
        if status_msg:
            await status_msg.delete()


async def pick_random(event, args, client):
    """
    A randomizer;
    Select a random or multiple random values from a list (replied message).
    Arguments:
        -a: Amount of values to select
        -m: Message header for returned values; can add without specifying -m
        -s: Change delimiter, default="\\n" (new lines)

    """
    try:
        if not event.quoted_text:
            return await event.reply(
                "*Reply to a message with list of items to choose from.*"
            )
        arg, args = get_args(
            "-a",
            "-m",
            "-s",
            to_parse=(args or str()),
            get_unknown=True,
        )
        items = event.quoted_text.split((arg.s or "\n"))
        if len(items) < 2:
            return await event.reply("I need more options to choose from.")
        if arg.a:
            if not arg.a.isdigit():
                return await event.reply("-a: value has to be a digit.")
            arg.a = int(arg.a)
        args = arg.m or args
        out = random.sample(items, (arg.a or 1))
        msg = list_items(out, (args or "*Selected:*"))
        await event.reply(msg)
    except Exception:
        await logger(Exception)


def list_items(items, ini):
    msg = f"{ini}\n"
    for item in items:
        msg += f"*⁍* {item.strip()}\n"
    return msg
