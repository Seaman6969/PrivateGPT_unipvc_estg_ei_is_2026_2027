from __future__ import annotations

import subprocess
import threading
import tkinter as tk
from tkinter import messagebox

from chat import controller
from config import sessions
from config.sessions import Session, SessionMeta
from ollama import server
from rag import build_index, index_session_memory, remove_session_memory
from utils.errors import Error

from . import chat_panel, greeter, session_panel, widgets

DEFAULT_OLLAMA_PORT: int = 11434
OLLAMA_BOOT_TIMEOUT_SECONDS: float = 30.0


class MainWindow:
    
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.port: int | None = None
        self.model: str = ""
        self._container: tk.Frame | None = None
        self._greeter: greeter.Greeter | None = None
        self._chat: chat_panel.ChatPanel | None = None
        self._sessions: session_panel.SessionPanel | None = None
        self._current_session: str | None = None
        self._ollama_proc: subprocess.Popen | None = None
        self._response_buffer: list[str] = []
        self._stop_event: threading.Event | None = None
        self._setup()

    def _setup(self) -> None:
        self._configure_root()
        self._build_toolbar()
        self._build_container()
        self._boot_ollama()
        self._show_greeter()
        self._greeter.set_status("Preparing models...")
        threading.Thread(target=self._ensure_models_worker, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)

    def _ensure_models_worker(self) -> None:
        port = controller.detect_port()
        err = controller.ensure_models(
            port=port,
            on_status=lambda s: self.root.after(0, self._set_greeter_status, s),
        ) if port else Error(message="Ollama not running")
        self.root.after(0, self._models_ready, err)
    
    def _configure_root(self) -> None:
        self.root.title("LocalGPT")
        self.root.geometry("900x680")
        self.root.minsize(720, 560)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

    def _build_toolbar(self) -> None:
        bar = widgets.make_frame(self.root, bg=widgets.WHITE)
        bar.grid(row=0, column=0, sticky="ew")
        widgets.make_title(bar, "LocalGPT").pack(side="left", padx=18, pady=12)
        widgets.make_small_button(bar, "← Back", self._show_greeter).pack(
            side="right", padx=18, pady=12,
        )

    def _build_container(self) -> None:
        self._container = widgets.make_frame(self.root)
        self._container.grid(row=1, column=0, sticky="nsew")

    def _boot_ollama(self) -> None:
        if server.is_running():
            return
        try:
            self._ollama_proc = server.start(port=DEFAULT_OLLAMA_PORT)
        except OSError:
            self._ollama_proc = None
            messagebox.showerror(
                "Ollama not found",
                "Ollama is not installed. Install it from https://ollama.com and restart LocalGPT.",
            )
            return
        server.wait_until_ready(port=DEFAULT_OLLAMA_PORT, timeout=OLLAMA_BOOT_TIMEOUT_SECONDS)
    
    def _detect(self) -> None:
        self.port = controller.detect_port()
        self.model = controller.default_model(self.port) if self.port else ""

    def _show_greeter(self) -> None:
        self._clear_container()
        self._greeter = greeter.Greeter(
            self._container,
            on_chat=self._show_chat,
            on_refresh=self._refresh_index,
        )
        self._greeter.pack(fill="both", expand=True)
        self._greeter.set_status(self._status_text())

    def _show_chat(self) -> None:
        if not self.model:
            messagebox.showinfo("Please wait", "Models are still being prepared (or Ollama is unavailable).")
            return
        self._build_chat_view()
        self._open_current_session()
        self._apply_chat_header()
     
    def _render_session_by_id(self, session_id: str) -> None:
        if self._chat is None:
            return
        session: Session | Error = sessions.load_session(session_id=session_id)
        if isinstance(session, Error):
            messagebox.showerror(
                "Could not load session", str(session), parent=self.root,
            )
            return
        self._current_session = session_id
        if self._sessions is not None:
            self._sessions.select(session_id=session_id)
        self._render_session(session=session)  
         
    def _open_current_session(self) -> None:
        assert self._sessions is not None
        self._sessions.reload()
        self._activate_picked_session()


    def _activate_picked_session(self) -> None:
        session_id: str | None = self._pick_active_session_id()
        if session_id is None:
            self._new_session()
            return
        self._render_session_by_id(session_id=session_id)
        
    def _apply_chat_header(self) -> None:
        if self._chat is None or not self.port:
            return
        self._chat.set_status(f"Connected on port {self.port}")
        self._chat.set_model(self.model)
    
    def _build_chat_view(self) -> None:
        self._clear_container()
        self._sessions = session_panel.SessionPanel(
            self._container,
            on_select=self._load_session,
            on_new=self._new_session,
            on_deleted=self._on_session_deleted,
        )
        self._sessions.pack(side="left", fill="y")
        self._chat = chat_panel.ChatPanel(
            self._container,
            on_send=self.on_send,
            on_modes_changed=self._on_modes_changed,
            on_stop=self._stop,
        )
        self._chat.pack(side="right", fill="both", expand=True)
            
    def _refresh_index(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            report, manifest = build_index(force=True)
            summary: str = report.summary()
            total: int = len(manifest.all())
            errors: list[str] = list(report.errors)
        except Exception as exc:
            summary = f"failed: {exc}"
            total = 0
            errors = [str(exc)]
        self.root.after(0, self._refresh_done, summary, total, errors)

    def _refresh_done(self, summary: str, total: int, errors: list[str] | None = None) -> None:
        errors = errors or []
        if self._greeter is not None:
            self._greeter.refresh_done(summary=summary, total=total, errors=errors)
            return
        if errors:
            messagebox.showerror(
                "Knowledge base refresh had errors",
                summary + "\n\n" + "\n".join(errors),
            )
        elif self._chat is not None:
            self._chat.set_status(summary)

    def _status_text(self) -> str:
        if self.port:
            return f"Ollama connected on port {self.port}"
        return "Ollama not running"

    def _clear_container(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()
        self._greeter = None
        self._chat = None

    def _on_quit(self) -> None:
        server.stop(proc=self._ollama_proc)
        self.root.destroy()

    def on_send(self, prompt: str) -> None:
        if not self.port or self._chat is None:
            return

        history: list[dict[str, str]] = []
        if self._current_session is not None:
            sess = sessions.load_session(session_id=self._current_session)
            if not isinstance(sess, Error):
                history = [dict(m) for m in sess.messages]

        self._append_session_message(role="user", content=prompt)
        self._response_buffer.clear()
        self._chat.append_user(prompt)
        self._chat.begin_response()
        self._chat.disable_input()
        attachments = self._chat.get_attachments()
        modes = self._chat.get_modes()
        self._stop_event = threading.Event()
        threading.Thread(
            target=self._send_worker,
            args=(prompt, attachments, modes, history),
            daemon=True,
        ).start()

    def _send_worker(self, prompt: str, attachments, modes, history: list[dict[str, str]]) -> None:
        controller.send(
            root=self.root, port=self.port, model=self.model, prompt=prompt,
            attachments=attachments, modes=modes,
            on_token=self._emit, on_thinking=self._emit_thinking,
            on_done=self._on_done_threadsafe,
            stop_event=self._stop_event,
            history=history,
        )

    def _on_done_threadsafe(self, result) -> None:
        self.root.after(0, self._done, result)

    def _stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()


    def _emit(self, token: str) -> None:
        self._response_buffer.append(token)
        self.root.after(0, self._chat.append_token, token)

    def _emit_thinking(self, token: str) -> None:
        self.root.after(0, self._chat.append_thinking, token)

    def _append_session_message(self, role: str, content: str) -> None:
        if self._current_session is None:
            return
        result = sessions.append_message(
            session_id=self._current_session, role=role, content=content,
        )
        if isinstance(result, Error):
            print(f"[session] failed to persist message: {result}")
        
    def _done(self, result) -> None:
        if self._chat is None:
            return
        self._chat.end_response()
        self._chat.enable_input()
        self._chat.clear_attachments()
        self._stop_event = None

        response_text: str = "".join(self._response_buffer)
        self._response_buffer.clear()

        if isinstance(result, (Error, Exception)):
            self._chat.append_system(f"Error: {result}")
            if response_text:
                self._append_session_message(role="assistant", content=response_text)
                self._trigger_memory_index()
            return

        if response_text:
            self._append_session_message(role="assistant", content=response_text)
            self._trigger_memory_index()

    def _trigger_memory_index(self) -> None:
        if self._current_session is None:
            return
        session_id = self._current_session
        threading.Thread(
            target=self._index_session_memory_worker,
            args=(session_id,),
            daemon=True,
        ).start()

    def _index_session_memory_worker(self, session_id: str) -> None:
        sess = sessions.load_session(session_id=session_id)
        if not isinstance(sess, Error):
            index_session_memory(session=sess)
            
    def _load_or_create_session(self) -> None:
        assert self._sessions is not None
        self._sessions.reload()
        known_ids: set[str] = {meta.id for meta in self._sessions.metas()}
        if self._current_session is None or self._current_session not in known_ids:
            self._new_session()
            return
        self._sessions.select(session_id=self._current_session)
        
    def _new_session(self) -> None:
        session: Session = sessions.create_session()
        self._current_session = session.meta.id
        self._sync_session_panel(session_id=self._current_session)
        self._reset_chat_messages()
        if self._chat is not None:
            self._chat.set_modes([])

    def _sync_session_panel(self, session_id: str) -> None:
        if self._sessions is None:
            return
        self._sessions.reload()
        self._sessions.select(session_id=session_id)

    def _reset_chat_messages(self) -> None:
        if self._chat is not None:
            self._chat.clear_messages()

    def _load_session(self, session_id: str) -> None:
        self._render_session_by_id(session_id=session_id)

    def _render_session(self, session: Session) -> None:
        self._chat.clear_messages()
        self._chat.set_modes(session.modes)
        for msg in session.messages:
            self._chat.append_user(msg["content"]) if msg["role"] == "user" else self._chat.append_system(msg["content"])

    
    def _set_greeter_status(self, text: str) -> None:
        if self._greeter is not None:
            self._greeter.set_status(text)
            
    def _pick_active_session_id(self) -> str | None:
        assert self._sessions is not None
        metas: list[SessionMeta] = self._sessions.metas()
        if not metas:
            return None
        known_ids: set[str] = {meta.id for meta in metas}
        if self._current_session is not None and self._current_session in known_ids:
            return self._current_session
        return metas[0].id
    
    def _on_session_deleted(self, session_id: str) -> None:
        threading.Thread(
            target=remove_session_memory,
            args=(session_id,),
            daemon=True,
        ).start()
        if session_id != self._current_session:
            return
        self._current_session = None
        self._activate_picked_session()
    
    def _on_modes_changed(self, modes: set[str]) -> None:
        if self._current_session is None:
            return
        result = sessions.set_modes(
            session_id=self._current_session, modes=sorted(modes),
        )
        if isinstance(result, Error):
            print(f"[session] failed to persist modes: {result}")
            
    def _models_ready(self, err) -> None:
        self._detect()
        if self._greeter is not None:
            self._greeter.set_status(str(err) if err else self._status_text())