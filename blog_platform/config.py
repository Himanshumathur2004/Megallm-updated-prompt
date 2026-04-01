"""Configuration for Blog Generation Platform."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Base configuration."""
    
    # MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB = os.getenv("MONGODB_DB", "megallm_blog_platform")
    
    # API Configuration - Support MegaLLM or OpenRouter
    USE_OPENROUTER = os.getenv("USE_OPENROUTER", "true").lower() == "true"
    
    if USE_OPENROUTER:
        # OpenRouter API - Use OpenRouter key for OpenRouter endpoint
        MEGALLM_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
        MEGALLM_BASE_URL = "https://openrouter.ai/api/v1"
        MEGALLM_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus-preview:free")
    else:
        # MegaLLM API (fallback)
        MEGALLM_API_KEY = os.getenv("MEGALLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        MEGALLM_BASE_URL = "https://ai.megallm.io/v1"
        MEGALLM_MODEL = os.getenv("MEGALLM_MODEL", "deepseek-ai/deepseek-v3.1")
    
    # Blog Generation Config
    BLOG_WORD_COUNT_MIN = 500
    BLOG_WORD_COUNT_MAX = 800
    BLOG_TEMPERATURE = 0.65
    BLOG_MAX_TOKENS = 2000
    
    # Schedule Config
    BLOGS_PER_24_HOURS = 12  # 3 per topic × 4 topics
    GENERATION_INTERVAL_MINUTES = 120  # Generate 12 blogs every 24 hours means 1 every 2 hours
    
    # Topics (4 CTO-focused topics for MegaLLM)
    TOPICS = {
        "cost_optimization": {
            "name": "Cost Optimization",
            "description": "Reducing inference costs and optimizing spending",
            "keywords": ["cost", "pricing", "budget", "optimization", "tokens per dollar"],
            "blogs_per_cycle": 3
        },
        "performance": {
            "name": "Performance & Speed",
            "description": "Latency reduction and throughput optimization",
            "keywords": ["latency", "speed", "throughput", "performance", "tokens per second"],
            "blogs_per_cycle": 3
        },
        "reliability": {
            "name": "Reliability & Uptime",
            "description": "Ensuring production stability and failover strategies",
            "keywords": ["reliability", "uptime", "failover", "SLA", "monitoring"],
            "blogs_per_cycle": 3
        },
        "infrastructure": {
            "name": "Infrastructure & Compliance",
            "description": "Data residency, GDPR, and regional deployment",
            "keywords": ["compliance", "GDPR", "data residency", "infrastructure", "security"],
            "blogs_per_cycle": 3
        }
    }
    
    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Accounts (predefined)
    ACCOUNTS = [
        {"id": "account_1", "name": "Account 1", "description": "Main content account"},
        {"id": "account_2", "name": "Account 2", "description": "Secondary publication"},
        {"id": "account_3", "name": "Account 3", "description": "Backup content"},
        {"id": "account_4", "name": "Account 4", "description": "Regional focus"},
        {"id": "account_5", "name": "Account 5", "description": "Specialized topics"},
    ]
