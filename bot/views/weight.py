import discord

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
            name = member.display_name if member else f"不明ユーザー({uid})"
        
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
