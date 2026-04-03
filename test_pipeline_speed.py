#!/usr/bin/env python
"""Test if the pipeline endpoint is hanging on blog generation."""
import sys
import os
import time

sys.path.insert(0, '.')
from blog_platform.config import Config
from blog_platform.blog_generator import BlogGenerator

# Check API key
print(f"API Key configured: {bool(Config.OPENROUTER_API_KEY)}")
print(f"Model: {Config.OPENROUTER_MODEL}")

if not Config.OPENROUTER_API_KEY:
    print("ERROR: No OpenRouter API key configured!")
    sys.exit(1)

# Initialize generator
gen = BlogGenerator(
    api_key=Config.OPENROUTER_API_KEY,
    base_url=getattr(Config, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
    model=Config.OPENROUTER_MODEL
)
print("Generator initialized")

# Test a single blog generation
print("\nTesting blog generation...")
start = time.time()
try:
    result = gen.generate_blog(
        topic='AI Performance',
        topic_description='Optimizing AI model performance',
        keywords=['model', 'optimization']
    )
    elapsed = time.time() - start
    print(f"SUCCESS! Took {elapsed:.1f}s")
    if result:
        title = str(result.get('title', 'N/A'))[:60]
        print(f"Title: {title}...")
except Exception as e:
    elapsed = time.time() - start
    print(f"ERROR after {elapsed:.1f}s")
    print(f"{type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
