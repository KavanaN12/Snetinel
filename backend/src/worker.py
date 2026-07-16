"""Entrypoint for the discovery worker service."""

import asyncio

from src.modules.discovery.services.discovery_worker import main


if __name__ == "__main__":
    asyncio.run(main())
