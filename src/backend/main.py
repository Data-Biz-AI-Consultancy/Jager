from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.api.api import router as api_router
from app.models import Setting

# Seed default settings
def seed_default_settings():
    db = SessionLocal()
    try:
        defaults = {
            "ollama_model": "llama3",
            "ollama_url": "http://host.docker.internal:11434",
            "user_profile": "We offer high-quality AI & Data Engineering consultancy services. We specialize in building automated LLM pipelines, dashboard application development, and integrating data systems.",
            "reddit_user_token": ""
        }
        for key, value in defaults.items():
            exists = db.query(Setting).filter(Setting.key == key).first()
            if not exists:
                setting = Setting(key=key, value=value)
                db.add(setting)
        db.commit()
    except Exception as e:
        print(f"Error seeding default settings: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    Base.metadata.create_all(bind=engine)
    seed_default_settings()
    yield

app = FastAPI(
    title="Jager API",
    description="Backend API for Jager Lead Generator & Opportunity Finder",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(api_router)

import os
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def read_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "..", "frontend", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard index.html not found</h1>", status_code=404)
