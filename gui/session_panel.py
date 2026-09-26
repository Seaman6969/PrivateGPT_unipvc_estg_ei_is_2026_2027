from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Callable

from config import sessions
from config.sessions import SessionMeta

from . import widgets

PANEL_WIDTH: int = 200


class SessionPanel(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        on_select: Callable[[str], None],
        on_new: Callable[[], None],
        on_deleted: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=widgets.INDIGO_GHOST, width=PANEL_WIDTH)
        self._on_select = on_select
        self._on_new = on_new
        self._on_deleted = on_deleted
        self._metas: list[SessionMeta] = []
        self._list: tk.Listbox | None = None
        self.pack_propagate(False)
        self._build()

    def _build(self) -> None:
        header = widgets.make_frame(self, bg=widgets.WHITE)
        header.pack(fill="x")
        widgets.make_small_button(header, "+ New", self._on_new).pack(
            side="left", padx=10, pady=10,
        )
        self._list = self._make_list_helper()
        self._list.pack(fill="both", expand=True, padx=(10, 0), pady=(0, 10))

    def _make_list_helper(self) -> tk.Listbox:
        box = tk.Listbox(
            self, bd=0, highlightthickness=0, activestyle="none",
            bg=widgets.WHITE, fg=widgets.GRAY_TEXT,
            selectbackground=widgets.INDIGO_PALE, selectforeground=widgets.INDIGO_DEEP,
            font=widgets.FONT_SMALL,
        )
        # React to user gestures only. Reacting to <<ListboxSelect>> would
        # also fire for programmatic selection_set() calls from select(),
        # which turns every sync of the visual selection into a re-load.
        box.bind("<ButtonRelease-1>", self._on_user_pick)
        box.bind("<KeyRelease-Up>", self._on_user_pick)
        box.bind("<KeyRelease-Down>", self._on_user_pick)
        box.bind("<Button-3>", self._on_right_click)
        return box

    def reload(self) -> None:
        if self._list is None:
            return
        self._list.delete(0, "end")
        self._metas = sessions.list_sessions()
        for meta in self._metas:
            self._list.insert("end", meta.title)

    def select(self, session_id: str) -> None:
        if self._list is None:
            return
        for idx, meta in enumerate(self._metas):
            if meta.id == session_id:
                self._list.selection_clear(0, "end")
                self._list.selection_set(idx)
                self._list.see(idx)
                return

    def selected_id(self) -> str | None:
        if self._list is None:
            return None
        sel = self._list.curselection()
        return self._metas[sel[0]].id if sel else None

    def metas(self) -> list[SessionMeta]:
        return list(self._metas)

    def _on_user_pick(self, _event) -> None:
        session_id: str | None = self.selected_id()
        if session_id:
            self._on_select(session_id)

    def _on_right_click(self, event) -> None:
        if self._list is None:
            return
        index = self._list.nearest(event.y)
        if index < 0 or index >= len(self._metas):
            return
        self._list.selection_clear(0, "end")
        self._list.selection_set(index)
        self._popup_helper(event=event)

    def _popup_helper(self, event) -> None:
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Rename…", command=self._rename)
        menu.add_command(label="Delete", command=self._delete)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _rename(self) -> None:
        session_id: str | None = self.selected_id()
        if session_id is None:
            return
        new_title: str | None = simpledialog.askstring(
            "Rename", "New title:", parent=self,
        )
        if new_title is None:
            return
        new_title = new_title.strip()
        if not new_title:
            return
        result = sessions.rename_session(session_id=session_id, title=new_title)
        if result is not None:
            messagebox.showerror("Could not rename", result.message, parent=self)
            return
        self.reload()
        self.select(session_id=session_id)

    def _delete(self) -> None:
        session_id: str | None = self.selected_id()
        if session_id is None:
            return
        if not messagebox.askyesno("Delete session", "Delete this chat?", parent=self):
            return
        result = sessions.delete_session(session_id=session_id)
        if result is not None:
            messagebox.showerror("Could not delete", result.message, parent=self)
            return
        self.reload()
        if self._on_deleted is not None:
            self._on_deleted(session_id)
