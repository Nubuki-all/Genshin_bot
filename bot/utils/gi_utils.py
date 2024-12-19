import asyncio
import io
import random

import aiohttp
from aiohttp_retry import RandomRetry, RetryClient
from bs4 import BeautifulSoup
from encard import encard, update_namecard
from encard.src.tools import pill
from enkacard import enc_error, encbanner
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .log_utils import logger

uri = "https://genshin-db-api.vercel.app/api/v5/{}?query={}&dumpResult=true"
uri2 = (
    "https://genshin-db-api.vercel.app/api/v5/stats?folder={}&query={}&dumpResult=true"
)


async def get_gi_info(
    folder="characters", query="qiqi", direct=False, stats=False, get=None
):
    url = uri.format(folder, query) if not stats else uri2.format(folder, query)
    if get:
        direct = True
        url = get
    field = "stats" if stats else "result"
    retry_options = RandomRetry(attempts=10)
    client_session = aiohttp.ClientSession()
    retry_requests = RetryClient(client_session)
    async with retry_requests.get(url, retry_options=retry_options) as result:
        if direct:
            info = await result.json()
        else:
            info = (await result.json()).get(field)
    await client_session.close()
    return info


async def async_dl(url):
    retry_options = RandomRetry(attempts=10)
    client_session = aiohttp.ClientSession()
    retry_requests = RetryClient(client_session)
    async with retry_requests.get(url, retry_options=retry_options) as result:
        assert result.status == 200
        raw = await result.content.read()
    await client_session.close()
    return raw


async def enka_update():
    await encbanner.update()
    await update_namecard.update()


async def get_enka_profile(uid, card=False, template=1):
    error = None
    result = None
    try:
        async with encbanner.ENC(uid=uid) as encard:
            result = await encard.profile(card=card, teamplate=template)
    except enc_error.ENCardError as e:
        error = e
    except Exception as e:
        error = e
        await logger(Exception)
    finally:
        return result, error


async def get_enka_card(uid, char_id, akasha=True, huid=False, template=1):
    error = False
    result = None
    try:
        async with encbanner.ENC(
            uid=uid, character_id=str(char_id), hide_uid=huid
        ) as encard:
            result = await encard.creat(akasha=akasha, template=template)
    except enc_error.ENCardError as e:
        error = True
        result = e
    except Exception as e:
        error = True
        result = e
        await logger(Exception)
    finally:
        return result, error


async def get_enka_profile2(uid, huid=False):
    error = result = None
    try:
        async with encard.ENCard(lang="en", hide=huid) as enc:
            result = await enc.create_profile(uid)
    except Exception as e:
        error = True
        result = e
        await logger(Exception)
    finally:
        return result, error


async def get_enka_card2(uid, char_id, huid=False):
    error = result = None
    try:
        async with encard.ENCard(
            lang="en", character_id=str(char_id), hide=huid
        ) as enc:
            result = await enc.create_cards(uid)
    except Exception as e:
        error = True
        result = e
        await logger(Exception)
    finally:
        return result, error

async def fetch_random_boss():
    try:
        boss_list_url = "https://genshin-db-api.vercel.app/api/v5/enemies?query=boss&matchCategories=true&verboseCategories=true"
        monster_list_url = "https://gi.yatta.moe/api/v2/en/monster{}"
        bosses = await get_gi_info(get=boss_list_url)
        boss = random.choice(bosses)
        return await get_gi_info(get=monster_list_url.format(boss.get("id")))
    except Exception:
        await logger(Exception)


async def fetch_random_character(amount=4):
    try:
        character_list_url = "https://genshin-db-api.vercel.app/api/v5/characters?query=boss&matchCategories=true&verboseCategories=true"
        characters = await get_gi_info(get=character_list_url)
        return random.sample(characters, amount)
    except Exception:
        await logger(Exception)


async def fetch_weapon_detail(weapon: dict, weapon_stats: dict) -> tuple:
    name = weapon.get("name")
    des = weapon.get("description")
    rarity = weapon.get("rarity")
    max_level = "90" if rarity > 2 else "70"
    typ = weapon.get("weaponText")
    base_atk = round(weapon.get("baseAtkValue"))
    main_stat = weapon.get("mainStatText", str())
    base_stat = weapon.get("baseStatText", str())
    effect_name = weapon.get("effectName", str())
    effects = weapon.get("effectTemplateRaw", str())
    if effects:
        effects = BeautifulSoup(effects, "html.parser").text
        r1 = weapon["r1"]["values"] if weapon.get("r1") else []
        r2 = weapon["r2"]["values"] if weapon.get("r2") else []
        r3 = weapon["r3"]["values"] if weapon.get("r3") else []
        r4 = weapon["r4"]["values"] if weapon.get("r4") else []
        r5 = weapon["r5"]["values"] if weapon.get("r5") else []
        key = [
            f'*{f"{a}/{b}/{c}/{d}/{e}".split("/None", maxsplit=1)[0]}*'
            for a, b, c, d, e in itertools.zip_longest(r1, r2, r3, r4, r5)
        ]
        effects = effects.format(*key)
    img_suf = weapon["images"]["filename_gacha"]
    img = await add_background(img_suf, rarity, name)
    max_stats = weapon_stats[max_level]
    max_base_atk = round(max_stats.get("attack"))
    max_main_stat = max_stats.get("specialized")
    if main_stat:
        if max_main_stat > 1:
            max_main_stat = round(max_main_stat)
        else:
            max_main_stat = f"{round(max_main_stat * 100)}%"
    caption = f"*{name}*\n"
    caption += f"{'⭐' * rarity}\n\n"
    caption += f"*Rarity:* *{'★' * rarity}*\n"
    caption += f"*Type:* *{typ}*\n"
    caption += f"*Base ATK:* *{base_atk}* ➜ *{max_base_atk}* _(Lvl {max_level})_\n"
    if main_stat:
        caption += (
            f"*{main_stat}:* *{base_stat}* ➜ *{max_main_stat}* _(Lvl {max_level})_\n"
        )
    caption += f"```{(des[:2000] + '…') if len(des) > 2000 else des}```\n\n"
    if effects:
        caption += f"*{effect_name}* +\n"
        caption += f"{effects}"

    return img, caption


color = {
        1: (126, 126, 128, 255),
        2: (78, 126, 110, 255),
        3: (84, 134, 169, 255),
        4: (127, 103, 161, 255),
        5: (176, 112, 48, 255),
    }

async def add_background(image_suf: str, rarity: int, name: str = "weapon"):
    """Fetches image and adds a background.

    Args:
        image_suf: identifier for image.
        rarity: rarity of item
    """
    # Dict for associating rarity with background color

    # Download the image
    image_url = f"https://api.hakush.in/gi/UI/{image_suf}.webp"

    raw = await async_dl(image_url)

    # Create an Image object from the downloaded content
    img = io.BytesIO(raw)
    img = Image.open(img)

    # Create a gold/purple/blue/green/white background image with the same
    # size as the input image
    background = Image.new("RGBA", img.size, color.get(rarity))  # color with alpha

    # Paste the input image onto the background
    background.paste(img, (0, 0), img)

    # Save the output image
    output = io.BytesIO()
    background.save(output, format="png")
    output.name = f"{name}.png"
    return output.getvalue()


async def get_character_image(
    image,
    text,
    rarity: int,
    gap_color: tuple = (200, 200, 200),
    text_color: tuple = (0, 0, 0),
    font_path: str = None,
    font_size: int = 20,
    element: str = None,
    additional_image_size: tuple = (90, 90),
    ):
    try:
        image_url = f"https://api.hakush.in/gi/UI/{image}.webp"
        raw = await async_dl(image_url)
        image_path = io.BytesIO(raw)
        element_url = f"https://api.hakush.in/gi/UI/{element}.webp"
        raw = await async_dl(element_url)
        element_path = io.BytesIO(raw)
        bg_color = color.get(rarity)

        # Create the main background
        rect_width, rect_height = 300, 400
        base = Image.new("RGBA", (rect_width, rect_height), bg_color)
        draw_base = ImageDraw.Draw(base)

        # Load and resize the main image
        img = Image.open(image_path).convert("RGBA")
        square_size = 330
        img_resized = img.resize((square_size, square_size))
        img_x, img_y = (rect_width - square_size) // 2, 0  # Align to top
        base.paste(img_resized, (img_x, img_y), img_resized)

        # Load and paste the additional image at the top-left corner
        if element:
            additional_img = Image.open(element_path).convert("RGBA")
            additional_img_resized = additional_img.resize(additional_image_size)
            base.paste(additional_img_resized, (0, 0), additional_img_resized)

        # Draw the gap at the bottom
        gap_top = img_y + square_size
        gap_bottom = rect_height
        draw_base.rectangle([(0, gap_top), (rect_width, gap_bottom)], fill=gap_color)

        # Add text centered on the gap
        font = ImageFont.truetype(font_path, font_size) if font_path else await pill.get_font(font_size)
        text_width = draw_base.textlength(text, font=font)
        text_x = (rect_width - text_width) // 2
        text_y = gap_top + (gap_bottom - gap_top - font_size) // 2
        draw_base.text((text_x, text_y), text, fill=text_color, font=font)

        # Save the final image
        output = io.BytesIO()
        base.save(output, format="png")
        output.name = f"{text}.png"
        return output
    except Exception as e:
        await logger(Exception)


async def get_challenge_image(
    image: str,
    background: str,
    extra_images_paths: list,
    text: str,
    bottom_text: str,
    font_path: str = None,
    font_size: int = 17
    ):
    try:
        image_url = f"https://api.hakush.in/gi/UI/{image}.webp"
        raw = await async_dl(image_url)
        image_path = io.BytesIO(raw)
        background_url = f"https://api.hakush.in/gi/UI/{background}.webp"
        raw = await async_dl(background_url)
        background_path = io.BytesIO(raw)
        # Open the original image
        img = Image.open(image_path).convert('RGBA')

        # Open the background image
        background = Image.open(background_path)
        if background.mode != 'RGBA':
            background = background.convert('RGBA')

        # Resize and blur the main background image
        background = background.resize((800, 600))  # Fixed size canvas
        background_blurred = background.filter(ImageFilter.GaussianBlur(radius=2))

        # Create the dark blurred background with rounded corners
        dark_bg_width, dark_bg_height = 600, 500
        corner_radius = 40

        # Position the dark blurred background
        dark_bg_x = (background_blurred.width - dark_bg_width) // 2
        dark_bg_y = (background_blurred.height - dark_bg_height) // 2
        
        # Create a new background layer for the dark blurred effect
        dark_bg = Image.new("RGBA", (dark_bg_width, dark_bg_height), (0, 0, 0, 0))
        # Copy and crop the corresponding region from the main blurred background
        cropped_bg = background_blurred.crop(
            (dark_bg_x, dark_bg_y, dark_bg_x + dark_bg_width, dark_bg_y + dark_bg_height)
        )
        
        # Apply an additional blur to this cropped region
        cropped_bg_blurred = cropped_bg.filter(ImageFilter.GaussianBlur(radius=52))
        
        # Create a mask for rounded corners
        mask = Image.new("L", (dark_bg_width, dark_bg_height), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle(
            [(0, 0), (dark_bg_width, dark_bg_height)],
            radius=corner_radius,
            fill=180
        )
        
        # Create the darkened version of the blurred region
        cropped_bg_blurred.paste(cropped_bg_blurred, (0, 0), mask)
        
        # Paste the darkened, blurred, rounded background back onto the main background
        background_blurred.paste(cropped_bg_blurred, (dark_bg_x, dark_bg_y), mask)
		
        # Resize and mask the profile image into a circle
        profile_size = 150
        img_resized = img.resize((profile_size, profile_size))

        mask = Image.new('L', (profile_size, profile_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, profile_size, profile_size), fill=255)

        img_masked = Image.new('RGBA', (profile_size, profile_size))
        img_masked.paste(img_resized, (0, 0), mask=mask)

        # Paste the circular profile onto the dark blurred background
        profile_x = dark_bg_x + (dark_bg_width - profile_size) // 2
        profile_y = dark_bg_y + 20
        background_blurred.paste(img_masked, (profile_x, profile_y), img_masked)

        # Add text below the circular profile
        if text:
            draw_main = ImageDraw.Draw(background_blurred)
            font = ImageFont.truetype(font_path, font_size) if font_path else await pill.get_font(font_size)

            text_bbox = draw_main.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (background_blurred.width - text_width) // 2
            text_y = profile_y + profile_size + 10
            draw_main.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

        # Add "Challengers" text above extra images
        if bottom_text:
            draw_main = ImageDraw.Draw(background_blurred)
            challengers_font_size = font_size + 5
            challengers_font = ImageFont.truetype(font_path, challengers_font_size) if font_path else await pill.get_font(font_size)

            challengers_text_bbox = draw_main.textbbox((0, 0), bottom_text, font=challengers_font)
            challengers_text_width = challengers_text_bbox[2] - challengers_text_bbox[0]
            challengers_text_x = (background_blurred.width - challengers_text_width) // 2
            challengers_text_y = dark_bg_y + dark_bg_height - 160

            draw_main.text((challengers_text_x, challengers_text_y), bottom_text, fill=(255, 255, 255), font=challengers_font)

        # Add extra images with rounded corners, preserving aspect ratio
        small_image_height = 120
        spacing = 20
        total_width = (len(extra_images_paths) - 1) * spacing

        resized_images = []
        for extra_image_path in extra_images_paths[:4]:
            extra_img = Image.open(extra_image_path).convert('RGBA')
            aspect_ratio = extra_img.width / extra_img.height
            resized_width = int(small_image_height * aspect_ratio)
            resized_img = extra_img.resize((resized_width, small_image_height))

            mask = Image.new('L', resized_img.size, 0)
            draw = ImageDraw.Draw(mask)
            corner_radius = 15
            draw.rounded_rectangle([(0, 0), resized_img.size], radius=corner_radius, fill=255)

            rounded_img = Image.new('RGBA', resized_img.size)
            rounded_img.paste(resized_img, (0, 0), mask)
            resized_images.append(rounded_img)
            total_width += resized_width

        start_x = (background_blurred.width - total_width) // 2
        bottom_y = challengers_text_y + 30

        x_offset = start_x
        for rounded_img in resized_images:
            background_blurred.paste(rounded_img, (x_offset, bottom_y), rounded_img)
            x_offset += rounded_img.width + spacing

        # Save the final image
        output = io.BytesIO()
        background_blurred.save(output, format="png")
        output.name = f"{image}.png"
        return output.getvalue()
    except Exception as e:
        await logger(Exception)

