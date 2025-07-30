import asyncio
import datetime
import itertools
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from hashlib import sha256

import aiohttp
import pytz
import requests
from ffmpeg.asyncio import FFmpeg

from bot import LOGS, bot, telegraph_errors, time

THREADPOOL = ThreadPoolExecutor(max_workers=1000)


def gfn(fn):
    "gets module path"
    return ".".join([fn.__module__, fn.__qualname__])


async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future


def create_api_token(retries=10):
    telgrph_tkn_err_msg = "Couldn't not successfully create telegraph api token!."
    while retries:
        try:
            bot.tgp_client.create_api_token("Rss")
            break
        except (requests.exceptions.ConnectionError, ConnectionError) as e:
            retries -= 1
            if not retries:
                LOGS.info(telgrph_tkn_err_msg)
                break
            time.sleep(1)
    return retries


async def post_to_tgph(title, text, author: str = None, author_url: str = None):
    bot.author = (await bot.client.get_me()).PushName if not bot.author else bot.author
    retries = 10
    while retries:
        try:
            page = await sync_to_async(
                bot.tgp_client.post,
                title=title,
                author=(author or bot.author),
                author_url=(author_url or bot.author_url),
                text=text,
            )
            return page
        except telegraph_errors.APITokenRequiredError as e:
            result = await sync_to_async(create_api_token)
            if not result:
                raise e
        except (requests.exceptions.ConnectionError, ConnectionError) as e:
            retries -= 1
            if not retries:
                raise e
            await asyncio.sleep(1)


def list_to_str(lst: list, sep=" ", start: int = None, md=True):
    string = str()
    t_start = start if isinstance(start, int) else 1
    for i, count in zip(lst, itertools.count(t_start)):
        if start is None:
            string += str(i) + sep
            continue
        entry = f"`{i}`"
        string += f"{count}. {entry} {sep}"

    return string.rstrip(sep)


def split_text(text: str, split="\n", pre=False, list_size=4000):
    current_list = ""
    message_list = []
    for string in text.split(split):
        line = string + split if not pre else split + string
        if len(current_list) + len(line) <= list_size:
            current_list += line
        else:
            # Add current_list to account_list
            message_list.append(current_list)
            # Reset the current_list with a new "line".
            current_list = line
    # Add the last line into list.
    message_list.append(current_list)
    return message_list


async def get_json(link):
    async with aiohttp.ClientSession() as requests:
        result = await requests.get(link)
        return await result.json()


async def get_text(link):
    async with aiohttp.ClientSession() as requests:
        result = await requests.get(link)
        return await result.text()


tz = pytz.timezone("Africa/Lagos")


def get_timestamp(date: str):
    return (
        datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=tz)
        .timestamp()
    )


def get_date(value, start=False):
    if len(value.split()) == 3:
        index = len(value) // 2
        return value[:index] if start else value[index:]
    else:
        if start:
            if len(value.split()[0]) == 10:
                index = 19
                add_v = str()
            else:
                index = 10
                add_v = " 00:00:00"
            return value[:index] + add_v
        else:
            if len(value.split()[1]) == 8:
                index = 10
                add_v = str()
            else:
                index = 19
                add_v = " 00:00:00"
            return value[index:] + add_v


def get_date_from_ts(timestamp):
    try:
        date = datetime.datetime.fromtimestamp(timestamp, tz)
        return date.strftime("%d %b %Y %I:%M %p")
    except Exception:
        return 0


def time_formatter(seconds: float) -> str:
    """humanize time"""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + "d, ") if days else "")
        + ((str(hours) + "h, ") if hours else "")
        + ((str(minutes) + "m, ") if minutes else "")
        + ((str(seconds) + "s, ") if seconds else "")
    )
    return tmp[:-2]


async def png_to_jpg(png: bytes | str):
    raw = False if isinstance(png, str) else True
    ffmpeg = (
        FFmpeg()
        .option("y")
        .input("pipe:0" if raw else png)
        .output(
            "pipe:1",
            f="mjpeg",
        )
    )
    input_ = png if raw else None
    return await ffmpeg.execute(input_)


def turn(turn_id: str = None):
    if turn_id:
        return turn_id in bot.p_queue
    return bot.p_queue


async def wait_for_turn(turn_id: str):
    while turn(turn_id):
        await asyncio.sleep(5)
        if bot.p_queue[0] == turn_id:
            return 1


def waiting_for_turn():
    return turn() and len(turn()) > 1


def get_sha256(string: str):
    return sha256(string.encode("utf-8")).hexdigest()


def trunc_string(string: str, limit: int):
    return (string[: limit - 2] + "…") if len(string) > limit else string


def split_list_in_half(list_: list):
    return (list_[: len(list_) // 2], list_[len(list_) // 2 :])


async def read_binary(file):
    def stdlib_read(file):
        with open(file, "rb") as f:
            return f.read()

    return await sync_to_async(stdlib_read, file)


async def write_binary(file, bytes_):
    def stdlib_write(file, bytes_):
        with open(file, "wb") as f:
            f.write(bytes_)

    return await sync_to_async(stdlib_write, file, bytes_)
