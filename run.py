import asyncio
import sys

# Must be set before uvicorn creates the event loop.
# Playwright needs ProactorEventLoop on Windows to spawn subprocesses.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
