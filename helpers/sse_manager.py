# sse_manager.py

import asyncio

# 1. This is our central "signal".
#    Think of it like a flag that can be raised.
update_event = asyncio.Event()

async def trigger_update():
    """
    This is the simple "trigger function" you will call from anywhere
    in your application after you've changed the database.
    It raises the flag.
    """
    print("Signal Triggered: Notifying all connected clients of an update.")
    update_event.set()
