import discord
import random
import asyncio

from utils import get_enabled_entries, get_member_safe, normalize_color, is_enabled, MAX_WEIGHT
from db import save_entry, add_history
from embed import create_role_embed

class DiceView(discord.ui.View):
    def __init__(self, entries, guild_id, dice_running):
        super().__init__(timeout=60)
        self.entries = entries
        self.guild_id = guild_id
        self.dice_running = dice_running
        self.used = False
        self.dice_running = dice_running

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def on_timeout(self):
        self.dice_running[self.guild_id] = False

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
            enabled_entries = {
                uid: e for uid, e in self.entries.items()
                if is_enabled(e)
            }

            total = sum(e["weight"] for e in enabled_entries.values()) or 1
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

                if r != interaction.guild.default_role and r.position < interaction.guild.me.top_role.position and not r.managed:
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
                    e["weight"] = round(min(e.get("weight", 1) + 0.2, MAX_WEIGHT), 1)
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
            await msg.edit(content=None, embed=embed)
            
        except Exception as e:
            print("dice error:", e)
            await msg.edit(content="エラーが発生しました")

        finally:
            self.dice_running[self.guild_id] = False
          
# ===================
# == pick winner ====
# ===================
def pick_winner(entries):
    enabled_entries = get_enabled_entries(entries)

    users = list(enabled_entries.keys())
    weights = [enabled_entries[u].get("weight", 1) for u in users]

    if not users:
        return None

    return random.choices(users, weights=weights, k=1)[0]
