import uvicorn

from gateway.config import Settings
from gateway.main import create_app

if __name__ == "__main__":
    settings = Settings.from_env()
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
