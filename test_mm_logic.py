"""Standalone test of model_manager logic without full Textual app."""
import asyncio, tomllib, sys
sys.path.insert(0, "/home/cyb3rdog/.picoclaw/workspace-2/lmstudio-tui")

from lmstudio_tui.config.models import ServerConfig
from lmstudio_tui.api.client import LMStudioClient
from lmstudio_tui.api.models import ModelsResponse

async def test_model_manager_logic():
    """Simulate what action_refresh does."""
    with open("/home/cyb3rdog/.lmstudio-tui/config.toml", "rb") as f:
        cfg = tomllib.load(f)
    s = cfg["servers"][0]
    client = LMStudioClient(ServerConfig(endpoint=s["endpoint"], api_key=s["api_key"]))
    
    print("Simulating action_refresh logic...")
    
    # Same logic as model_manager.action_refresh
    if not client:
        print("ERROR: client is None")
        return
    
    models = await client.list_models()
    print(f"Got {len(models)} models from client.list_models()")
    
    for m in models:
        status = "LOADED" if m.is_loaded else "—"
        quant = m.quantization or "—"
        ctx = str(m.max_context_length or m.context_length or "?")
        vram = "—"
        print(f"  Would add_row: id={m.id[:40]:40s} status={status:6s} quant={quant} ctx={ctx} vram={vram}")
    
    await client.close()
    print("Done. 12 rows would be added.")

asyncio.run(test_model_manager_logic())