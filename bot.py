import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import random
import sqlite3
import shutil

DB_PATH = "/data/data.db"
MAX_WEIGHT = 5

# =========================
# DB初期化
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        guild_id TEXT,
        user_id TEXT,
        role_name TEXT,
        color TEXT,
        target TEXT,
        weight REAL,
        role_id INTEGER,
        PRIMARY KEY (guild_id, user_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history (
        guild_id TEXT,
        winner_id TEXT,
        role_name TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

# =========================
# DB操作
# =========================
def get_entries(guild_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    cur.execute("SELECT * FROM entries WHERE guild_id=?", (guild_id,))
    rows = cur.fetchall()
    conn.close()

    data = {}
    for r in rows:
        data[r[1]] = {
            "role_name": r[2],
            "color": r[3],
            "target": r[4],
            "weight": r[5],
            "role_id": r[6]
        }
    return data

def save_entry(guild_id, user_id, entry):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO entries VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        guild_id,
        user_id,
        entry["role_name"],
        entry["color"],
        entry["target"],
        entry["weight"],
        entry.get("role_id")
    ))

    conn.commit()
    conn.close()

def delete_entry(guild_id, user_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    cur.execute("DELETE FROM entries WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    conn.commit()
    conn.close()

def add_history(guild_id, winner_id, role_name):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO history (guild_id, winner_id, role_name)
    VALUES (?, ?, ?)
    """, (guild_id, winner_id, role_name))

    conn.commit()
    conn.close()

def get_history(guild_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()

    cur.execute("""
    SELECT winner_id, role_name FROM history
    WHERE guild_id=? ORDER BY ts DESC LIMIT 10
    """, (guild_id,))

    rows = cur.fetchall()
    conn.close()
    return rows

# =========================
# 上書き確認ボタン
# =========================
class ConfirmView(discord.ui.View):
    def __init__(self, guild_id, uid, entry):
        super().__init__(timeout=30)
        self.guild_id = guild_id
        self.uid = uid
        self.entry = entry
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return str(interaction.user.id) == self.uid
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.message:
            await self.message.edit(
                content="⏰ 時間切れでキャンセルされました",
                view=self
            )

    @discord.ui.button(label="上書きする", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        save_entry(self.guild_id, self.uid, self.entry)
        try:
            member = await interaction.guild.fetch_member(int(self.entry["target"]))
        except:
            member = None
        embed = create_role_embed(
            "✅上書きしました",
            self.entry["role_name"],
            self.entry["color"],
            member
        )
        self.stop()
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(
            content="キャンセルしました",
            embed=None,
            view=None
        )

# =========================
# 抽選
# =========================
def pick_winner(entries):
    users = list(entries.keys())
    weights = [entries[u].get("weight", 1) for u in users]
    if not users:
        return None
    return random.choices(users, weights=weights, k=1)[0]

# =========================
# Embed
# =========================
def create_role_embed(title, role_name, color_code, target_member=None):
    # 色処理
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

    # 対象ユーザー表示
    if target_member:
        target_text = target_member.display_name
    else:
        target_text = "未指定"

    desc = f"ロール名：{role_name}\n色：{color_text}\n対象：{target_text}"

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
async def role(interaction: discord.Interaction, name: str, color: str = None, user: discord.Member = None):

    guild_id = str(interaction.guild.id)
    uid = str(interaction.user.id)
    target_member = user if user else interaction.user

    if color:
        color = color.replace("#", "")

    old = get_entries(guild_id).get(uid)

    entry = {
        "role_name": name,
        "color": color,
        "target": str(user.id) if user else uid,
        "weight": 1,
        "role_id": old.get("role_id") if old else None
    }

    # 既に登録あり → 確認出す
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

    # 新規登録
    save_entry(guild_id, uid, entry)

    embed = create_role_embed(
        "✅登録しました",
        name,
        color,
        target_member
    )
    await interaction.response.send_message(embed=embed)

# =========================
# /delete
# =========================
@tree.command(name="delete", description="登録削除")
async def delete(interaction: discord.Interaction, user: discord.Member = None):

    guild_id = str(interaction.guild.id)
    entries = get_entries(guild_id)

    uid = str(interaction.user.id)
    is_admin = interaction.user.guild_permissions.administrator

    # 一般ユーザー
    if not is_admin:
        if uid not in entries:
            await interaction.response.send_message("登録がありません", ephemeral=True)
            return

        entry = entries[uid]

        if entry.get("role_id"):
            role = interaction.guild.get_role(entry["role_id"])
            if role:
                try:
                    await role.delete()
                except:
                    pass

        delete_entry(guild_id, uid)
        await interaction.response.send_message("登録を解除しました", ephemeral=True)
        return

    # 管理者
    if not user:
        await interaction.response.send_message("ユーザーを指定して下さい", ephemeral=True)
        return

    target_id = str(user.id)

    if target_id not in entries:
        await interaction.response.send_message("登録なし", ephemeral=True)
        return

    entry = entries[target_id]

    if entry.get("role_id"):
        role = interaction.guild.get_role(entry["role_id"])
        if role:
            try:
                await role.delete()
            except:
                pass

    delete_entry(guild_id, target_id)
    await interaction.response.send_message(f"{user.display_name} の登録を解除しました")

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

        guild_id = str(interaction.guild.id)
        entries = get_entries(guild_id)

        if not entries:
            await interaction.followup.send("登録なし")
            return

        winner_id = pick_winner(entries)
        entry = entries[winner_id]

        member = await interaction.guild.fetch_member(int(entry["target"]))

        color = discord.Color(int(entry["color"], 16)) if entry["color"] else discord.Color.default()

        if entry.get("role_id"):
            old = interaction.guild.get_role(entry["role_id"])
            if old:
                try:
                    await old.delete()
                except:
                    pass

        role = await interaction.guild.create_role(name=entry["role_name"], color=color)
        await role.edit(position=interaction.guild.me.top_role.position - 1)
        await member.add_roles(role)

        entry["role_id"] = role.id

        for uid, e in entries.items():
            if uid == winner_id:
                e["weight"] = 1
            else:
                e["weight"] = min(e.get("weight", 1) + 0.5, MAX_WEIGHT)

            save_entry(guild_id, uid, e)

        add_history(guild_id, winner_id, entry["role_name"])

        embed = create_role_embed(
            "🎲当選！",
            entry["role_name"],
            entry["color"],
            member
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

    entries = get_entries(str(interaction.guild.id))

    embed = discord.Embed(title="📋一覧", color=discord.Color.blurple())

    for uid, entry in entries.items():
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else uid

        embed.add_field(
            name=name,
            value=f"{entry['role_name']}\n倍率: {entry['weight']:.1f}",
            inline=False
        )

    embed.set_footer(text=f"登録人数: {len(entries)}人" if entries else "登録なし")

    await interaction.followup.send(embed=embed)

# =========================
# /history
# =========================
@tree.command(name="history", description="当選履歴")
async def history(interaction: discord.Interaction):
    await interaction.response.defer()

    rows = get_history(str(interaction.guild.id))

    desc = ""
    for i, (uid, role) in enumerate(rows, 1):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else uid
        desc += f"{i}. {name} → {role}\n"

    embed = discord.Embed(
        title="履歴",
        description=desc or "履歴なし",
        color = discord.Color.blurple()
    )
    embed.set_footer(text="直近10件")

    await interaction.followup.send(embed=embed)

# =========================
# 起動
# =========================
@client.event
async def on_ready():
    os.makedirs("/data", exist_ok=True)

    if not os.path.exists("/data/data.db"):
        shutil.copy("data.db", "/data/data.db")
        print("DBコピー完了")

    init_db()
    await tree.sync()
    print("起動完了")
client.run(TOKEN)
