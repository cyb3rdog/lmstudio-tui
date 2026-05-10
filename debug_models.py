import asyncio, sys, tomllib
sys.path.insert(0, "/home/cyb3rdog/.picoclaw/workspace-2/lmstudio-tui")
from lmstudio_tui.api.client import LMStudioClient
from lmstudio_tui.config.models import ServerConfig
from lmstudio_tui.api.models import ModelsResponse

async def debug():
    with open("/home/cyb3rdog/.lmstudio-tui/config.toml", "rb") as f:
        cfg = tomllib.load(f)
    s = cfg["servers"][0]
    client = LMStudioClient(ServerConfig(endpoint=s["endpoint"], api_key=s["api_key"]))
    
    raw = await client._get("/api/v1/models")
    resp = ModelsResponse.from_raw(raw)
    models = resp.model_list
    
    print(f"Total models: {len(models)}")
    print(f"Loaded count: {sum(1 for m in models if m.is_loaded)}")
    print()
    for m in models:
        inst = m.instance_id
        print(f"  id={m.id[:50]:50s} is_loaded={m.is_loaded:5} instance={inst}")

asyncio.run(debug())