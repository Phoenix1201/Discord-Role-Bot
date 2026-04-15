import discord
from db import get_history, get_latest_winner

class HistoryView(discord.ui.View):
    def __init__(self, guild_id, guild, limit=5):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.guild = guild
        self.limit = limit

    def build_embed(self):
        rows = get_history(self.guild_id)
        latest = get_latest_winner(self.guild_id)

        if not rows:
            return discord.Embed(
                title="📜 履歴",
                description="履歴がありません",
                color=discord.Color.gold()
            )

        display_rows = rows[:self.limit] if self.limit else rows

        embed = discord.Embed(
            title=f"📜 履歴（最新{len(display_rows)}件）",
            color=discord.Color.gold()
        )

        for i, (uid, role_name) in enumerate(display_rows, start=1):
            member = self.guild.get_member(int(uid))
            name = member.display_name if member else f"ID:{uid}"
            mark = " 👑" if uid == latest else ""
            
            embed.add_field(
                name=f"{i}. {name}{mark}",
                value=role_name,
                inline=False
            )

        return embed

    async def update(self, interaction):
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="5件", style=discord.ButtonStyle.gray)
    async def show5(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.limit = 5
        await self.update(interaction)

    @discord.ui.button(label="10件", style=discord.ButtonStyle.gray)
    async def show10(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.limit = 10
        await self.update(interaction)

    @discord.ui.button(label="全て", style=discord.ButtonStyle.green)
    async def show_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.limit = None
        await self.update(interaction)
