import discord
from db import get_entries
from views.toggle import ToggleView
from views.weight import WeightView
from views.delete import DeleteView

class ManageMenuView(discord.ui.View):
    def __init__(self, guild_id, guild):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.guild = guild

    @discord.ui.button(label="🔁 ON/OFF", style=discord.ButtonStyle.green)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ToggleView(get_entries(self.guild_id), self.guild_id, self.guild)
        await interaction.response.send_message("ON/OFF変更", view=view, ephemeral=True)

    @discord.ui.button(label="⚖ 重み変更", style=discord.ButtonStyle.blurple)
    async def weight(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = WeightView(get_entries(self.guild_id), self.guild_id, self.guild)
        await interaction.response.send_message("重み変更", view=view, ephemeral=True)

    @discord.ui.button(label="🗑 削除", style=discord.ButtonStyle.red)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DeleteView(get_entries(self.guild_id), self.guild_id, self.guild)
        await interaction.response.send_message("削除するユーザーを選択", view=view, ephemeral=True)
