"""WSGI Entry Point for Heroku Deployment"""
import sys
from pathlib import Path

# Add blog_platform directory to path
blog_platform_dir = Path(__file__).parent / "blog_platform"
sys.path.insert(0, str(blog_platform_dir))

from app import app

if __name__ == "__main__":
    app.run()
