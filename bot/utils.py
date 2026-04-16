import discord

MAX_WEIGHT = 3.0

def is_enabled(entry):
    return entry.get("enabled", 1) == 1


def get_enabled_entries(entries):
    return {
        uid: e for uid, e in entries.items()
        if is_enabled(e)
    }


async def get_member_safe(guild: discord.Guild, uid: str):
    member = guild.get_member(int(uid))
    if member:
        return member

    try:
        return await guild.fetch_member(int(uid))
    except:
        return None


def get_display_name(member, uid: str):
    return member.display_name if member else f"ID:{uid}"


def normalize_color(code: str) -> int:
    try:
        if not code:
            return 0x5865F2
        code = code.replace("#", "")
        if len(code) != 6:
            return 0x5865F2
        return int(code, 16)
    except:
        return 0x5865F2
