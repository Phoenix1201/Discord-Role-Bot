import discord
from discord import app_commands
import os
from dotenv import load_dotenv

from db import *
from utils import *
from embed import create_role_embed, create_operator_embed
from chart import create_pie_chart

from views.admin import AdminPanelView, AdminListView
from views.confirm import ConfirmView
from views.delete import ConfirmDeleteView
from views.dice import DiceView
from views.history import HistoryView

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

    view = AdminPanelView(guild_id, interaction.guild)

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

    # グラフと同じ順番
    sorted_entries = sorted(
        entries.items(),
        key=lambda x: x[1]["weight"],
        reverse=True
    )

    desc = "ボタンを押して抽選！\n\n"

    for i, (uid, e) in enumerate(sorted_entries, start=1):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"ID:{uid}"
    
        role_name = e["role_name"]

        desc += f"{i}. {name} - {role_name}\n"

    embed = discord.Embed(
        title="🎲 抽選準備",
        description=desc
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

    view = HistoryView(guild_id, interaction.guild, limit=5)

    embed = view.build_embed()

    await interaction.response.send_message(
        embed=embed,
        view=view
    )
    
# =========================
# /list
# =========================
@tree.command(name="list", description="登録一覧")
async def list_cmd(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    uid = str(interaction.user.id)

    is_op = is_operator(guild_id, uid)
    is_admin = interaction.user.guild_permissions.administrator

    entries = get_entries(guild_id)

    if not entries:
        await interaction.response.send_message("登録なし", ephemeral=True)
        return

    # 👑 管理者モード
    if is_op or is_admin:
        embed = discord.Embed(title="📋 登録一覧（管理者）", color=discord.Color.blurple())

        for uid, entry in entries.items():
            try:
                member = interaction.guild.get_member(int(uid)) \
                    or await interaction.guild.fetch_member(int(uid))
            except:
                member = None

            name = member.display_name if member else f"ID:{uid}"
            status = "🟢ON" if is_enabled(entry) else "🔴OFF"

            embed.add_field(
                name=name,
                value=f"{entry['role_name']}\n倍率: {entry['weight']:.1f} | {status}",
                inline=False
            )

        view = AdminListView(entries, guild_id, interaction.guild)

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

    # 👤 一般ユーザー
    else:
        public_entries = get_enabled_entries(entries)

        embed = discord.Embed(title="📋 登録一覧", color=discord.Color.blurple())

        for uid, entry in public_entries.items():
            try:
                member = interaction.guild.get_member(int(uid)) \
                    or await interaction.guild.fetch_member(int(uid))
            except:
                member = None

            name = member.display_name if member else f"ID:{uid}"

            embed.add_field(
                name=name,
                value=f"{entry['role_name']}\n倍率: {entry['weight']:.1f}",
                inline=False
            )

        embed.set_footer(text=f"登録人数: {len(public_entries)}人")

        await interaction.response.send_message(embed=embed)
        
# =========================
# /role
# =========================
@app_commands.describe(
    name="ロール名",
    color="カラーコード（例: FF0000）",
    user="対象ユーザー（未指定なら自分）"
)
@tree.command(name="role", description="ロール登録")
async def role(
    interaction: discord.Interaction,
    name: str,
    color: str = None,
    user: discord.Member = None
):
    guild_id = str(interaction.guild.id)
    uid = str(interaction.user.id)

    target_member = user if user else interaction.user

    if color:
        color = color.replace("#", "")

    entries = get_entries(guild_id)
    old = entries.get(uid)

    entry = {
        "role_name": name,
        "color": color,
        "target": str(target_member.id),
        "weight": 1,
        "role_id": old.get("role_id") if old else None
    }

    # =========================
    # 既存あり → 上書き確認
    # =========================
    if old:
        old_member = interaction.guild.get_member(int(old["target"]))

        old_embed = create_role_embed(
            "現在の設定",
            old["role_name"],
            old["color"],
            old_member
        )

        new_embed = create_role_embed(
            "新しい設定",
            name,
            color,
            target_member
        )

        view = ConfirmView(guild_id, uid, entry)

        await interaction.response.send_message(
            content="⚠️ 上書きしますか？",
            embeds=[old_embed, new_embed],
            view=view,
            ephemeral=True
        )

        view.message = await interaction.original_response()
        return

    # =========================
    # 新規登録
    # =========================
    save_entry(guild_id, uid, entry)

    embed = create_role_embed(
        "✅登録しました",
        name,
        color,
        target_member
    )

    await interaction.response.send_message(embed=embed)

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
