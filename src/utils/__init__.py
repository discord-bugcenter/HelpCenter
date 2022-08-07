from discord import Color


class ExtendedColor(Color):
    @classmethod
    def grey_embed(cls):
        return cls(0x2F3136)

    def to_matplotlib(self, a: float = 1) -> tuple[float, float, float, float]:
        return self.r / 255, self.g / 255, self.b / 255, a
