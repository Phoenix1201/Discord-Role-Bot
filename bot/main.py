import discord
from discord import app_commands
import os
from dotenv import load_dotenv

from db import *
from utils import *
from embed import create_role_embed, create_operator_embed
from chart import create_pie_chart

from views.dice import DiceView
from views.admin import AdminPanelView
from views.delete import ConfirmDeleteView
from views.weight import WeightView
from views.toggle import ToggleView

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

dice_running = {}

# =========================
# /admin
# =========================
@tree.command(name="admin", description="管理パネル")
async def admin_panel(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral=True)

    guild_id = str(interaction.guild.id)
    uid = str(interaction.user.id)

    is_op = is_operator(guild_id, uid)
    is_admin = interaction.user.guild_permissions.administrator

    if not (is_op or is_admin):
        await interaction.followup.send("権限なし")
        return

    embed = create_operator_embed(interaction.guild, guild_id)

    is_full_access = is_op

    view = AdminPanelView(guild_id, interaction.guild, is_full_access)
    view.disable_for_non_operator()

    await interaction.followup.send(
        embed=embed,
        view=view
    )
    
# =========================
# /delete
# =========================
@tree.command(name="delete", description="登録削除")
async def delete(interaction: discord.Interaction):

    guild_id = str(interaction.guild.id)
    uid = str(interaction.user.id)

    entries = get_entries(guild_id)

    if uid not in entries:
        await interaction.response.send_message("登録がありません", ephemeral=True)
        return

    entry = entries[uid]

    # 対象ユーザー取得
    member = interaction.guild.get_member(int(entry["target"]))
    if not member:
        try:
            member = await interaction.guild.fetch_member(int(entry["target"]))
        except Exception as e:
            print("fetch_member error:", e)
            member = None

    # 現在の情報表示
    embed = create_role_embed(
        "⚠️ この登録を削除しますか？",
        entry["role_name"],
        entry["color"],
        member
    )

    view = ConfirmDeleteView(guild_id, uid, entry)

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

    view.message = await interaction.original_response()

# =========================
# /dice
# =========================
@tree.command(name="dice", description="抽選")
async def dice(interaction: discord.Interaction):
    gid = str(interaction.guild.id)

    if dice_running.get(gid):
        await interaction.response.send_message("抽選中です", ephemeral=True)
        return

    dice_running[gid] = True

    await interaction.response.defer()

    entries = get_enabled_entries(get_entries(gid))

    if not entries:
        dice_running[gid] = False
        await interaction.followup.send("登録なし")
        return

    img = create_pie_chart(entries)
    file = discord.File(img, filename="chart.png")

    embed = discord.Embed(
        title="🎲 抽選準備",
        description="ボタンを押して抽選！"
    )
    embed.set_image(url="attachment://chart.png")

    view = DiceView(entries, gid, dice_running)
    await interaction.followup.send(embed=embed, file=file, view=view)

# =========================
# /history
# =========================
@tree.command(name="history", description="過去の当選履歴")
async def history(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)

    rows = get_history(guild_id)

    if not rows:
        await interaction.response.send_message("履歴がありません", ephemeral=True)
        return

    embed = discord.Embed(
        title="📜 過去の当選履歴（最新10件）",
        color=discord.Color.gold()
    )

    for i, (uid, role_name) in enumerate(rows, start=1):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"ID:{uid}"

        embed.add_field(
            name=f"{i}. {name}",
            value=role_name,
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)
    
# =========================
# /list
# =========================
@tree.command(name="list", description="登録一覧")
async def list_cmd(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    entries = get_enabled_entries(get_entries(guild_id))

    if not entries:
        await interaction.response.send_message("登録なし", ephemeral=True)
        return

    embed = discord.Embed(title="📋 登録一覧", color=discord.Color.blurple())

    for uid, entry in entries.items():
        try:
            member = interaction.guild.get_member(int(uid)) \
                or await interaction.guild.fetch_member(int(uid))
        except:
            member = None

        name = member.display_name if member else f"ID:{uid}"

        status = "ON" if is_enabled(entry) else "OFF"

        embed.add_field(
            name=name,
            value=f"{entry['role_name']}\n倍率: {entry['weight']:.1f} | {status}",
            inline=False
        )

    embed.set_footer(text=f"登録人数: {len(entries)}人")

    await interaction.response.send_message(embed=embed)

# =========================
# /toggle
# =========================
@tree.command(name="toggle", description="参加ON/OFF")
async def toggle(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    entries = get_entries(guild_id)

    view = ToggleView(entries, guild_id, interaction.guild)

    await interaction.response.send_message(
        "切り替えるユーザーを選択",
        view=view,
        ephemeral=True
    )

# =========================
# /weight
# =========================
@tree.command(name="weight", description="重み変更")
async def weight(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    entries = get_entries(guild_id)

    view = WeightView(entries, guild_id, interaction.guild)

    await interaction.response.send_message(
        "重みを変更するユーザーを選択",
        view=view,
        ephemeral=True
    )

# =========================
# 起動
# =========================
@client.event
async def on_ready():
    os.makedirs("/data", exist_ok=True)
    init_db()
    await tree.sync()
    print("起動完了")

client.run(TOKEN)
