class ToggleSelect(discord.ui.Select):
    def __init__(self, entries, guild_id, guild):
        self.entries = entries
        self.guild_id = guild_id
        self.guild = guild

        options = []

        # ON → OFFの順に並べる（見やすい）
        sorted_entries = sorted(
            entries.items(),
            key=lambda x: x[1].get("enabled", 1),
            reverse=True
        )

        for uid, e in sorted_entries:
            member = guild.get_member(int(uid))
            name = get_display_name(member, uid)

            enabled = e.get("enabled", 1)
            status = "🟢ON" if enabled else "🔴OFF"

            label = f"{name} [{status}]"

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=uid
                )
            )

        super().__init__(
            placeholder="ON/OFFを切り替えるユーザーを選択",
            options=options[:25]
        )

    async def callback(self, interaction: discord.Interaction):
        uid = self.values[0]

        entry = self.entries.get(uid)
        if not entry:
            await interaction.response.send_message("対象が存在しません", ephemeral=True)
            return

        # トグル
        entry["enabled"] = 0 if entry.get("enabled", 1) == 1 else 1
        save_entry(self.guild_id, uid, entry)

        member = interaction.guild.get_member(int(uid))
        name = get_display_name(member, uid)

        status = "🟢ON（参加中）" if entry["enabled"] else "🔴OFF（除外中）"

        await interaction.response.edit_message(
            content=f"{name} を {status} に変更しました",
            view=None
        )


class ToggleView(discord.ui.View):
    def __init__(self, entries, guild_id, guild):
        super().__init__(timeout=60)
        self.add_item(ToggleSelect(entries, guild_id, guild))
