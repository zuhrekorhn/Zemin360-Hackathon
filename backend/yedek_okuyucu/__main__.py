"""`python -m yedek_okuyucu` (backend klasöründen): servisi `PORT`'ta (varsayılan 8100) açar."""

import logging
import os

import uvicorn

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "yedek_okuyucu.app:app",
        host=os.environ.get("YEDEK_OKUYUCU_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8100")),
    )
