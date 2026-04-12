class ConfirmDeleteView(discord.ui.View):
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

    @discord.ui.button(label="削除する", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        # ロール削除（安全チェック強化）
        if self.entry.get("role_id"):
            role = interaction.guild.get_role(self.entry["role_id"])
            if role and role.position < interaction.guild.me.top_role.position and not role.managed:
                try:
                    await role.delete()
                except Exception as e:
                    print("role delete error:", e)

        delete_entry(self.guild_id, self.uid)

        self.stop()
        await interaction.edit_original_response(
            content="✅ 削除しました",
            embed=None,
            view=None
        )

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        button.disabled = True
        await interaction.response.defer()
        await interaction.edit_original_response(
            content="キャンセルしました",
            embed=None,
            view=None
        )
