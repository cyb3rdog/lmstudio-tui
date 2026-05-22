from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lmstudio-tui",
        description="Terminal UI for LM Studio — management, monitoring and benchmarking",
    )
    parser.add_argument("--endpoint", "-e", metavar="URL", help="LM Studio server URL (e.g. http://localhost:1234)")
    parser.add_argument("--api-key", "-k", metavar="TOKEN", help="Bearer API token")
    args = parser.parse_args()

    from .app import create_app
    app = create_app(endpoint=args.endpoint, api_key=args.api_key)
    app.run()


if __name__ == "__main__":
    main()
