import os
# Set database URL environment variable to sqlite for tests before importing modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import sys
from os.path import dirname, abspath, join
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to Python path
sys.path.insert(0, join(dirname(dirname(abspath(__file__))), "src", "backend"))

from app.database import Base, get_db
from app.models import Setting
from main import app

# SQLite in-memory database URL for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(name="db_engine", scope="session")
def fixture_db_engine():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
    yield engine
    engine.dispose()

@pytest.fixture(name="db", scope="function")
def fixture_db(db_engine):
    # Create the tables in the in-memory test database
    Base.metadata.create_all(bind=db_engine)
    
    connection = db_engine.connect()
    transaction = connection.begin()
    
    Session = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = Session()
    
    # Seed default settings in test db for tests that expect them
    defaults = {
        "ollama_model": "llama3",
        "ollama_url": "http://host.docker.internal:11434",
        "user_profile": "We offer high-quality AI & Data Engineering consultancy services. We specialize in building automated LLM pipelines, dashboard application development, and integrating data systems."
    }
    for key, value in defaults.items():
        setting = Setting(key=key, value=value)
        session.add(setting)
    session.commit()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
    
    # Drop all tables after the test runs
    Base.metadata.drop_all(bind=db_engine)

@pytest.fixture(name="client", scope="function")
def fixture_client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    # Override database dependency in FastAPI
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    # Reset dependency override
    app.dependency_overrides.clear()
