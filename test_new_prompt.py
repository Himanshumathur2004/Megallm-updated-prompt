#!/usr/bin/env python
"""Test the updated blog generator prompt locally."""
import sys
import time
sys.path.insert(0, '.')

from blog_platform.config import Config
from blog_platform.blog_generator import BlogGenerator

print("Initializing blog generator...")
gen = BlogGenerator(
    api_key=Config.OPENROUTER_API_KEY,
    base_url='https://openrouter.ai/api/v1',
    model=Config.OPENROUTER_MODEL
)

print("\nGenerating 1 test blog (may take 30-60 seconds)...")
start = time.time()

try:
    result = gen.generate_blog(
        topic="Cost Optimization in LLM Inference",
        topic_description="How to optimize costs when running LLM-powered applications at scale",
        keywords=["cost", "optimization", "inference", "model selection"]
    )
    
    elapsed = time.time() - start
    
    if result is None:
        print(f"ERROR: Blog generation returned None after {elapsed:.1f}s")
    else:
        print(f"\n✓ GENERATED in {elapsed:.1f}s\n")
        print("=" * 60)
        print(f"TITLE: {result['title']}")
        print("=" * 60)
        print(f"BODY (first 500 chars):\n{result['body'][:500]}...")
        print("=" * 60)
        
        # Check for MegaLLM mentions
        title_has_megallm = "megallm" in result['title'].lower()
        body_has_megallm = "megallm" in result['body'].lower()
        
        print(f"\nMegaLLM in title: {title_has_megallm} (should be False)")
        print(f"MegaLLM in body: {body_has_megallm}")
        
        if title_has_megallm:
            print("\n⚠️  WARNING: MegaLLM found in title (should not be there)")
        else:
            print("\n✓ PASS: Title has no brand mentions")
            
except Exception as e:
    elapsed = time.time() - start
    print(f"ERROR after {elapsed:.1f}s: {e}")
    import traceback
    traceback.print_exc()
