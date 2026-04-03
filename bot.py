import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import random
import sqlite3
import shutil
from io import BytesIO
import asyncio
from PIL import ImageFont

FONT_PATH = os.path.join(os.path.dirname(__file__), "NotoSansJP-VariableFont_wght.ttf")
if not os.path.exists(FONT_PATH):
    print("フォントファイルが存在しません")
print("FONT_PATH:", FONT_PATH)
try:
    FONT = ImageFont.truetype(FONT_PATH, 15)
    SMALL_FONT = ImageFont.truetype(FONT_PATH, 10)
    print("フォント読み込み成功")
except Exception as e:
    print("フォント読み込み失敗:", e)
    FONT = ImageFont.load_default()
    SMALL_FONT = FONT

DB_PATH = "/data/data.db"
MAX_WEIGHT = 3

# =========================
# DB初期化
# =========================
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_conn()
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operators (
        guild_id TEXT,
        user_id TEXT,
        PRIMARY KEY (guild_id, user_id)
    )
""")

    conn.commit()
    conn.close()

# =========================
# DB操作
# =========================
def get_entries(guild_id):
    conn = get_conn()
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
    conn = get_conn()
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
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM entries WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    conn.commit()
    conn.close()

def add_history(guild_id, winner_id, role_name):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO history (guild_id, winner_id, role_name)
    VALUES (?, ?, ?)
    """, (guild_id, winner_id, role_name))

    conn.commit()
    conn.close()

def get_history(guild_id):
    conn = get_conn()
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
                embeds=[],
                view=self
            )

    @discord.ui.button(label="上書きする", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        save_entry(self.guild_id, self.uid, self.entry)
        try:
            member = interaction.guild.get_member(int(self.entry["target"]))
            if not member:
                member = await interaction.guild.fetch_member(int(self.entry["target"]))
        except Exception as e:
            print("member fetch error:", e)
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
        await interaction.response.defer()
        await interaction.edit_original_response(
            content="キャンセルしました",
            embed=None,
            view=None
        )

# =========================
# 管理者
# =========================
def add_operator(guild_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO operators VALUES (?, ?)
    """, (guild_id, user_id))

    conn.commit()
    conn.close()


def remove_operator(guild_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    DELETE FROM operators WHERE guild_id=? AND user_id=?
    """, (guild_id, user_id))

    conn.commit()
    conn.close()


def is_operator(guild_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT 1 FROM operators WHERE guild_id=? AND user_id=?
    """, (guild_id, user_id))

    result = cur.fetchone()
    conn.close()

    return result is not None

# =========================
# 抽選
# =========================
def pick_winner(entries):
    users = list(entries.keys())
    weights = [entries[u].get("weight", 1) for u in users]
    if not users:
        return None
    return random.choices(users, weights=weights, k=1)[0]

def normalize_color(code: str) -> int:
    try:
        if not code:
            return 0x5865F2  # デフォルト

        code = code.replace("#", "")

        if len(code) != 6:
            return 0x5865F2

        return int(code, 16)

    except:
        return 0x5865F2

from PIL import Image, ImageDraw
import math
from io import BytesIO

def create_pie_chart(entries):
    size = 350
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)

    center = size // 2
    radius = 120

    total = sum(e["weight"] for e in entries.values())
    if total <= 0:
        total = 1

    start_angle = -90  # 上スタート

    sorted_entries = sorted(entries.items(), key=lambda x: x[1]["weight"], reverse=True)

    for i, (uid, e) in enumerate(sorted_entries, start=1):
        weight = e["weight"]
        angle = 360 * (weight / total)
        color_val = normalize_color(e.get("color"))
        hex_color = f"#{color_val:06x}"

        # ===== 円 =====
        draw.pieslice(
            [
                center - radius,
                center - radius,
                center + radius,
                center + radius
            ],
            start=start_angle,
            end=start_angle + angle,
            fill=hex_color,
            outline="white"
        )

        percent = (weight / total * 100)
        mid_angle = math.radians(start_angle + angle / 2)

        # ===== 中に％ =====
        if percent >= 5:
            text = f"{percent:.0f}%"

            tx = center + (radius * 0.6) * math.cos(mid_angle)
            ty = center + (radius * 0.6) * math.sin(mid_angle)

            bbox = draw.textbbox((0, 0), text, font=FONT)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]

            for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
                draw.text((tx - w/2 + dx, ty - h/2 + dy), text, fill="black", font=FONT)

            draw.text((tx - w/2, ty - h/2), text, fill="white", font=FONT)

        # ===== 外側：番号だけ =====
        label = str(i)

        lx = center + (radius * 1.15) * math.cos(mid_angle)
        ly = center + (radius * 1.15) * math.sin(mid_angle)

        bbox = draw.textbbox((0, 0), label, font=FONT)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        draw.text(
            (lx - w/2, ly - h/2),
            label,
            fill="black",
            font=FONT
        )

        start_angle += angle

    # タイトル
    draw.text((20, 10), "Participants", fill="black", font=FONT)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

class DiceView(discord.ui.View):
    def __init__(self, entries, guild_id):
        super().__init__(timeout=60)
        self.entries = entries
        self.guild_id = guild_id
        self.used = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def on_timeout(self):
        dice_running[self.guild_id] = False

        for item in self.children:
            item.disabled = True

        if hasattr(self, "message") and self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="🎲 抽選する", style=discord.ButtonStyle.green)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.used:
            await interaction.response.send_message("もう抽選済みです", ephemeral=True)
            return
    
        self.used = True
        button.disabled = True

        await interaction.response.defer()
        await interaction.edit_original_response(view=self)

        try:
            # ① 1個だけメッセージ送る
            msg = await interaction.followup.send(content="🎲 抽選中...")

            # 演出
            for i in range(3):
                await msg.edit(content="🎲 抽選中" + "." * i)
                await asyncio.sleep(0.5)

            winner_id = pick_winner(self.entries)
            if not winner_id:
                await msg.edit(content="抽選できませんでした")
                return

            entry = self.entries[winner_id]

            winner_weight = entry["weight"]
            total = sum(e["weight"] for e in self.entries.values()) or 1
            chance = winner_weight / total * 100

            try:
                member = interaction.guild.get_member(int(entry["target"])) \
                    or await interaction.guild.fetch_member(int(entry["target"]))
            except:
                await interaction.followup.send("⚠️ ユーザー取得に失敗しました")
                return

            # ロール削除
            for uid, e in self.entries.items():
                role_id = e.get("role_id")
                if not role_id:
                    continue

                r = interaction.guild.get_role(role_id)
                if not r:
                    e["role_id"] = None
                    save_entry(self.guild_id, uid, e)
                    continue

                if r != interaction.guild.default_role and r < interaction.guild.me.top_role and not r.managed:
                    try:
                        await r.delete()
                    except Exception as e:
                        print("role delete error:", e)

            # ロール作成
            color = discord.Color(normalize_color(entry["color"]))
            role = await interaction.guild.create_role(
                name=entry["role_name"],
                color=color
            )

            try:
                await role.edit(position=interaction.guild.me.top_role.position - 1)
            except:
                pass

            await member.add_roles(role)
            entry["role_id"] = role.id

            # 重み更新
            for uid, e in self.entries.items():
                if uid == winner_id:
                    e["weight"] = 1
                else:
                    e["weight"] = min(e.get("weight", 1) + 0.25, MAX_WEIGHT)
                save_entry(self.guild_id, uid, e)

            add_history(self.guild_id, winner_id, entry["role_name"])

            embed = create_role_embed(
                "🎉当選！",
                entry["role_name"],
                entry["color"],
                member
            )
            embed.description = (embed.description or "") + f"\n当選確率: {chance:.1f}%"

        # ② 同じメッセージを結果に変更
        try:
            await msg.edit(content=None, embed=embed)
        except Exception as e:
            print("dice error:", e)
            try:
                await msg.edit(content="エラーが発生しました")
            except:
            pass

        finally:
            dice_running[self.guild_id] = False
                
# =========================
# Weight
# =========================
class WeightSelect(discord.ui.Select):
    def __init__(self, entries, guild_id, guild):
        self.entries = entries
        self.guild_id = guild_id
        self.guild = guild
        self.used = False

        options = []

        sorted_entries = sorted(
            entries.items(),
            key=lambda x: x[1]["weight"],
            reverse=True
        )

        for i, (uid, e) in enumerate(sorted_entries, start=1):
            member = self.guild.get_member(int(uid))
            name = member.display_name if member else uid
        
            weight = e["weight"]

            label = f"{i}. {name} (w={weight:.2f})"

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=uid
                )
            )

        super().__init__(
            placeholder="ユーザーを選択",
            options=options[:25]  # Discord制限
        )

    async def callback(self, interaction: discord.Interaction):
        uid = self.values[0]

        modal = WeightModal(self.guild_id, uid)
        await interaction.response.send_modal(modal)

class WeightModal(discord.ui.Modal, title="重み変更"):
    value = discord.ui.TextInput(label="新しい重み", placeholder="例: 1.5")

    def __init__(self, guild_id, target_id):
        super().__init__()
        self.guild_id = guild_id
        self.target_id = target_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = float(self.value.value)
        except:
            await interaction.response.send_message("数値を入力してください", ephemeral=True)
            return

        value = max(0.1, min(value, MAX_WEIGHT))

        entries = get_entries(self.guild_id)

        if self.target_id not in entries:
            await interaction.response.send_message("対象が存在しません", ephemeral=True)
            return

        # 更新
        entries[self.target_id]["weight"] = value
        save_entry(self.guild_id, self.target_id, entries[self.target_id])

        # 確率計算
        total = sum(e["weight"] for e in entries.values())
        if total <= 0:
            total = 1
        chance = value / total * 100

        member = interaction.guild.get_member(int(self.target_id))
        name = member.display_name if member else self.target_id

        await interaction.response.send_message(
            f"{name} の重みを {value:.2f} に変更\n現在の当選確率: {chance:.1f}%",
            ephemeral=True
        )

class WeightView(discord.ui.View):
    def __init__(self, entries, guild_id, guild):
        super().__init__(timeout=60)
        self.add_item(WeightSelect(entries, guild_id, guild))
# =========================
# Embed
# =========================
def create_role_embed(title, role_name, color_code, target_member=None):
    # 色処理
    if color_code:
        hex_code = f"{normalize_color(color_code):06x}"
        color = discord.Color(normalize_color(color_code))
        image_url = f"https://dummyimage.com/100x100/{hex_code}/{hex_code}.png"
        color_text = f"#{hex_code}"
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

dice_running = {}

# =========================
# /role
# =========================
@app_commands.describe(
    name="ロール名",
    color="カラーコード（例: FF0000）",
    user="対象ユーザー（未指定の場合は自分）"
)
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
    is_op = is_operator(guild_id, uid)

    # 一般ユーザー
    if not is_op:
        if uid not in entries:
            await interaction.response.send_message("登録がありません", ephemeral=True)
            return

        entry = entries[uid]

        if entry.get("role_id"):
            role = interaction.guild.get_role(entry["role_id"])
            if role:
                try:
                    await role.delete()
                except Exception as e:
                    print("role delete error:", e)

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
    gid = str(interaction.guild.id)

    if dice_running.get(gid):
        await interaction.response.send_message("抽選中です", ephemeral=True)
        return

    dice_running[gid] = True
    
    try:
        await interaction.response.defer()

        entries = get_entries(gid)

        if not entries:
            dice_running[gid] = False
            await interaction.followup.send("登録なし")
            return

        img = create_pie_chart(entries)
        file = discord.File(img, filename="chart.png")

        embed = discord.Embed(
            title="🎲 抽選準備",
            description="ボタンを押して抽選！",
            color=discord.Color.blurple()
        )
        embed.set_image(url="attachment://chart.png")

        desc = ""
        sorted_entries = sorted(entries.items(), key=lambda x: x[1]["weight"], reverse=True)

        for i, (uid, entry) in enumerate(sorted_entries, start=1):
            member = interaction.guild.get_member(int(uid)) \
                or await interaction.guild.fetch_member(int(uid))
            name = member.display_name if member else uid
            desc += f"{i}. {name} → {entry['role_name']}\n"
        
        embed.add_field(name="参加者一覧", value=desc or "なし", inline=False)

        view = DiceView(entries, gid)
        msg = await interaction.followup.send(embed=embed, file=file, view=view)
        view.message = msg

    except Exception as e:
        print("dice error:", e)
        await interaction.followup.send("エラーが発生しました")

# =========================
# /list
# =========================
@tree.command(name="list", description="登録一覧")
async def list_roles(interaction: discord.Interaction):
    await interaction.response.defer()

    entries = get_entries(str(interaction.guild.id))

    embed = discord.Embed(title="📋一覧", color=discord.Color.blurple())

    for uid, entry in entries.items():
        member = interaction.guild.get_member(int(uid)) \
            or await interaction.guild.fetch_member(int(uid))
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
        member = interaction.guild.get_member(int(uid)) \
            or await interaction.guild.fetch_member(int(uid))
        name = member.display_name if member else uid
        desc += f"{i}. {name} → {role}\n"

    embed = discord.Embed(
        title="履歴",
        description=desc or "履歴なし",
        color = discord.Color.blurple()
    )
    embed.set_footer(text="直近10件")

    await interaction.followup.send(embed=embed)

#==========================
#/operator
#==========================
@tree.command(name="add_operator", description="Bot管理者を追加")
@app_commands.describe(user="追加するユーザー")
async def add_operator_cmd(interaction: discord.Interaction, user: discord.Member):

    # サーバー管理者のみ実行可能
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("管理者のみ実行可能", ephemeral=True)
        return

    add_operator(str(interaction.guild.id), str(user.id))

    await interaction.response.send_message(f"{user.display_name} をBot管理者に追加しました")

@tree.command(name="delete_operator", description="Bot管理者を削除")
@app_commands.describe(user="削除するユーザー")
async def delete_operator_cmd(interaction: discord.Interaction, user: discord.Member):

    # Bot管理者のみ実行可能
    if not is_operator(str(interaction.guild.id), str(interaction.user.id)):
        await interaction.response.send_message("Bot管理者のみ実行可能", ephemeral=True)
        return

    remove_operator(str(interaction.guild.id), str(user.id))

    await interaction.response.send_message(f"{user.display_name} をBot管理者から削除しました")

# =========================
# /weight
# =========================
@tree.command(name="weight", description="重み変更（Bot管理者のみ）")
async def weight(interaction: discord.Interaction):

    guild_id = str(interaction.guild.id)
    uid = str(interaction.user.id)

    if not is_operator(guild_id, uid):
        await interaction.response.send_message("Bot管理者のみ実行可能", ephemeral=True)
        return

    entries = get_entries(guild_id)

    if not entries:
        await interaction.response.send_message("登録がありません", ephemeral=True)
        return

    view = WeightView(entries, guild_id, interaction.guild)

    await interaction.response.send_message(
        "重みを変更するユーザーを選択してください",
        view=view,
        ephemeral=True
    )

# =========================
# 起動
# =========================
@client.event
async def on_ready():
    os.makedirs("/data", exist_ok=True)

    if not os.path.exists(DB_PATH):
        open(DB_PATH, "a").close()

    init_db()
    await tree.sync()
    print("起動完了")

    await client.change_presence(
        activity=discord.Game(name="( ˘ω˘)ｽﾔｧ")
    )
client.run(TOKEN)
