async def fetch_events(api_url: str, wiki_url: str):
    """Fetch event data from API and Wiki."""
    api_response, wiki_page = await asyncio.gather(
        get_gi_info(get=api_url), get_text(wiki_url)
    )
    events = api_response.get("events", [])
    soup = BeautifulSoup(wiki_page, "html.parser")
    tables = soup.find_all("table", class_="wikitable sortable")
    
    current_events = parse_table_items(tables[0])
    upcoming_events = parse_table_items(tables[1], is_upcoming=True)
    
    return events, current_events, upcoming_events


def parse_table_items(table, is_upcoming=False):
    """Parse event table items."""
    items = table.find_all("td")
    temp_dict = {}
    parsed_list = []

    for item in items:
        if value := item.find("img"):
            temp_dict.update({"name": value.get("alt")})
            link = value.get("src", "")
            if link.startswith("data"):
                link = value.get("data-src", "")
            if link:
                index = link.find(".png")
                link = link[: index + 4]
            temp_dict.update({"link": link})
        elif value := item.get("data-sort-value"):
            svalue = get_timestamp(value[: len(value) // 2])
            evalue = get_timestamp(value[len(value) // 2 :])
            temp_dict.update({"start_time": svalue, "end_time": evalue})
        else:
            value = item.getText()
            temp_dict.update({"type_name": value})
            if is_upcoming:
                temp_dict["upcoming"] = True
            parsed_list.append({temp_dict["name"]: temp_dict})
            temp_dict = {}

    return parsed_list


def merge_events(event_list, current_events, upcoming_events):
    """Merge events from API with current and upcoming events."""
    event_dict = {list(e.keys())[0]: e for e in event_list}
    current_dict = {list(c.keys())[0]: c for c in current_events}
    upcoming_dict = {list(u.keys())[0]: u for u in upcoming_events}

    for name, data in current_dict.items():
        if name in event_dict:
            event_dict[name][name].update(data[name])
        else:
            event_dict[name] = data

    for name, data in upcoming_dict.items():
        if name in event_dict:
            if "end_time" in event_dict[name][name]:
                data[name].pop("upcoming", None)
            event_dict[name][name].update(data[name])
        else:
            event_dict[name] = data

    return list(event_dict.values())


def format_event_message(event):
    """Format a single event message."""
    dict_ = list(event.values())[0]
    msg_parts = [f"*{dict_['name']}*", f"*Type:* {dict_['type_name']}"]

    if desc := dict_.get("description"):
        desc = desc.encode().decode("unicode_escape") if "\\n" in desc else desc
        msg_parts.append(f"*Description:* {desc}")

    if rewards := get_rewards(dict_.get("rewards", [])):
        msg_parts.append(f"*Rewards:* {rewards}")

    msg_parts.append(f"*Start date:* {get_date_from_ts(dict_['start_time'])}")
    msg_parts.append(f"*End date:* {get_date_from_ts(dict_['end_time'])}")

    time_left = (
        dict_["start_time"] - time.time()
        if dict_.get("upcoming")
        else dict_["end_time"] - time.time()
    )
    time_label = "Starts in:" if dict_.get("upcoming") else "Time left:"
    msg_parts.append(f"*{time_label}* *{time_formatter(time_left)}*")

    return "\n\n".join(msg_parts)


async def send_event_list(event, event_list, verbose=False):
    """Send formatted event list."""
    if verbose:
        for e in event_list:
            msg = format_event_message(e)
            link = list(e.values())[0].get("link")
            if link:
                await clean_reply(event, event.reply_to_message, "reply_photo", photo=link, caption=msg)
            else:
                await clean_reply(event, event.reply_to_message, "reply", msg)
            await asyncio.sleep(3)
    else:
        msg = "*List of Current & Upcoming Events:*"
        for e in event_list:
            msg += "\n\n" + format_event_message(e)
        await event.reply(msg)


async def get_events(event, args, client):
    """Main function to fetch, process, and send events."""
    if not user_is_owner(event.from_user.id):
        if not pm_is_allowed(event) or not user_is_allowed(event.from_user.id):
            return

    status = await event.reply("*Fetching events…*")
    api_url = "https://api.ennead.cc/mihoyo/genshin/calendar"
    wiki_url = "https://genshin-impact.fandom.com/wiki/Event"

    try:
        event_list, current_events, upcoming_events = await fetch_events(api_url, wiki_url)
        merged_events = merge_events(event_list, current_events, upcoming_events)

        await status.edit("*Listing Current & Upcoming Events…*")
        await send_event_list(event, merged_events, verbose=(args == "-v"))
    except Exception as e:
        await logger(f"Error fetching events: {e}")
    finally:
        await asyncio.sleep(3)
        await status.delete()


def get_rewards(rewards):
    return ", ".join(
        [f"{reward['name']} x {reward['amount']}" for reward in rewards if reward.get("name")]
    )
