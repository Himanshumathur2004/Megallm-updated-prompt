#!/usr/bin/env python3
"""Test OpenRouter API connection."""

import requests
import json
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_openrouter():
    """Test OpenRouter API."""
    logger.info(f"Testing OpenRouter API...")
    logger.info(f"API Key: {Config.MEGALLM_API_KEY[:20]}...")
    logger.info(f"Base URL: {Config.MEGALLM_BASE_URL}")
    logger.info(f"Model: {Config.MEGALLM_MODEL}")
    
    headers = {
        "Authorization": f"Bearer {Config.MEGALLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": Config.MEGALLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello' in one word."}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        logger.info(f"\nSending request to {Config.MEGALLM_BASE_URL}/chat/completions")
        response = requests.post(
            f"{Config.MEGALLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ API Response Success!")
            logger.info(f"Response: {json.dumps(data, indent=2)[:500]}...")
            return True
        else:
            logger.error(f"✗ API Error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Connection Error: {e}")
        return False

if __name__ == "__main__":
    success = test_openrouter()
    exit(0 if success else 1)
