# Machine Learning App

This directory contains the machine learning application written in Python. It provides scripts and models for predicting optimal LinkedIn publishing timeslots based on post features and engagement statistics.

The service is packaged inside the **`ml`** container service.

## Directory Structure

*   `linkedin_publishing_timeslot/`: Core training, prediction, and feature processing pipelines for the LinkedIn timeslot prediction use case.
*   `main.py`: FastAPI service exposing endpoints (e.g. `/train`, `/predict`, `/backtest`) for execution and orchestration.
*   `train.py` / `predict.py` / `backtest.py`: Top-level orchestration scripts.
*   `utils.py`: Common helper functions and utilities.
*   `Dockerfile` & `requirements.txt`: Container packaging and Python dependencies.

## Usage

The ML service is typically triggered by N8N workflows or downstream pipelines via HTTP endpoints. Refer to `main.py` for API routes and payload definitions.
