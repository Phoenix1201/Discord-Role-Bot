import discord
from discord import app_commands
import os
from dotenv import load_dotenv

from db import *
from utils import *
from embed import create_role_embed
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

    guild_id = str(interaction.guild.id)
    uid = str(interaction.user.id)

    is_op = is_operator(guild_id, uid)
    is_admin = interaction.user.guild_permissions.administrator

    if not (is_op or is_admin):
        await interaction.response.send_message("権限なし", ephemeral=True)
        return

    embed = create_operator_embed(interaction.guild, guild_id)

    is_full_access = is_op

    view = AdminPanelView(guild_id, interaction.guild, is_full_access)
    view.disable_for_non_operator()

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

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

    view = DiceView(entries, gid)
    await interaction.followup.send(embed=embed, file=file, view=view)

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
