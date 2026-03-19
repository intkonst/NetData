import fastapi
from loguru import logger
from db import Database

class API():
    def __init__(self, Database: Database):
        self.app = fastapi.FastAPI()
        logging.info

    def run(self):
        try:
            print(1 / 0)
        except Exception as e:
            logging.exception(f"API run aborted, class return exitkey 1, exeption log: {e}")
            return 1
        return 0