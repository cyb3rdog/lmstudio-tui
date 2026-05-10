import asyncio, tomllib, sys, traceback
sys.path.insert(0, "/home/cyb3rdog/.picoclaw/workspace-2/lmstudio-tui")

# Patch model_manager to add debug logging
import lmstudio_tui.screens.model_manager as mm
original_refresh = mm.ModelManager.action_refresh

async def debug_refresh(self):
    print(f"[DEBUG] action_refresh called, cursor_row={getattr(self, '_dl_timer', None)}")
    try:
        client = self.app.server_registry.active_client
        print(f"[DEBUG] client={client}")
        if not client:
            print("[DEBUG] no client, returning")
            return
        models = await client.list_models()
        print(f"[DEBUG] got {len(models)} models")
        table = self.query_one("#models-table", mm.DataTable)
        print(f"[DEBUG] table found, clearing")
        table.clear()
        for i, m in enumerate(models):
            print(f"[DEBUG] adding row {i}: {m.id[:40]}")
            table.add_row(m.id, "LOADED" if m.is_loaded else "—", m.quantization or "—", str(m.max_context_length or "?"), "—", key=m.id)
        print(f"[DEBUG] done, {len(models)} rows added")
    except Exception as e:
        print(f"[DEBUG] ERROR: {e}")
        traceback.print_exc()

mm.ModelManager.action_refresh = debug_refresh

# Now run the app
from textual.app import App
from lmstudio_tui.config.loader import load_config
from lmstudio_tui.app import create_app

config = load_config()
app = create_app()
app.run()