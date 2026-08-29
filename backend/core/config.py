# backend/core/config.py

import os
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


SUBSCRIBERS = {}      
SUBSCRIBED_SITES = set()  # dynamic set of sites
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5173")

DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/agents.db")
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/vectors")

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")