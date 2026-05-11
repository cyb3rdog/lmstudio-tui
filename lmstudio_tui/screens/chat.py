from __future__ import annotations

import asyncio
import time as _time

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, RichLog, Select, Static
from textual import work

from ..api.models import ChatCompletionRequest, ChatMessage
from ..state.metrics_store import MetricSample


class ChatScreen(Widget):
    """Interactive chat screen with streaming responses."""

    DEFAULT_CSS = """
    ChatScreen {
        width: 1fr;
        height: 1fr;
    }
    ChatScreen #toolbar {
        height: auto;
        min-height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
    }
    ChatScreen #toolbar-model-row {
        height: 3;
        width: 1fr;
    }
    ChatScreen #toolbar-model-row Label {
        height: 1;
        margin: 1 1 0 0;
        width: auto;
    }
    ChatScreen #model-select { width: 1fr; }
    ChatScreen #toolbar-btns-row {
        height: 3;
        width: auto;
    }
    ChatScreen #btn-clear { margin: 0 1; width: auto; }
    ChatScreen #btn-stop  { margin: 0 0; width: auto; }
    ChatScreen #chat-log {
        height: 1fr;
        padding: 0 1;
    }
    ChatScreen #streaming-row {
        height: auto;
        min-height: 1;
        max-height: 4;
        padding: 0 1 0 1;
        background: $surface-darken-2;
        border-top: dashed $primary-darken-3;
    }
    ChatScreen #streaming-row.-hidden { display: none; }
    ChatScreen #streaming-label {
        width: 1fr;
        color: $text-muted;
    }
    ChatScreen #input-row {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-top: solid $primary-darken-3;
    }
    ChatScreen #chat-input { width: 1fr; }
    ChatScreen #btn-send   { width: 8; margin: 0 0 0 1; }
    ChatScreen #empty-state {
        height: 1fr;
        align: center middle;
        color: $text-muted;
        text-style: italic;
    }
    ChatScreen #empty-state.-hidden { display: none; }

    /* ── Narrow: toolbar stacks into 2 rows ─────────────────────────────── */
    ChatScreen #toolbar.stacked {
        layout: vertical;
        height: auto;
    }
    ChatScreen #toolbar.stacked #toolbar-model-row {
        width: 1fr;
    }
    ChatScreen #toolbar.stacked #toolbar-btns-row {
        width: 1fr;
        height: 3;
    }
    ChatScreen #toolbar.stacked #btn-clear { width: 1fr; }
    ChatScreen #toolbar.stacked #btn-stop  { width: 1fr; }
    """

    BINDINGS = [
        ("ctrl+l", "clear_chat", "Clear"),
    ]

    # Oldest turns beyond this count are dropped to bound memory and API payload size.
    _MAX_HISTORY_TURNS = 40

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: list[ChatMessage] = []
        self._streaming = False
        self._abort = asyncio.Event()

    # ── compose ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal(id="toolbar"):
            with Horizontal(id="toolbar-model-row"):
                yield Label("Model:", id="lbl-model")
                yield Select([], id="model-select", prompt="Select a model…")
            with Horizontal(id="toolbar-btns-row"):
                yield Button("Clear", id="btn-clear", variant="default")
                yield Button("■ Stop", id="btn-stop", variant="error")
        yield Static(
            "[dim]No models loaded — go to Models screen to load one.[/dim]",
            id="empty-state",
        )
        yield RichLog(id="chat-log", markup=True, highlight=False, wrap=True, max_lines=500)
        with Horizontal(id="streaming-row", classes="-hidden"):
            yield Static("", id="streaming-label")
        with Horizontal(id="input-row"):
            yield Input(
                placeholder="Type a message… (Enter to send)",
                id="chat-input",
            )
            yield Button("Send ↵", id="btn-send", variant="primary")

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._sync_stop_button()
        self._populate_models()
        self._update_layout()

    def on_show(self) -> None:
        self._populate_models()

    def on_resize(self) -> None:
        self._update_layout()

    def _update_layout(self) -> None:
        try:
            toolbar = self.query_one("#toolbar")
            lbl = self.query_one("#lbl-model", Label)
            if self.size.width < 60:
                toolbar.add_class("stacked")
                lbl.display = False
            else:
                toolbar.remove_class("stacked")
                lbl.display = True
        except Exception:
            pass

    # ── model selector ────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _populate_models(self) -> None:
        client = self.app.server_registry.active_client
        if not client:
            for _ in range(20):
                await asyncio.sleep(0.25)
                client = self.app.server_registry.active_client
                if client:
                    break
        if not client:
            return
        try:
            models = await client.list_models()
            loaded = [m for m in models if m.is_loaded]
        except Exception:
            return

        sel = self.query_one("#model-select", Select)
        empty = self.query_one("#empty-state", Static)
        log = self.query_one("#chat-log", RichLog)

        if loaded:
            sel.set_options([(m.id, m.id) for m in loaded])
            if sel.value is Select.BLANK:
                sel.value = loaded[0].id
            empty.add_class("-hidden")
            log.remove_class("-hidden")
        else:
            sel.set_options([])
            empty.remove_class("-hidden")
            log.add_class("-hidden")

    # ── events ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-send":
                self._send_message()
            case "btn-clear":
                self.action_clear_chat()
            case "btn-stop":
                self._abort.set()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            self._send_message()

    # ── send / stream ─────────────────────────────────────────────────────────

    def _send_message(self) -> None:
        if self._streaming:
            self.notify("Wait for response to finish or press Stop", severity="warning")
            return

        inp = self.query_one("#chat-input", Input)
        text = inp.value.strip()
        if not text:
            return

        sel = self.query_one("#model-select", Select)
        if sel.value is Select.BLANK:
            self.notify("Select a model first", severity="warning")
            return

        model_id = str(sel.value)
        inp.value = ""
        self._history.append(ChatMessage(role="user", content=text))
        # Drop oldest turns to keep history bounded (saves memory + API payload size).
        # Keep pairs: trim from the front in steps of 2 (user+assistant).
        max_msgs = self._MAX_HISTORY_TURNS * 2
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]

        try:
            log = self.query_one("#chat-log", RichLog)
            log.write(Text.from_markup(f"[bold cyan]You:[/bold cyan] {text}"))
        except Exception:
            pass

        self._stream_response(model_id)

    @work
    async def _stream_response(self, model_id: str) -> None:
        client = self.app.server_registry.active_client
        if not client:
            self.notify("No server connected", severity="error")
            return

        self._streaming = True
        self._abort.clear()
        self._sync_stop_button()

        # Guard all widget queries: widget may be unmounted if user quits mid-stream.
        try:
            streaming_row = self.query_one("#streaming-row")
            streaming_label = self.query_one("#streaming-label", Static)
        except Exception:
            self._streaming = False
            self._sync_stop_button()
            return

        try:
            streaming_row.remove_class("-hidden")
            streaming_label.update("[dim]▌[/dim]")
        except Exception:
            pass

        req = ChatCompletionRequest(
            model=model_id,
            messages=self._history,
            temperature=0.7,
        )

        collected: list[str] = []
        t0 = _time.perf_counter()
        t_first: float | None = None
        chunk_count = 0

        try:
            async for chunk in client.chat_completion_stream(req):
                if self._abort.is_set():
                    break
                if t_first is None:
                    t_first = _time.perf_counter()
                chunk_count += 1
                collected.append(chunk)
                preview = "".join(collected)
                if len(preview) > 300:
                    display = "…" + preview[-297:]
                else:
                    display = preview
                try:
                    streaming_label.update(
                        Text.from_markup(f"[green]Assistant:[/green] {display}[dim]▌[/dim]")
                    )
                except Exception:
                    pass
        except Exception as e:
            self.notify(str(e), severity="error")

        total_ms = (_time.perf_counter() - t0) * 1000.0
        ttft_ms = (t_first - t0) * 1000.0 if t_first is not None else None
        tps = (chunk_count / total_ms * 1000.0) if total_ms > 0 and chunk_count > 0 else None
        try:
            prompt_tokens = sum(len(m.content) // 4 for m in self._history if isinstance(m.content, str))
            self.app.metrics_store.record(
                self.app.server_registry.active_name,
                MetricSample.now(
                    model_id=model_id,
                    tps=tps,
                    ttft_ms=ttft_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=chunk_count,
                ),
            )
        except Exception:
            pass

        full_response = "".join(collected)

        try:
            self.query_one("#streaming-row").add_class("-hidden")
            self.query_one("#streaming-label", Static).update("")
        except Exception:
            pass

        if full_response:
            self._history.append(ChatMessage(role="assistant", content=full_response))
            try:
                log = self.query_one("#chat-log", RichLog)
                log.write(Text.from_markup(f"[green]Assistant:[/green] {full_response}"))
                log.write(Text.from_markup("[dim]─────[/dim]"))
            except Exception:
                pass

        self._streaming = False
        self._abort.clear()
        self._sync_stop_button()
        try:
            self.query_one("#chat-input", Input).focus()
        except Exception:
            pass

    # ── actions ───────────────────────────────────────────────────────────────

    def action_clear_chat(self) -> None:
        self._history.clear()
        try:
            self.query_one("#chat-log", RichLog).clear()
            self.query_one("#streaming-row").add_class("-hidden")
            self.query_one("#streaming-label", Static).update("")
        except Exception:
            pass

    def _sync_stop_button(self) -> None:
        try:
            btn = self.query_one("#btn-stop", Button)
            btn.disabled = not self._streaming
        except Exception:
            pass
