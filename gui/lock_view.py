from __future__ import annotations

import tkinter as tk
from typing import Callable

import config.sessions as sessions
import security

from . import widgets


class LockView(tk.Frame):
    def __init__(self, parent: tk.Misc, on_unlocked: Callable[[], None]) -> None:
        super().__init__(parent, bg=widgets.INDIGO_GHOST)
        self._on_unlocked = on_unlocked
        self._is_setup: bool = not security.is_vault_initialized()
        self._pw_entry: tk.Entry | None = None
        self._confirm_entry: tk.Entry | None = None
        self._error_label: tk.Label | None = None
        self._build()

    def _build(self) -> None:
        # Centering container
        center = widgets.make_frame(self, bg=widgets.INDIGO_GHOST)
        center.place(relx=0.5, rely=0.45, anchor="center")

        card = widgets.make_frame(center, bg=widgets.WHITE)
        card.pack(padx=20, pady=20)

        # Padding frame inside card
        pad = tk.Frame(card, bg=widgets.WHITE, padx=36, pady=32)
        pad.pack()

        # Title & subtitle
        title_text = "Welcome to PrivateGPT" if self._is_setup else "PrivateGPT Locked"
        widgets.make_label(
            pad,
            title_text,
            font=widgets.FONT_TITLE,
            fg=widgets.INDIGO_DEEP,
            bg=widgets.WHITE,
        ).pack(anchor="w", pady=(0, 4))

        sub_text = (
            "Create a master password to encrypt and secure your chats."
            if self._is_setup
            else "Enter your master password to decrypt your chats."
        )
        widgets.make_label(
            pad,
            sub_text,
            font=widgets.FONT_SMALL,
            fg=widgets.GRAY_MUTED,
            bg=widgets.WHITE,
        ).pack(anchor="w", pady=(0, 20))

        # Password label & input
        widgets.make_label(
            pad,
            "Master Password",
            font=widgets.FONT_SMALL,
            fg=widgets.GRAY_TEXT,
            bg=widgets.WHITE,
        ).pack(anchor="w", pady=(0, 4))

        self._pw_entry = widgets.make_entry(pad, show="*", width=30)
        self._pw_entry.pack(anchor="w", pady=(0, 12), ipady=4)
        self._pw_entry.bind("<Return>", lambda _e: self._on_submit())

        # If first-time setup, show confirmation input
        if self._is_setup:
            widgets.make_label(
                pad,
                "Confirm Password",
                font=widgets.FONT_SMALL,
                fg=widgets.GRAY_TEXT,
                bg=widgets.WHITE,
            ).pack(anchor="w", pady=(0, 4))

            self._confirm_entry = widgets.make_entry(pad, show="*", width=30)
            self._confirm_entry.pack(anchor="w", pady=(0, 12), ipady=4)
            self._confirm_entry.bind("<Return>", lambda _e: self._on_submit())

        # Error label
        self._error_label = widgets.make_label(
            pad,
            "",
            font=widgets.FONT_SMALL,
            fg=widgets.RED_ERROR,
            bg=widgets.WHITE,
        )
        self._error_label.pack(anchor="w", pady=(0, 12))

        # Action button
        btn_text = "Create Password & Unlock" if self._is_setup else "Unlock"
        btn = widgets.make_button(pad, btn_text, self._on_submit)
        btn.pack(anchor="w", fill="x")

        # Focus password entry
        self.after(50, self._focus_entry)

    def _focus_entry(self) -> None:
        if self._pw_entry is not None:
            self._pw_entry.focus_set()

    def _show_error(self, message: str) -> None:
        if self._error_label is not None:
            self._error_label.config(text=message)

    def _clear_error(self) -> None:
        if self._error_label is not None:
            self._error_label.config(text="")

    def _on_submit(self) -> None:
        self._clear_error()
        assert self._pw_entry is not None
        pw = self._pw_entry.get().strip()

        if not pw:
            self._show_error("Please enter a password.")
            return

        if self._is_setup:
            assert self._confirm_entry is not None
            confirm = self._confirm_entry.get().strip()
            if pw != confirm:
                self._show_error("Passwords do not match.")
                return
            if len(pw) < 4:
                self._show_error("Password must be at least 4 characters.")
                return

            try:
                security.setup_vault(password=pw)
                # If there are legacy LocalGPT chats, import and encrypt them
                sessions.import_legacy_sessions_if_present()
                self._on_unlocked()
            except Exception as exc:
                self._show_error(f"Setup failed: {exc}")
        else:
            if security.unlock_vault(password=pw):
                # Import any legacy sessions if first unlock
                sessions.import_legacy_sessions_if_present()
                self._on_unlocked()
            else:
                self._show_error("Incorrect password. Please try again.")
                self._pw_entry.delete(0, "end")
                self._pw_entry.focus_set()


class ChangePasswordDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.title("Change Master Password - PrivateGPT")
        self.resizable(False, False)
        self.configure(bg=widgets.INDIGO_GHOST)
        self.transient(parent)
        self.grab_set()

        self._old_pw: tk.Entry | None = None
        self._new_pw: tk.Entry | None = None
        self._confirm_pw: tk.Entry | None = None
        self._error_label: tk.Label | None = None
        self._build()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _build(self) -> None:
        pad = tk.Frame(self, bg=widgets.WHITE, padx=28, pady=24)
        pad.pack(padx=16, pady=16)

        widgets.make_label(
            pad,
            "Change Master Password",
            font=widgets.FONT_TITLE,
            fg=widgets.INDIGO_DEEP,
            bg=widgets.WHITE,
        ).pack(anchor="w", pady=(0, 4))

        widgets.make_label(
            pad,
            "Re-encrypts all stored chats with your new master password.",
            font=widgets.FONT_SMALL,
            fg=widgets.GRAY_MUTED,
            bg=widgets.WHITE,
        ).pack(anchor="w", pady=(0, 16))

        # Current password
        widgets.make_label(
            pad,
            "Current Password",
            font=widgets.FONT_SMALL,
            fg=widgets.GRAY_TEXT,
            bg=widgets.WHITE,
        ).pack(anchor="w", pady=(0, 4))
        self._old_pw = widgets.make_entry(pad, show="*", width=28)
        self._old_pw.pack(anchor="w", pady=(0, 10), ipady=3)

        # New password
        widgets.make_label(
            pad,
            "New Password",
            font=widgets.FONT_SMALL,
            fg=widgets.GRAY_TEXT,
            bg=widgets.WHITE,
        ).pack(anchor="w", pady=(0, 4))
        self._new_pw = widgets.make_entry(pad, show="*", width=28)
        self._new_pw.pack(anchor="w", pady=(0, 10), ipady=3)

        # Confirm new password
        widgets.make_label(
            pad,
            "Confirm New Password",
            font=widgets.FONT_SMALL,
            fg=widgets.GRAY_TEXT,
            bg=widgets.WHITE,
        ).pack(anchor="w", pady=(0, 4))
        self._confirm_pw = widgets.make_entry(pad, show="*", width=28)
        self._confirm_pw.pack(anchor="w", pady=(0, 10), ipady=3)

        # Error label
        self._error_label = widgets.make_label(
            pad,
            "",
            font=widgets.FONT_SMALL,
            fg=widgets.RED_ERROR,
            bg=widgets.WHITE,
        )
        self._error_label.pack(anchor="w", pady=(0, 12))

        # Buttons
        row = widgets.make_frame(pad, bg=widgets.WHITE)
        row.pack(fill="x")
        widgets.make_button(row, "Save", self._on_save).pack(side="left", padx=(0, 8))
        widgets.make_small_button(row, "Cancel", self.destroy).pack(side="left")

        self.after(50, lambda: self._old_pw.focus_set() if self._old_pw else None)

    def _on_save(self) -> None:
        assert self._old_pw is not None
        assert self._new_pw is not None
        assert self._confirm_pw is not None

        old = self._old_pw.get().strip()
        new = self._new_pw.get().strip()
        confirm = self._confirm_pw.get().strip()

        if not old:
            self._set_error("Please enter your current password.")
            return
        if not new:
            self._set_error("Please enter a new password.")
            return
        if new != confirm:
            self._set_error("New passwords do not match.")
            return
        if len(new) < 4:
            self._set_error("Password must be at least 4 characters.")
            return

        success = security.change_password(
            old_password=old,
            new_password=new,
            reencrypt_callback=sessions.reencrypt_all_sessions,
        )
        if not success:
            self._set_error("Current password is incorrect.")
            return

        self.destroy()

    def _set_error(self, message: str) -> None:
        if self._error_label is not None:
            self._error_label.config(text=message)
