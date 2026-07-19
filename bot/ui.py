from typing import Awaitable, Callable

import discord
from discord import ui

from .utils import estado_texto


class PaginadorView(ui.View):
    """View genérica para paginar texto o Embeds ya renderizados, con botones."""

    def __init__(
        self, paginas: list[str] | list[discord.Embed], autor_id: int, timeout: float = 120
    ):
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

    def _render_kwargs(self) -> dict:
        pagina = self.paginas[self.pagina]
        if isinstance(pagina, discord.Embed):
            return {"content": None, "embed": pagina}
        return {"content": pagina, "embed": None}

    async def enviar_inicial(self, interaction: discord.Interaction, ephemeral: bool = False) -> None:
        await interaction.response.send_message(**self._render_kwargs(), view=self, ephemeral=ephemeral)
        self.message = await interaction.original_response()

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
        await interaction.response.edit_message(**self._render_kwargs(), view=self)

    @ui.button(label="Siguiente ➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, _button: ui.Button):
        self.pagina += 1
        self._actualizar_botones()
        await interaction.response.edit_message(**self._render_kwargs(), view=self)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True  # type: ignore[attr-defined]
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class SelectorPosView(ui.View):
    """Dropdown para elegir una POS entre varias que tiene el mismo dueño."""

    def __init__(
        self,
        outposts: list,
        autor_id: int,
        on_select: Callable[[discord.Interaction, object], Awaitable[None]],
        timeout: float = 60,
    ):
        super().__init__(timeout=timeout)
        self.autor_id = autor_id
        self.on_select = on_select
        self.por_id = {o.id_num: o for o in outposts}
        self.selector.options = [
            discord.SelectOption(
                label=f"#{o.id_num} - {o.nombre_pos}"[:100],
                description=estado_texto(o.pagado_hasta_mes, o.anio_vencimiento)[:100],
                value=str(o.id_num),
            )
            for o in outposts[:25]
        ]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "No podés usar este menú.", ephemeral=True
            )
            return False
        return True

    @ui.select(placeholder="Elegí una POS...")
    async def selector(self, interaction: discord.Interaction, select: ui.Select):
        outpost = self.por_id[int(select.values[0])]
        await self.on_select(interaction, outpost)
