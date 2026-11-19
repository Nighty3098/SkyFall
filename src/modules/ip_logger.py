from loguru import logger

class IpLogger:
    def __init__(self):
        logger.debug("Init: IP Logger")

    async def start_server(self, port: str):
        pass
