import asyncio, sys, tomllib, json
sys.path.insert(0, "/home/cyb3rdog/.picoclaw/workspace-2/lmstudio-tui")
from lmstudio_tui.api.client import LMStudioClient
from lmstudio_tui.config.models import ServerConfig

async def debug():
    with open("/home/cyb3rdog/.lmstudio-tui/config.toml", "rb") as f:
        cfg = tomllib.load(f)
    s = cfg["servers"][0]
    client = LMStudioClient(ServerConfig(endpoint=s["endpoint"], api_key=s["api_key"]))
    
    raw = await client._get("/api/v1/models")
    print(json.dumps(raw, indent=2))

asyncio.run(debug())