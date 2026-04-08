import asyncio
import os
import sys

from src.routers.translation_router import _llm_translate
import logging

logging.basicConfig(level=logging.ERROR)

async def main():
    try:
        res = await _llm_translate("Confirm", "hi")
        print("OUTPUT:", res)
    except Exception as e:
        print("ERROR:", e)

asyncio.run(main())
