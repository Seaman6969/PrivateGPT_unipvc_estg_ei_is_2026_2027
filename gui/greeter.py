from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from local.catalog import CATEGORIES, FileCatalog
from rag.manifest import ManifestEntry
from local.extract import filetypes
from . import widgets

HERO_TITLE: str = "PrivateGPT"
HERO_SUBTITLE: str = "Private procurement assistant"
KB_TITLE: str = "Knowledge base"
STATUS_PLACEHOLDER: str = "…"
CATEGORY_COLUMN_WIDTH: int = 120
ACTIVE_COLUMN_WIDTH: int = 80
INDEXED_COLUMN_WIDTH: int = 160
TREE_HEIGHT: int = 10
BUTTON_GAP: int = 6


class Greeter(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        on_chat: Callable[[], None],
        on_refresh: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=widgets.INDIGO_GHOST)
        self._on_refresh = on_refresh
        self._catalog = FileCatalog()
        self._stale = False
        self._tree: ttk.Treeview | None = None
        self._status = None
        self._refresh_button = None
        self._category_var: tk.StringVar | None = None
        self._build(on_chat=on_chat)

    def _build(self, on_chat: Callable[[], None]) -> None:
        self._build_hero(on_chat=on_chat)
        self._build_knowledge_base()
        self._build_status()
        self._refresh_tree()

    def _build_hero(self, on_chat: Callable[[], None]) -> None:
        hero = widgets.make_frame(self, bg=widgets.INDIGO_GHOST)
        hero.pack(fill="x", padx=40, pady=(30, 20))
        widgets.make_label(
            hero, HERO_TITLE, font=widgets.FONT_TITLE,
            fg=widgets.INDIGO_DEEP, bg=widgets.INDIGO_GHOST,
        ).pack(anchor="w")
        widgets.make_subtle(hero, HERO_SUBTITLE).pack(anchor="w", pady=(4, 14))
        widgets.make_button(hero, "Talk to the assistant", on_chat).pack(anchor="w")

    def _build_knowledge_base(self) -> None:
        section = widgets.make_frame(self, bg=widgets.INDIGO_GHOST)
        section.pack(fill="both", expand=True, padx=40, pady=(0, 20))
        widgets.make_label(
            section, KB_TITLE, font=widgets.FONT_TITLE,
            fg=widgets.INDIGO_DEEP, bg=widgets.INDIGO_GHOST,
        ).pack(anchor="w", pady=(0, 8))
        self._build_kb_toolbar(section)
        self._build_kb_tree(section)

    def _build_kb_toolbar(self, parent: tk.Misc) -> None:
        row = widgets.make_frame(parent, bg=widgets.INDIGO_GHOST)
        row.pack(fill="x", pady=(0, 8))
        self._category_var = tk.StringVar(value=CATEGORIES[0])
        for label, command in self._toolbar_buttons_helper():
            widgets.make_small_button(row, label, command).pack(side="left", padx=(0, BUTTON_GAP))
        ttk.Combobox(
            row, values=CATEGORIES, textvariable=self._category_var, width=14,
        ).pack(side="left", padx=(BUTTON_GAP, 0))
        self._refresh_button = widgets.make_small_button(row, "Refresh index", self._refresh)
        self._refresh_button.pack(side="right")

    def _toolbar_buttons_helper(self) -> list[tuple[str, Callable[[], None]]]:
        return [
            ("+ Add files", self._add),
            ("Apply category", self._apply_category),
            ("Toggle active", self._toggle_active),
            ("Remove", self._remove),
        ]

    def _on_tree_select(self, _event) -> None:
        path = self._selected_path()
        if path is None:
            return
        entry = self._entry_for_helper(path=path)
        if entry is not None and self._category_var is not None:
            self._category_var.set(entry.category)
        
    def _build_kb_tree(self, parent: tk.Misc) -> None:
        wrapper = widgets.make_frame(parent, bg=widgets.WHITE)
        wrapper.pack(fill="both", expand=True)
        self._tree = ttk.Treeview(
            wrapper,
            columns=("category", "active", "indexed"),
            show="tree headings",
            selectmode="browse",
            height=TREE_HEIGHT,
        )
        self._tree.heading("#0", text="File")
        self._tree.heading("category", text="Category")
        self._tree.heading("active", text="Active")
        self._tree.heading("indexed", text="Last indexed")
        self._tree.column("#0", width=380)
        self._tree.column("category", width=CATEGORY_COLUMN_WIDTH)
        self._tree.column("active", width=ACTIVE_COLUMN_WIDTH)
        self._tree.column("indexed", width=INDEXED_COLUMN_WIDTH)
        self._tree.pack(side="left", fill="both", expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        bar = widgets.attach_scrollbar(wrapper, self._tree)
        bar.pack(side="right", fill="y")

    def _build_status(self) -> None:
        strip = widgets.make_frame(self, bg=widgets.INDIGO_GHOST)
        strip.pack(fill="x", side="bottom", padx=40, pady=(0, 20))
        self._status = widgets.make_subtle(strip, STATUS_PLACEHOLDER)
        self._status.pack(side="left")

    def _refresh_tree(self) -> None:
        if self._tree is None:
            return
        for row in self._tree.get_children():
            self._tree.delete(row)
        for entry in self._catalog.entries():
            self._tree.insert(
                "", "end", iid=entry.path, text=entry.path,
                values=_row_values_helper(entry=entry),
            )

    def _add(self) -> None:
        paths = filedialog.askopenfilenames(title="Add files", filetypes=filetypes())
        errors: list[str] = []
        for path in paths:
            result = self._catalog.add(path=path, category=self._category_var.get())
            if result is not None:
                errors.append(result.message)
        if errors:
            messagebox.showerror("Could not add file", "\n".join(errors))

        self._mark_stale()
        self._refresh_tree()

    def _apply_category(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        
        result = self._catalog.set_category(
            path=path,
            category=self._category_var.get(),
        )
        if result is not None:
            messagebox.showerror("Could not apply category", result.message)
            return
        self._mark_stale()
        self._refresh_tree()

    def _toggle_active(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        entry = self._entry_for_helper(path=path)
        if entry is None:
            return
        self._catalog.deactivate(path) if entry.active else self._catalog.activate(path)
        self._mark_stale()
        self._refresh_tree()

    def _remove(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        if not messagebox.askyesno("Remove file", f"Remove {path} from the knowledge base?"):
            return
        self._catalog.remove(path=path)
        self._mark_stale()
        self._refresh_tree()

    def _selected_path(self) -> str | None:
        if self._tree is None:
            return None
        selection = self._tree.selection()
        return selection[0] if selection else None

    def _entry_for_helper(self, path: str) -> ManifestEntry | None:
        return next((e for e in self._catalog.entries() if e.path == path), None)

    def _mark_stale(self) -> None:
        self._catalog.save()
        self._stale = True
        if self._refresh_button is not None:
            self._refresh_button.config(state="normal")

    def _refresh(self) -> None:
        if self._refresh_button is not None:
            self._refresh_button.config(state="disabled")
        if self._status is not None:
            self._status.config(text="Re-indexing…")
        self._on_refresh()

    def refresh_done(self, summary: str, total: int, errors: list[str] | None = None) -> None:
        self._stale = False
        self._catalog = FileCatalog()  # reload the manifest freshly written to disk
        if self._status is not None:
            text = f"Index: {total} files · sync: {summary}"
            if errors:
                text += " · " + "; ".join(errors)
            self._status.config(text=text)
        if self._refresh_button is not None:
            self._refresh_button.config(state="normal")
        self._refresh_tree()

    def set_status(self, text: str) -> None:
        if self._status is not None:
            self._status.config(text=text)


def _row_values_helper(entry: ManifestEntry) -> tuple[str, str, str]:
    active: str = "yes" if entry.active else "no"
    indexed: str = entry.indexed_at[:19].replace("T", " ") if entry.indexed_at else "—"
    return entry.category, active, indexed
