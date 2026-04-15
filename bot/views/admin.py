import discord
from db import *
from utils import *
from embed import create_operator_embed
from views.weight import WeightView
from views.toggle import ToggleView
from views.delete import ConfirmDeleteView
from views.admin_manage import ManageMenuView

class AdminPanelView(discord.ui.View):
    def __init__(self, guild_id, guild):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.guild = guild

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

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

class OperatorManageView(discord.ui.View):
    def __init__(self, guild_id, can_full_control=False, can_add_only=False):
        super().__init__(timeout=60)
        self.guild_id = guild_id

        # 後で実行させる
        self.can_full_control = can_full_control
        self.can_add_only = can_add_only

    async def on_timeout(self):
        pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    def setup_buttons(self):
        if self.can_add_only:
            for item in self.children:
                if item.label != "追加":
                    item.disabled = True

        elif not self.can_full_control:
            for item in self.children:
                item.disabled = True

    @discord.ui.button(label="追加", style=discord.ButtonStyle.green)
    async def add_op(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            "追加するユーザーを選択",
            view=OperatorAddSelectView(self.guild_id),
            ephemeral=True
        )

    @discord.ui.button(label="解除", style=discord.ButtonStyle.red)
    async def remove_op(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not is_operator(self.guild_id, str(interaction.user.id)):
            await interaction.response.send_message("Bot管理者のみ操作可能", ephemeral=True)
            return
        
        button.disabled = True
        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            "解除するユーザーを選択",
            view=OperatorRemoveSelectView(self.guild_id),
            ephemeral=True
        )

class OperatorAddSelect(discord.ui.UserSelect):
    def __init__(self, guild_id):
        super().__init__(
            placeholder="追加するユーザーを選択",
            min_values=1,
            max_values=1
        )
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        user = self.values[0]
        uid = str(user.id)

        ops = get_operators(self.guild_id)

        if uid in ops:
            await interaction.response.edit_message(
                content=f"{user.display_name} は既に管理者です",
                view=None
            )
            return

        add_operator(self.guild_id, uid)

        await interaction.response.edit_message(
            content=f"{user.display_name} を管理者に追加しました",
            view=None
        )

class OperatorAddSelectView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=60)
        self.add_item(OperatorAddSelect(guild_id))

class OperatorRemoveSelect(discord.ui.UserSelect):
    def __init__(self, guild_id):
        super().__init__(
            placeholder="解除するユーザーを選択",
            min_values=1,
            max_values=1
        )
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        user = self.values[0]

        remove_operator(self.guild_id, str(user.id))

        await interaction.response.edit_message(
            content=f"{user.display_name} の管理者権限を解除しました",
            view=None
        )

class OperatorRemoveSelectView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=60)
        self.add_item(OperatorRemoveSelect(guild_id))

#===================
#/list(管理者用)
#===================
class AdminListView(discord.ui.View):
    def __init__(self, entries, guild_id, guild):
        super().__init__(timeout=60)
        self.entries = entries
        self.guild_id = guild_id
        self.guild = guild

    @discord.ui.button(label="⚙️ 登録管理", style=discord.ButtonStyle.gray)
    async def manage(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        await interaction.response.edit_message(view=self)

        view = ManageMenuView(self.guild_id, self.guild)

        await interaction.followup.send(
            "管理メニュー",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="📢 公開する", style=discord.ButtonStyle.green)
    async def publish(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        await interaction.response.defer()
        
        embed = discord.Embed(title="📋 登録一覧", color=discord.Color.blurple())

        public_entries = {
            uid: e for uid, e in self.entries.items()
            if is_enabled(e)
        }

        latest = get_latest_winner(self.guild_id)
        
        sorted_entries = sorted(
            public_entries.items(),
            key=lambda x: x[1]["weight"],
            reverse=True
        )

        for uid, entry in sorted_entries:
            member = await get_member_safe(self.guild, uid)
            name = member.display_name if member else f"ID:{uid}"
            mark = " 👑" if uid == latest else ""

            embed.add_field(
                name=f"{name}{mark}",
                value=f"{entry['role_name']}\n倍率: {entry['weight']:.1f}",
                inline=False
            )

        embed.set_footer(text=f"登録人数: {len(public_entries)}人")

        # チャンネルに送信（公開）
        await interaction.followup.send(embed=embed)

        try:
            await interaction.edit_original_response(view=None)
        except:
            pass
