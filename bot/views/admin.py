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
