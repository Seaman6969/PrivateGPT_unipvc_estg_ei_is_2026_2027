import tkinter as tk

from . import markdown, widgets

PADX = 14
PADY = 10
WIDTH = 60
THROTTLE_MS = 60


class MessageBubble(tk.Frame):
    def __init__(self, parent, role: str):
        super().__init__(parent, bg=widgets.INDIGO_GHOST, bd=0)
        self.role = role
        self._raw = ""
        self._base = f"{role}_base"
        self._text = None
        self._pending = None
        self._build()

    def _build(self) -> None:
        self._text = self._make_text()
        self._text.pack(anchor=self._anchor(), padx=18, pady=5)
        self._text.tag_configure(self._base, background=self._bg(), foreground=self._fg())
        markdown.configure(self._text, self._palette())

    def _make_text(self) -> tk.Text:
        return tk.Text(
            self, wrap="word", height=1, width=WIDTH,
            bd=0, highlightthickness=0, relief="flat",
            padx=PADX, pady=PADY, cursor="arrow",
            font=self._font(),
            background=self._bg(), foreground=self._fg(),
            state="disabled",
        )

    def _bg(self) -> str:
        return {
            "user": widgets.INDIGO,
            "thinking": widgets.INDIGO_GHOST,
            "assistant": widgets.WHITE,
        }.get(self.role, widgets.WHITE)

    def _fg(self) -> str:
        return {
            "user": widgets.WHITE,
            "thinking": widgets.GRAY_MUTED,
            "assistant": widgets.GRAY_TEXT,
        }.get(self.role, widgets.GRAY_TEXT)

    def _font(self):
        return widgets.FONT_SMALL if self.role == "thinking" else widgets.FONT_BODY

    def _anchor(self) -> str:
        return "e" if self.role == "user" else "w"

    def _palette(self) -> dict:
        family, size = self._font()[:2]
        return {
            "bold": (family, size, "bold"),
            "italic": (family, size, "italic"),
            "mono": ("monospace", size - 1),
            "code_bg": self._code_bg(),
            "heading": (family, size + 2, "bold"),
        }

    def _code_bg(self) -> str:
        return {
            "user": widgets.INDIGO_DEEP,
            "thinking": widgets.WHITE,
        }.get(self.role, widgets.INDIGO_GHOST)

    def set_text(self, text: str) -> None:
        self._raw = text
        self._rerender()

    def append(self, token: str) -> None:
        self._raw += token
        self._schedule()

    def _schedule(self) -> None:
        if self._pending is None:
            self._pending = self.after(THROTTLE_MS, self._flush)

    def _flush(self) -> None:
        self._pending = None
        self._rerender()

    def _rerender(self) -> None:
        markdown.render(self._text, self._raw, self._base)
        self._fit()

    def _fit(self) -> None:
        self._text.update_idletasks()
        try:
            lines = self._text.count("1.0", "end", "displaylines")
        except tk.TclError:
            return
        if lines:
            self._text.config(height=lines)

    def destroy(self) -> None:
        if self._pending is not None:
            self.after_cancel(self._pending)
        super().destroy()
