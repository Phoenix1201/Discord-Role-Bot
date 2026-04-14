import discord
from db import save_entry
from embed import create_role_embed

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
            member = interaction.guild.get_member(int(self.entry["target"])) \
                or await interaction.guild.fetch_member(int(self.entry["target"]))
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
        await interaction.response.defer()
        await interaction.edit_original_response(
            content="キャンセルしました",
            embed=None,
            view=None
        )
