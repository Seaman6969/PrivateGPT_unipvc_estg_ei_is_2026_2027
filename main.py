from __future__ import annotations

import os
import sys

# Prevent any .pyc / __pycache__ generation next to main.py or inside any package
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import tkinter as tk

from gui import widgets, window


def main() -> None:
    root: tk.Tk = tk.Tk()
    widgets.apply_theme(root)
    window.MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
