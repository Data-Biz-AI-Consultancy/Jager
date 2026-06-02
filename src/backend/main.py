from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.api.api import router as api_router
from app.models import Setting

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Jager API",
    description="Backend API for Jager Lead Generator & Opportunity Finder",
    version="1.0.0"
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

# Seed default settings
def seed_default_settings():
    db = SessionLocal()
    try:
        defaults = {
            "ollama_model": "llama3",
            "ollama_url": "http://host.docker.internal:11434",
            "user_profile": "We offer high-quality AI & Data Engineering consultancy services. We specialize in building automated LLM pipelines, dashboard application development, and integrating data systems."
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

@app.on_event("startup")
def startup_event():
    seed_default_settings()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Jager API. Visit /docs for API documentation."}
