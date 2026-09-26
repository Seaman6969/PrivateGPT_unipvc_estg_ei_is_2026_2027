from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

INDIGO_DEEP: str = "#1a237e"
INDIGO: str = "#3949ab"
INDIGO_LIGHT: str = "#5c6bc0"
INDIGO_PALE: str = "#c5cae9"
INDIGO_GHOST: str = "#e8eaf6"
WHITE: str = "#ffffff"
GRAY_TEXT: str = "#263238"
GRAY_MUTED: str = "#78909c"
GRAY_BORDER: str = "#cfd8dc"
RED_ERROR: str = "#c62828"
GREEN_SUCCESS: str = "#2e7d32"

FontSpec = tuple[str, int] | tuple[str, int, str]
Command = Callable[[], None]

FONT_BODY: FontSpec = ("Helvetica", 11)
FONT_SMALL: FontSpec = ("Helvetica", 9)
FONT_TITLE: FontSpec = ("Helvetica", 13, "bold")
FONT_CHIP_REMOVE: FontSpec = ("Helvetica", 9, "bold")

SCROLLBAR_ARROW_SIZE: int = 12
CHIP_LABEL_PADX: tuple[int, int] = (8, 2)
CHIP_REMOVE_PADX: tuple[int, int] = (2, 8)
CHIP_PADY: int = 3
BUTTON_PADX: int = 20
BUTTON_PADY: int = 8
SMALL_BUTTON_PADX: int = 10
SMALL_BUTTON_PADY: int = 4
TEXT_PADX: int = 12
TEXT_PADY: int = 10
CHECKBOX_PADX: int = 6
SEPARATOR_HEIGHT: int = 1


def apply_theme(root: tk.Tk) -> None:
    _use_clam_helper()
    _root_bg_helper(root=root)
    _fonts_helper(root=root)
    _scroll_style_helper()


def make_frame(parent: tk.Misc, bg: str = INDIGO_GHOST) -> tk.Frame:
    return tk.Frame(parent, bg=bg, bd=0, highlightthickness=0)


def make_label(parent: tk.Misc, text: str = "", **overrides: Any) -> tk.Label:
    options: dict[str, Any] = _label_defaults_helper()
    options.update(overrides)
    return tk.Label(parent, text=text, **options)


def make_title(parent: tk.Misc, text: str) -> tk.Label:
    return make_label(parent, text, font=FONT_TITLE, fg=INDIGO_DEEP)


def make_subtle(parent: tk.Misc, text: str = "") -> tk.Label:
    return make_label(parent, text, font=FONT_SMALL, fg=GRAY_MUTED)


def make_checkbox(
    parent: tk.Misc,
    text: str,
    variable: tk.BooleanVar,
    command: Command | None = None,
    bg: str = WHITE,
) -> tk.Checkbutton:
    return tk.Checkbutton(
        parent, text=text, variable=variable, command=command,
        bg=bg, fg=GRAY_TEXT,
        activebackground=bg, activeforeground=INDIGO_DEEP,
        selectcolor=WHITE, font=FONT_SMALL,
        bd=0, highlightthickness=0, cursor="hand2",
        anchor="w", padx=CHECKBOX_PADX,
    )


def make_button(parent: tk.Misc, text: str, command: Command) -> tk.Button:
    return tk.Button(
        parent, text=text, command=command,
        bg=INDIGO, fg=WHITE,
        activebackground=INDIGO_DEEP, activeforeground=WHITE,
        font=FONT_BODY, bd=0, padx=BUTTON_PADX, pady=BUTTON_PADY,
        highlightthickness=0, cursor="hand2",
    )


def make_small_button(parent: tk.Misc, text: str, command: Command) -> tk.Button:
    return tk.Button(
        parent, text=text, command=command,
        bg=INDIGO_PALE, fg=INDIGO_DEEP,
        activebackground=INDIGO_LIGHT, activeforeground=WHITE,
        font=FONT_SMALL, bd=0, padx=SMALL_BUTTON_PADX, pady=SMALL_BUTTON_PADY,
        highlightthickness=0, cursor="hand2",
    )


def make_canvas(parent: tk.Misc) -> tk.Canvas:
    return tk.Canvas(parent, bg=INDIGO_GHOST, bd=0, highlightthickness=0, borderwidth=0)


def make_text(parent: tk.Misc, height: int = 3) -> tk.Text:
    return tk.Text(
        parent, height=height, wrap="word",
        bg=WHITE, fg=GRAY_TEXT,
        insertbackground=INDIGO,
        font=FONT_BODY, bd=0, highlightthickness=0,
        relief="flat", padx=TEXT_PADX, pady=TEXT_PADY,
    )


def make_entry(parent: tk.Misc, show: str = "", width: int = 28) -> tk.Entry:
    entry = tk.Entry(
        parent,
        show=show,
        width=width,
        bg=WHITE,
        fg=GRAY_TEXT,
        insertbackground=INDIGO,
        font=FONT_BODY,
        bd=1,
        relief="solid",
        highlightthickness=1,
        highlightbackground=GRAY_BORDER,
        highlightcolor=INDIGO,
    )
    return entry


def make_separator(parent: tk.Misc, bg: str = GRAY_BORDER) -> tk.Frame:
    return tk.Frame(parent, bg=bg, height=SEPARATOR_HEIGHT, bd=0, highlightthickness=0)


def attach_scrollbar(parent: tk.Misc, widget: tk.Canvas) -> ttk.Scrollbar:
    bar: ttk.Scrollbar = ttk.Scrollbar(parent, orient="vertical", command=widget.yview)
    widget.config(yscrollcommand=bar.set)
    return bar


def make_chip(parent: tk.Misc, text: str, on_remove: Command) -> tk.Frame:
    chip: tk.Frame = tk.Frame(parent, bg=INDIGO_PALE, bd=0, highlightthickness=0)
    _chip_label_helper(parent=chip, text=text).pack(
        side="left", padx=CHIP_LABEL_PADX, pady=CHIP_PADY,
    )
    _chip_remove_helper(parent=chip, on_remove=on_remove).pack(
        side="left", padx=CHIP_REMOVE_PADX, pady=CHIP_PADY,
    )
    return chip


def _use_clam_helper() -> None:
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        return


def _root_bg_helper(root: tk.Tk) -> None:
    root.configure(bg=INDIGO_GHOST)


def _fonts_helper(root: tk.Tk) -> None:
    root.option_add("*Font", FONT_BODY)


def _scroll_style_helper() -> None:
    ttk.Style().configure(
        "Vertical.TScrollbar",
        background=INDIGO_PALE,
        troughcolor=INDIGO_GHOST,
        borderwidth=0,
        arrowsize=SCROLLBAR_ARROW_SIZE,
    )


def _label_defaults_helper() -> dict[str, Any]:
    return {
        "bg": INDIGO_GHOST,
        "fg": GRAY_TEXT,
        "font": FONT_BODY,
        "anchor": "w",
        "justify": "left",
    }


def _chip_label_helper(parent: tk.Misc, text: str) -> tk.Label:
    return tk.Label(
        parent, text=text, bg=INDIGO_PALE, fg=INDIGO_DEEP, font=FONT_SMALL,
    )


def _chip_remove_helper(parent: tk.Misc, on_remove: Command) -> tk.Label:
    label: tk.Label = tk.Label(
        parent, text="x", bg=INDIGO_PALE, fg=INDIGO_DEEP,
        font=FONT_CHIP_REMOVE, cursor="hand2",
    )
    label.bind("<Button-1>", lambda _event: on_remove())
    return label
