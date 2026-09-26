import tkinter as tk
from tkinter import filedialog, messagebox

from local.extract import filetypes, read

from . import widgets


class AttachmentsBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=widgets.WHITE, bd=0)
        self._chips = None
        self._files: list[tuple[str, str]] = []
        self._build()

    def _build(self) -> None:
        self._make_attach_button().pack(side="left")
        self._chips = widgets.make_frame(self, bg=widgets.WHITE)
        self._chips.pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _make_attach_button(self) -> tk.Button:
        return widgets.make_small_button(self, "+ Attach", self._pick)

    def _pick(self) -> None:
        paths = filedialog.askopenfilenames(
        title="Attach files",
        filetypes=filetypes(),
        )
        for path in paths:
            self._attach(path)

    def _attach(self, path: str) -> None:
        try:
            content = read(path)
        except Exception as e:
            messagebox.showerror("Could not read file", f"{path}\n\n{e}")
            return
        self._files.append((path, content))
        self._render()

    def _render(self) -> None:
        self._clear()
        for path, _ in self._files:
            chip = widgets.make_chip(self._chips, _name(path),
                                     lambda p=path: self._remove(p))
            chip.pack(side="left", padx=(0, 6))

    def _clear(self) -> None:
        for child in self._chips.winfo_children():
            child.destroy()

    def _remove(self, path: str) -> None:
        self._files = [f for f in self._files if f[0] != path]
        self._render()

    def get_files(self) -> list[tuple[str, str]]:
        return list(self._files)

    def clear(self) -> None:
        self._files = []
        self._render()


def _name(path: str) -> str:
    return path.rsplit("/", 1)[-1]
