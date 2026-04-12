class AdminPanelView(discord.ui.View):
    def __init__(self, guild_id, guild, is_full_access):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.guild = guild
        self.is_full_access = is_full_access

    async def on_timeout(self):
        pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    def disable_for_non_operator(self):
        if not self.is_full_access:
            for item in self.children:
                if item.label != "👑 管理者編集":
                    item.disabled = True

    @discord.ui.button(label="⚖ 重み", style=discord.ButtonStyle.blurple)
    async def weight_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_operator(self.guild_id, str(interaction.user.id)):
            await interaction.response.send_message("Bot管理者のみ操作可能", ephemeral=True)
            return
            
        button.disabled = True
        await interaction.response.edit_message(view=self)

        view = WeightView(get_entries(self.guild_id), self.guild_id, self.guild)
        await interaction.followup.send("重み変更", view=view, ephemeral=True)

    @discord.ui.button(label="🔁 ON/OFF", style=discord.ButtonStyle.green)
    async def toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_operator(self.guild_id, str(interaction.user.id)):
            await interaction.response.send_message("Bot管理者のみ操作可能", ephemeral=True)
            return
            
        button.disabled = True
        await interaction.response.edit_message(view=self)

        view = ToggleView(get_entries(self.guild_id), self.guild_id, self.guild)
        await interaction.followup.send("ON/OFF変更", view=view, ephemeral=True)

    @discord.ui.button(label="👑 管理者編集", style=discord.ButtonStyle.gray)
    async def operator_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        uid = str(interaction.user.id)
        guild_id = self.guild_id

        is_op = is_operator(guild_id, uid)
        is_admin = interaction.user.guild_permissions.administrator

        # 権限チェック
        if not (is_op or is_admin):
            await interaction.response.send_message("権限なし", ephemeral=True)
            return

        button.disabled = True
        await interaction.response.edit_message(view=self)
        
        embed = create_operator_embed(self.guild, guild_id)

        view = OperatorManageView(
            guild_id,
            can_full_control=is_op,
            can_add_only=(is_admin and not is_op)
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
