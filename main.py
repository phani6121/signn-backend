from dotenv import load_dotenv
import logging
from pathlib import Path
from fastapi import FastAPI
from app.api.v1.api import api_router

env_path = Path(__file__).resolve().parent / ".env.local"
load_dotenv(dotenv_path=env_path, override=False)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Gig-worker API", version="1.0.0")

app.include_router(api_router)
