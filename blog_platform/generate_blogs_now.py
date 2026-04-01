#!/usr/bin/env python
"""
Generate blogs immediately for all accounts.
This script directly calls the blog generation logic, bypassing HTTP issues.
"""

import sys
from pathlib import Path
import traceback

# Add blog_platform to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app import app, blog_generator, db, Config
    import logging
    
    logger = logging.getLogger(__name__)
    
    def generate_blogs_all():
        """Generate blogs for all accounts immediately."""
        total_generated = 0
        
        with app.test_client() as client:
            for account in Config.ACCOUNTS:
                account_id = account["id"]
                
                # Prepare all topics
                topics = {}
                for topic_id in Config.TOPICS.keys():
                    topics[topic_id] = 1  # 1 blog per topic to start
                
                print(f"[{account_id}] Requesting {sum(topics.values())} blogs...")
                
                # Call the generate endpoint via test client
                response = client.post(
                    '/api/blogs/generate',
                    json={"account_id": account_id, "topics": topics},
                    content_type='application/json'
                )
                
                result = response.get_json()
                count = result.get('generated_count', 0)
                error = result.get('error')
                total_generated += count
                
                status_msg = f"  Generated {count} blogs" if count > 0 else "  Generated 0 blogs"
                if error:
                    status_msg += f" (error: {error})"
                print(status_msg)
        
        print(f"\n{'='*60}")
        print(f"Total blogs generated: {total_generated}")
        print(f"{'='*60}")
        
        return total_generated
    
    if __name__ == "__main__":
        generate_blogs_all()

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
