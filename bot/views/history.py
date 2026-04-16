import discord
from utils import get_member_safe, get_display_name

# =========================
# 共通：タイムアウト処理
# =========================
class BaseTimeoutView(discord.ui.View):
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if hasattr(self, "message") and self.message:
            await self.message.edit(view=self)

# =========================
# Embed生成
# =========================
async def create_history_embed(data, guild, title="履歴"):
    embed = discord.Embed(
        title=title,
        color=discord.Color.blue()
    )

    if not data:
        embed.description = "履歴がありません"
        return embed

    text = ""
    for i, (uid, role_name) in enumerate(data, 1):
        member = await get_member_safe(guild, uid)
        name = get_display_name(member, uid)

        text += f"{i}. {name} - {role_name}\n"
        
    embed.description = text
    return embed

# =========================
# 通常履歴（5件）
# =========================
class HistoryView(discord.ui.View):
    def __init__(self, history):
        super().__init__(timeout=60)
        self.history_full = history

    @discord.ui.button(label="全履歴", style=discord.ButtonStyle.green)
    async def show_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = HistoryAllView(self.history_full)
        await view.update_first(interaction)

        view.message = await interaction.original_response()

# =========================
# 全履歴（ページング）
# =========================
class HistoryAllView(BaseTimeoutView):
    def __init__(self, history):
        super().__init__(timeout=120)
        self.history = history
        self.page = 0
        self.per_page = 10

    def get_page_data(self):
        start = self.page * self.per_page
        end = start + self.per_page
        return self.history[start:end]

    def get_max_page(self):
        if not self.history:
            return 0
        return (len(self.history) - 1) // self.per_page

    # 🔽 初回表示
    async def update_first(self, interaction: discord.Interaction):
        max_page = self.get_max_page()

        self.page_label.label = f"{self.page+1}/{max_page+1}"
        self.prev.disabled = self.page == 0
        self.next.disabled = self.page == max_page

        embed = await create_history_embed(
            self.get_page_data(),
            interaction.guild,
            title="📜 全履歴"
        )

        await interaction.response.send_message(
            embed=embed,
            view=self,
            ephemeral=True
        )

    # 🔽 更新用
    async def update(self, interaction: discord.Interaction):
        max_page = self.get_max_page()

        self.page_label.label = f"{self.page+1}/{max_page+1}"
        self.prev.disabled = self.page == 0
        self.next.disabled = self.page == max_page

        embed = await create_history_embed(
            self.get_page_data(),
            interaction.guild,
            title="📜 全履歴"
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    # =========================
    # ボタン
    # =========================
    @discord.ui.button(label="<<", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await self.update(interaction)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True)
    async def page_label(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label=">>", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.get_max_page():
            self.page += 1
        await self.update(interaction)
