import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import json
import random

# =========================
# データ処理（サーバー対応）
# =========================
def load_data():
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}
    return data

def save_data(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_guild_data(data, guild_id):
    if guild_id not in data:
        data[guild_id] = {"entries": {}, "history": []}
    return data[guild_id]

# =========================
# 重み付き抽選
# =========================
def pick_winner(entries):
    users = list(entries.keys())
    weights = [entries[u].get("weight", 1) for u in users]

    if not users:
        return None

    return random.choices(users, weights=weights, k=1)[0]

# =========================
# Embed生成
# =========================
def create_role_embed(title, role_name, color_code, target=None):
    if color_code:
        try:
            color = discord.Color(int(color_code, 16))
            color_text = f"#{color_code}"
            image_url = f"https://dummyimage.com/100x100/{color_code}/{color_code}.png"
        except:
            color = discord.Color.blurple()
            color_text = "不正"
            image_url = None
    else:
        color = discord.Color.blurple()
        color_text = "未指定"
        image_url = None

    desc = f"ロール名：{role_name}\n色：{color_text}"
    if target:
        desc += f"\n対象：{target}"

    embed = discord.Embed(title=title, description=desc, color=color)

    if image_url:
        embed.set_thumbnail(url=image_url)

    return embed

# =========================
# Discord設定
# =========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

dice_running = False

# =========================
# /role
# =========================
@tree.command(name="role", description="ロール登録")
@app_commands.describe(
    name="ロール名",
    color="カラーコード",
    user="対象ユーザー"
)
async def role(interaction: discord.Interaction, name: str, color: str = None, user: discord.Member = None):

    data = load_data()
    guild_id = str(interaction.guild.id)
    gdata = get_guild_data(data, guild_id)

    uid = str(interaction.user.id)

    if color:
        color = color.replace("#", "")

    target_id = str(user.id) if user else uid

    gdata["entries"][uid] = {
        "role_name": name,
        "color": color,
        "target": target_id,
        "weight": 1,  # ← 固定
        "role_id": gdata["entries"].get(uid, {}).get("role_id")
    }

    save_data(data)

    embed = create_role_embed("✅登録しました", name, color)
    await interaction.response.send_message(embed=embed)

# =========================
# /dice
# =========================
@tree.command(name="delete", description="登録削除")
@app_commands.describe(user="削除対象（管理者のみ）")
async def delete(interaction: discord.Interaction, user: discord.Member = None):

    data = load_data()
    guild_id = str(interaction.guild.id)
    gdata = get_guild_data(data, guild_id)

    uid = str(interaction.user.id)
    is_admin = interaction.user.guild_permissions.administrator

    # ===== 一般ユーザー =====
    if not is_admin:
        if uid not in gdata["entries"]:
            await interaction.response.send_message("登録がありません", ephemeral=True)
            return

        entry = gdata["entries"][uid]

        # ロール削除
        if entry.get("role_id"):
            role = interaction.guild.get_role(entry["role_id"])
            if role:
                try:
                    await role.delete()
                except:
                    pass

        del gdata["entries"][uid]
        save_data(data)

        await interaction.response.send_message("の登録を解除しました", ephemeral=True)
        return

    # ===== 管理者 =====
    if not user:
        await interaction.response.send_message("ユーザー指定して", ephemeral=True)
        return

    target_id = str(user.id)

    if target_id not in gdata["entries"]:
        await interaction.response.send_message("登録なし", ephemeral=True)
        return

    entry = gdata["entries"][target_id]

    if entry.get("role_id"):
        role = interaction.guild.get_role(entry["role_id"])
        if role:
            try:
                await role.delete()
            except:
                pass

    del gdata["entries"][target_id]
    save_data(data)

    await interaction.response.send_message(f"{user.display_name} を削除しました")

# =========================
# /dice
# =========================
@tree.command(name="dice", description="抽選")
async def dice(interaction: discord.Interaction):
    global dice_running

    if dice_running:
        await interaction.response.send_message("抽選中です", ephemeral=True)
        return

    dice_running = True

    try:
        await interaction.response.defer()

        data = load_data()
        guild_id = str(interaction.guild.id)
        gdata = get_guild_data(data, guild_id)

        if not gdata["entries"]:
            await interaction.followup.send("登録なし")
            return

        winner_id = pick_winner(gdata["entries"])
        entry = gdata["entries"][winner_id]

        member = await interaction.guild.fetch_member(int(entry["target"]))

        color = discord.Color(int(entry["color"], 16)) if entry["color"] else discord.Color.default()

        # 旧ロール削除
        if entry.get("role_id"):
            old = interaction.guild.get_role(entry["role_id"])
            if old:
                try:
                    await old.delete()
                except:
                    pass

        # 新規作成
        role = await interaction.guild.create_role(
            name=entry["role_name"],
            color=color
        )

        entry["role_id"] = role.id

        await role.edit(position=interaction.guild.me.top_role.position - 1)
        await member.add_roles(role)

        # =========================
        # 🎯 weight更新（ここ追加）
        # =========================
        for uid, e in gdata["entries"].items():
            if uid == winner_id:
                e["weight"] = 1
            else:
                current = e.get("weight", 1)
                e["weight"] = min(current + 0.5, 5.0)  # 上限5

        # =========================
        # 履歴
        # =========================
        gdata["history"].append({
            "winner_id": winner_id,
            "role_name": entry["role_name"]
        })
        gdata["history"] = gdata["history"][-10:]

        save_data(data)

        embed = create_role_embed(
            "🎲当選！",
            entry["role_name"],
            entry["color"],
            member.display_name
        )
        await interaction.followup.send(embed=embed)

    finally:
        dice_running = False

# =========================
# /list
# =========================
@tree.command(name="list", description="登録一覧")
async def list_roles(interaction: discord.Interaction):
    await interaction.response.defer()

    data = load_data()
    gdata = get_guild_data(data, str(interaction.guild.id))

    embed = discord.Embed(
        title="📋一覧",
        color = discord.Color.blurple()
    )

    for uid, entry in gdata["entries"].items():
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"ID:{uid}"

        weight = entry.get("weight", 1)

        embed.add_field(
            name=name,
            value=f"{entry['role_name']}\n倍率: {weight:.1f}",
            inline=False
        )
    count = len(gdata["entries"])
    embed.set_footer(text=f"登録人数: {count}人" if count else "登録なし")

    await interaction.followup.send(embed=embed)

# =========================
# /history
# =========================
@tree.command(name="history", description="当選履歴")
async def history(interaction: discord.Interaction):
    await interaction.response.defer()

    data = load_data()
    gdata = get_guild_data(data, str(interaction.guild.id))

    desc = ""

    for i, h in enumerate(reversed(gdata["history"]), 1):
        member = interaction.guild.get_member(int(h["winner_id"]))
        name = member.display_name if member else "不明"
        desc += f"{i}. {name} → {h['role_name']}\n"

    embed = discord.Embed(
        title="履歴",
        description=desc,
        color = discord.Color.blurple()
        )
    embed.set_footer(text="直近の10件を表示")
    await interaction.followup.send(embed=embed)

# =========================
# 起動
# =========================
@client.event
async def on_ready():
    await tree.sync()
    print("起動完了")

client.run(TOKEN)
