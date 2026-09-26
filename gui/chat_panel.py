import tkinter as tk

from chat import modes as m
from config import sessions
from utils.errors import Error

from . import attachments_bar, chat_bubble, widgets


class ChatPanel(tk.Frame):
    def __init__(self, parent, on_send, on_modes_changed=None,on_tokenless_requested=None, on_stop=None):
        super().__init__(parent, bg=widgets.INDIGO_GHOST, bd=0)
        self.on_send = on_send
        self._canvas = None
        self._stream = None
        self._input = None
        self._status = None
        self._model = None
        self._thinking = None
        self._assistant = None
        self._attachments = None
        self._stop_button = None
        self.on_modes_changed = on_modes_changed
        self.on_tokenless_requested = on_tokenless_requested
        self.on_stop = on_stop
        self._mode_vars: dict[str, tk.BooleanVar] = {}
        self._build()


    def _build(self) -> None:
        self._build_header()
        self._build_stream()
        self._build_input()

    def _build_header(self) -> None:
        bar = self._make_header_frame()
        self._status = self._make_status(bar)
        self._model = self._make_model(bar)
        self._divider()

    def _make_header_frame(self) -> tk.Frame:
        bar = widgets.make_frame(self, bg=widgets.WHITE)
        bar.pack(fill="x")
        return bar

    def _make_status(self, parent) -> tk.Label:
        label = widgets.make_label(parent, "starting...", fg=widgets.GRAY_MUTED)
        label.pack(side="left", padx=18, pady=10)
        return label

    def _make_model(self, parent) -> tk.Label:
        label = widgets.make_label(parent, "", fg=widgets.INDIGO_DEEP)
        label.pack(side="right", padx=18, pady=10)
        return label

    def _divider(self) -> None:
        widgets.make_separator(self).pack(fill="x")

    def _build_stream(self) -> None:
        wrapper = self._make_wrapper()
        self._canvas = self._make_canvas(wrapper)
        self._stream = self._make_stream_frame(self._canvas)
        self._wire_scroll(wrapper)
        self._wire_resize()

    def set_modes(self, modes: list[str]) -> None:
        active = set(modes)
        for name, var in self._mode_vars.items():
            var.set(name in active)
        

    def _make_wrapper(self) -> tk.Frame:
        wrapper = widgets.make_frame(self)
        wrapper.pack(fill="both", expand=True)
        return wrapper

    def _make_canvas(self, parent) -> tk.Canvas:
        canvas = widgets.make_canvas(parent)
        canvas.pack(side="left", fill="both", expand=True)
        return canvas

    def _make_stream_frame(self, canvas) -> tk.Frame:
        frame = widgets.make_frame(canvas)
        canvas.create_window((0, 0), window=frame, anchor="nw", tags="stream")
        return frame

    def _add_mode_checkbox(self, parent, name: str) -> None:
        var = tk.BooleanVar(value=(name == m.DEFAULT))
        self._mode_vars[name] = var
        box = widgets.make_checkbox(parent, name, var, lambda n=name: self._on_toggle(n))
        box.pack(side="left", padx=(0, 14))

    def _wire_scroll(self, parent) -> None:
        bar = widgets.attach_scrollbar(parent, self._canvas)
        bar.pack(side="right", fill="y")

    def _wire_resize(self) -> None:
        self._stream.bind("<Configure>", self._on_stream_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_stream_configure(self, _event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfig("stream", width=event.width)

    def _build_input(self) -> None:
        container = self._make_input_container()
        self._build_attach_row(container)
        self._build_input_row(container)
        self._build_modes_row(container)

    def _make_input_container(self) -> tk.Frame:
        container = widgets.make_frame(self, bg=widgets.WHITE)
        container.pack(fill="x", padx=18, pady=(10, 14))
        return container

    def _build_attach_row(self, parent) -> None:
        self._attachments = attachments_bar.AttachmentsBar(parent)
        self._attachments.pack(fill="x", pady=(0, 6))

    def _build_input_row(self, parent) -> None:
        row = widgets.make_frame(parent, bg=widgets.WHITE)
        row.pack(fill="x")
        self._input = self._make_input(row)
        self._bind_keys()
        self._make_send_button(row)
        self._make_stop_button(row)


    def _make_input(self, parent) -> tk.Text:
        widget = widgets.make_text(parent, height=3)
        widget.pack(side="left", fill="both", expand=True)
        widget.focus_set()
        return widget

    def _bind_keys(self) -> None:
        self._input.bind("<Return>", self._on_enter)
        self._input.bind("<Shift-Return>", self._on_shift_enter)

    def _on_enter(self, _event) -> str:
        self._send()
        return "break"

    def _on_shift_enter(self, _event) -> None:
        self._input.insert("insert", "\n")

    def _make_send_button(self, parent) -> None:
        button = widgets.make_button(parent, "Send", self._send)
        button.pack(side="right", padx=(10, 8), pady=8)

    def _make_stop_button(self, parent) -> None:
        self._stop_button = widgets.make_button(parent, "STOP", self._on_stop)
        self._stop_button.pack(side="right", padx=(10, 8), pady=8)
        self._stop_button.config(bg="#d32f2f", activebackground="#b71c1c")
        self._stop_button.config(state="disabled")

    def _on_stop(self) -> None:
        if self.on_stop is not None:
            self.on_stop()

    def _build_modes_row(self, parent) -> None:
        row = widgets.make_frame(parent, bg=widgets.WHITE)
        row.pack(fill="x", pady=(6, 0))
        for name in m.ALL:
            self._add_mode_checkbox(row, name)

    def _on_toggle(self, name: str) -> None:
        if not self.get_modes():          
            self._mode_vars[name].set(True)
        if self.on_modes_changed is not None:
            self.on_modes_changed(self.get_modes())

    def get_modes(self) -> set[str]:
        return {n for n, v in self._mode_vars.items() if v.get()}

    def get_attachments(self) -> list[tuple[str, str]]:
        return self._attachments.get_files()

    def clear_attachments(self) -> None:
        self._attachments.clear()

    def _send(self) -> None:
        text = self._read()
        if not text:
            return
        self._clear()
        self.on_send(text)

    def _read(self) -> str:
        return self._input.get("1.0", "end").strip()

    def _clear(self) -> None:
        self._input.delete("1.0", "end")

    def _scroll_bottom(self) -> None:
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    def _add_bubble(self, role: str) -> chat_bubble.MessageBubble:
        bubble = chat_bubble.MessageBubble(self._stream, role)
        bubble.pack(fill="x")
        self._scroll_bottom()
        return bubble

    def set_status(self, text: str) -> None:
        self._status.config(text=text)

    def set_model(self, model: str) -> None:
        self._model.config(text=model)

    def append_user(self, prompt: str) -> None:
        self._add_bubble("user").set_text(prompt)

    def append_system(self, text: str) -> None:
        self._add_bubble("assistant").set_text(text)

    def begin_response(self) -> None:
        self._thinking = None
        self._assistant = None

    def append_thinking(self, token: str) -> None:
        if self._thinking is None:
            self._thinking = self._add_bubble("thinking")
        self._thinking.append(token)
        self._scroll_bottom()

    def append_token(self, token: str) -> None:
        if self._assistant is None:
            self._assistant = self._add_bubble("assistant")
        self._assistant.append(token)
        self._scroll_bottom()

    def end_response(self) -> None:
        self._thinking = None
        self._assistant = None

    def disable_input(self) -> None:
        self._input.config(state="disabled")
        if self._stop_button is not None:
            self._stop_button.config(state="normal")

    def enable_input(self) -> None:
        self._input.config(state="normal")
        self._input.focus_set()
        if self._stop_button is not None:
            self._stop_button.config(state="disabled")

    def set_mode(self, name: str, value: bool) -> None:
        if name in self._mode_vars:
            self._mode_vars[name].set(value)

    def clear_messages(self) -> None:
        for child in self._stream.winfo_children():
            child.destroy()
