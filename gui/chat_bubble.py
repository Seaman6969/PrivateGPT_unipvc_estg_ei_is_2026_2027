import tkinter as tk

from . import markdown, widgets

PADX = 14
PADY = 10
WIDTH = 40
THROTTLE_MS = 60
MIN_FIT_WIDTH = 50

_CTRL_OR_CMD = 0x4 | 0x8 | 0x10

_NAV_KEYS = frozenset({
    "Left", "Right", "Up", "Down",
    "Home", "End", "Prior", "Next",
    "Page_Up", "Page_Down",
    "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
})


def _on_readonly_key(event):
    if event.keysym.lower() in ("c", "a") and (event.state & _CTRL_OR_CMD):
        return None
    if event.keysym in _NAV_KEYS:
        return None
    return "break"


class MessageBubble(tk.Frame):
    def __init__(self, parent, role):
        super().__init__(parent, bg=widgets.INDIGO_GHOST, bd=0)
        self.role = role
        self._raw = ""
        self._base = f"{role}_base"
        self._text = None
        self._pending = None
        self._last_width = 0
        self._build()

    def _build(self):
        self._text = self._make_text()
        self._text.pack(fill="x", padx=18, pady=5)
        self._text.tag_configure(
            self._base,
            background=self._bg(),
            foreground=self._fg(),
            justify=self._justify(),
        )
        markdown.configure(self._text, self._palette())
        sel_bg, sel_fg = self._selection_colors()
        self._text.tag_configure("sel", background=sel_bg, foreground=sel_fg)
        self._text.tag_raise("sel")
        self.bind("<Configure>", self._on_configure)

    def _make_text(self):
        sel_bg, sel_fg = self._selection_colors()
        text = tk.Text(
            self, wrap="word", height=1, width=WIDTH,
            bd=0, highlightthickness=0, relief="flat",
            padx=PADX, pady=PADY, cursor="arrow",
            font=self._font(),
            background=self._bg(), foreground=self._fg(),
            insertwidth=0,
            selectbackground=sel_bg, selectforeground=sel_fg,
        )
        text.bind("<Key>", _on_readonly_key)
        text.bind("<Button-2>", lambda _event: "break")
        text.bind("<Button-1>", lambda _event: text.focus_set())
        return text

    def _justify(self):
        return "right" if self.role == "user" else "left"

    def _selection_colors(self):
        if self.role == "user":
            return widgets.WHITE, widgets.INDIGO_DEEP
        return widgets.INDIGO_DEEP, widgets.WHITE

    def _bg(self):
        return {
            "user": widgets.INDIGO,
            "thinking": widgets.INDIGO_GHOST,
            "assistant": widgets.WHITE,
        }.get(self.role, widgets.WHITE)

    def _fg(self):
        return {
            "user": widgets.WHITE,
            "thinking": widgets.GRAY_MUTED,
            "assistant": widgets.GRAY_TEXT,
        }.get(self.role, widgets.GRAY_TEXT)

    def _font(self):
        return widgets.FONT_SMALL if self.role == "thinking" else widgets.FONT_BODY

    def _palette(self):
        family, size = self._font()[:2]
        return {
            "bold": (family, size, "bold"),
            "italic": (family, size, "italic"),
            "mono": ("monospace", size - 1),
            "code_bg": self._code_bg(),
            "heading": (family, size + 2, "bold"),
        }

    def _code_bg(self):
        return {
            "user": widgets.INDIGO_DEEP,
            "thinking": widgets.WHITE,
        }.get(self.role, widgets.INDIGO_GHOST)

    def set_text(self, text):
        self._raw = text
        self._rerender()

    def append(self, token):
        self._raw += token
        self._schedule()

    def _schedule(self):
        if self._pending is None:
            self._pending = self.after(THROTTLE_MS, self._flush)

    def _flush(self):
        self._pending = None
        self._rerender()

    def _rerender(self):
        markdown.render(self._text, self._raw, self._base)
        self._fit()
        self._text.tag_raise("sel")

    def _on_configure(self, event):
        if event.width == self._last_width:
            return
        self._last_width = event.width
        self.after_idle(self._fit)

    def _fit(self):
        if self._text is None:
            return
        self._text.update_idletasks()
        if self._text.winfo_width() < MIN_FIT_WIDTH:
            return
        try:
            lines = self._text.count("1.0", "end", "displaylines")
        except tk.TclError:
            return
        if lines:
            self._text.config(height=lines)

    def destroy(self):
        if self._pending is not None:
            self.after_cancel(self._pending)
        super().destroy()