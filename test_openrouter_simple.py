#!/usr/bin/env python
"""Simple test of OpenRouter blog generation"""

import sys
sys.path.insert(0, 'blog_platform')

from config import Config
from blog_generator import BlogGenerator
from dotenv import load_dotenv

load_dotenv()

print("Testing OpenRouter Blog Generation")
print("="*60)

generator = BlogGenerator(
    Config.OPENROUTER_API_KEY,
    Config.OPENROUTER_BASE_URL,
    Config.OPENROUTER_MODEL
)

print(f"API Key: {Config.OPENROUTER_API_KEY[:20]}...")
print(f"Model: {Config.OPENROUTER_MODEL}")
print(f"Base URL: {Config.OPENROUTER_BASE_URL}")

print("\nGenerating blog...")
print("-"*60)

try:
    result = generator.generate_blog(
        topic="Test Topic",
        topic_description="This is a test",
        keywords=["test", "demo"],
        word_count_min=100,
        word_count_max=200
    )
    
    if result:
        print("SUCCESS!")
        print(f"Title: {result['title']}")
        print(f"Body length: {len(result['body'])} chars")
    else:
        print("ERROR: generate_blog returned None")
        
except Exception as e:
    print(f"EXCEPTION: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("="*60)
