import discord
from discord import ui


class PaginadorView(ui.View):
    """View genérica para paginar texto ya renderizado con botones."""

    def __init__(self, paginas: list[str], autor_id: int, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.paginas = paginas
        self.autor_id = autor_id
        self.pagina = 0
        self.message: discord.Message | None = None
        self._actualizar_botones()
        if len(paginas) <= 1:
            self.clear_items()

    def _actualizar_botones(self) -> None:
        self.anterior.disabled = self.pagina == 0
        self.siguiente.disabled = self.pagina >= len(self.paginas) - 1

    def render(self) -> str:
        return self.paginas[self.pagina]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "Solo quien pidió este reporte puede pasar de página.", ephemeral=True
            )
            return False
        return True

    @ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary)
    async def anterior(self, interaction: discord.Interaction, _button: ui.Button):
        self.pagina -= 1
        self._actualizar_botones()
        await interaction.response.edit_message(content=self.render(), view=self)

    @ui.button(label="Siguiente ➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, _button: ui.Button):
        self.pagina += 1
        self._actualizar_botones()
        await interaction.response.edit_message(content=self.render(), view=self)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True  # type: ignore[attr-defined]
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
