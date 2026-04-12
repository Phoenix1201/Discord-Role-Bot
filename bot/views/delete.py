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
