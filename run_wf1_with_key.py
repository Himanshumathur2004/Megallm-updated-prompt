#!/usr/bin/env python3
"""Wrapper to force new API key before importing wf1."""

import os
import sys

# Force the new API key BEFORE any imports
os.environ['MEGALLM_API_KEY'] = 'sk-mega-77fc25dc77c9a47a319c8cb59696ff19d45d143c35adc391b853a44854311b7d'
os.environ['OPENAI_API_KEY'] = 'sk-mega-77fc25dc77c9a47a319c8cb59696ff19d45d143c35adc391b853a44854311b7d'

# NOW import wf1 (after env vars are set)
from wf1 import ContentIntelligencePipeline, _build_config

config = _build_config()
print(f"Using API key: {config.api_key[:20]}...")
print(f"Starting WF1 with {config.api_key.count('a')} characters")
print()

wf1 = ContentIntelligencePipeline(config)
wf1.run()
wf1.close()

print("\nWF1 Complete!")
