import discord
from utils import normalize_color
from db import get_operators

def create_role_embed(title, role_name, color_code, target_member=None):
    if color_code:
        hex_code = f"{normalize_color(color_code):06x}"
        color = discord.Color(normalize_color(color_code))
        image_url = f"https://dummyimage.com/100x100/{hex_code}/{hex_code}.png"
        color_text = f"#{hex_code}"
    else:
        color = discord.Color.blurple()
        color_text = "未指定"
        image_url = None

    target_text = target_member.display_name if target_member else "未指定"

    embed = discord.Embed(
        title=title,
        description=f"ロール名：{role_name}\n色：{color_text}\n対象：{target_text}",
        color=color
    )

    if image_url:
        embed.set_thumbnail(url=image_url)

    return embed

def create_operator_embed(guild, guild_id):
    ops = get_operators(guild_id)

    desc = ""
    for uid in ops:
        member = guild.get_member(int(uid))
        name = get_display_name(member, uid)
        desc += f"・{name}\n"

    return discord.Embed(
        title="👑 Bot管理者一覧",
        description=desc or "なし",
        color=discord.Color.gold()
    )
