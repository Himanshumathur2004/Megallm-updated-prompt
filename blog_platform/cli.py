#!/usr/bin/env python3
"""Command-line management tool for Blog Generation Platform."""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import Database
from blog_generator import BlogGenerator
from config import Config


def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


class BlogManager:
    """CLI interface for managing blogs."""
    
    def __init__(self):
        self.db = Database(Config.MONGODB_URI, Config.MONGODB_DB)
        self.generator = BlogGenerator(
            Config.OPENROUTER_API_KEY,
            Config.OPENROUTER_BASE_URL,
            Config.OPENROUTER_MODEL
        )
    
    def list_accounts(self):
        """List all accounts."""
        print_header("Accounts")
        accounts = self.db.get_all_accounts()
        
        for account in accounts:
            print(f"• {account['account_id']:15} {account['name']:20} ({account.get('blog_count', 0)} blogs)")
    
    def account_status(self, account_id):
        """Show account statistics."""
        print_header(f"Account: {account_id}")
        
        summary = self.db.get_dashboard_summary(account_id)
        if not summary:
            print(f"Account '{account_id}' not found")
            return
        
        account = summary.get('account', {})
        print(f"Name:              {account.get('name', 'N/A')}")
        print(f"Description:       {account.get('description', 'N/A')}")
        print(f"Total Blogs:       {account.get('blog_count', 0)}")
        print(f"Posted Blogs:      {summary.get('posted_blogs', 0)}")
        print(f"Draft Blogs:       {summary.get('draft_blogs', 0)}")
        print(f"Last Generation:   {account.get('last_generation', 'Never')}")
        
        print("\nBlogs by Topic:")
        for topic, count in summary.get('blogs_by_topic', {}).items():
            print(f"  {topic:20} {count:3} blogs")
    
    def list_blogs(self, account_id, status=None, limit=10):
        """List blogs for an account."""
        blogs = self.db.get_blogs_by_account(account_id, status=status, limit=limit)
        
        print_header(f"Blogs for {account_id}" + (f" ({status})" if status else ""))
        
        if not blogs:
            print("No blogs found.")
            return
        
        for i, blog in enumerate(blogs, 1):
            status_badge = f"[{blog.get('status', 'unknown').upper()}]"
            title = blog.get('title', 'N/A')[:50]
            topic = blog.get('topic', 'unknown')
            date = blog.get('created_at', 'N/A')[:10]
            
            print(f"{i}. {status_badge:9} {title:50} ({topic}) - {date}")
    
    def generate_blogs(self, account_id, count=None):
        """Generate blogs for an account."""
        print_header(f"Generating blogs for {account_id}")
        
        if count is None:
            topics_to_gen = {topic_id: 3 for topic_id in Config.TOPICS.keys()}
        else:
            topics_to_gen = {topic_id: count for topic_id in Config.TOPICS.keys()}
        
        generated_count = 0
        try:
            for topic_id, topic_count in topics_to_gen.items():
                topic_info = Config.TOPICS[topic_id]
                
                for i in range(topic_count):
                    blog_data = self.generator.generate_blog(
                        topic=topic_info["name"],
                        topic_description=topic_info["description"],
                        keywords=topic_info["keywords"]
                    )
                    
                    if blog_data:
                        blog_data["account_id"] = account_id
                        blog_data["topic"] = topic_id
                        blog_id = self.db.insert_blog(blog_data)
                        generated_count += 1
                        print(f"✓ {topic_id:20} ({i+1}/{topic_count}): {blog_data['title'][:40]}...")
                    else:
                        print(f"✗ {topic_id:20} ({i+1}/{topic_count}): Failed to generate")
        
        except KeyboardInterrupt:
            print("\n⚠ Generation interrupted by user")
        except Exception as e:
            print(f"✗ Error during generation: {e}")
        
        # Log generation event
        self.db.log_generation(account_id, generated_count, None)
        
        print(f"\n✓ Generated {generated_count} blogs successfully")
    
    def mark_posted(self, blog_id):
        """Mark a blog as posted."""
        success = self.db.mark_blog_posted(blog_id)
        
        if success:
            print(f"✓ Blog {blog_id} marked as posted")
        else:
            print(f"✗ Failed to mark blog {blog_id} as posted")
    
    def delete_blog(self, blog_id):
        """Delete a blog."""
        blog = self.db.get_blog_by_id(blog_id)
        
        if not blog:
            print(f"✗ Blog {blog_id} not found")
            return
        
        if blog.get('status') != 'draft':
            print(f"✗ Can only delete draft blogs (this one is {blog.get('status')})")
            return
        
        success = self.db.delete_blog(blog_id)
        
        if success:
            print(f"✓ Blog {blog_id} deleted")
        else:
            print(f"✗ Failed to delete blog {blog_id}")
    
    def show_blog(self, blog_id):
        """Display full blog content."""
        blog = self.db.get_blog_by_id(blog_id)
        
        if not blog:
            print(f"Blog {blog_id} not found")
            return
        
        print_header("Blog Content")
        
        print(f"ID:        {blog.get('_id')}")
        print(f"Account:   {blog.get('account_id')}")
        print(f"Topic:     {blog.get('topic')}")
        print(f"Status:    {blog.get('status')}")
        print(f"Created:   {blog.get('created_at')}")
        print(f"Posted:    {blog.get('posted_at', 'Not yet')}")
        
        print(f"\nTitle:\n{blog.get('title')}\n")
        print(f"Body:\n{blog.get('body')}\n")
    
    def export_blogs(self, account_id, status=None, output_file=None):
        """Export blogs to a file."""
        blogs = self.db.get_blogs_by_account(account_id, status=status, limit=1000)
        
        if not blogs:
            print("No blogs to export")
            return
        
        output = []
        for blog in blogs:
            output.append({
                'title': blog.get('title'),
                'body': blog.get('body'),
                'topic': blog.get('topic'),
                'status': blog.get('status'),
                'created_at': blog.get('created_at')
            })
        
        if output_file:
            import json
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"✓ Exported {len(output)} blogs to {output_file}")
        else:
            import json
            print(json.dumps(output, indent=2))
    
    def cleanup(self):
        """Close database connection."""
        self.db.close()


def main():
    parser = argparse.ArgumentParser(
        description='OpenRouter Blog Generation Platform - CLI Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py accounts                    # List accounts
  python cli.py status account_1            # Show account statistics
  python cli.py list account_1              # List blogs
  python cli.py list account_1 --status=draft  # List draft blogs only
  python cli.py generate account_1          # Generate 12 blogs
  python cli.py generate account_1 --count=5  # Generate 5 blogs per topic
  python cli.py show <blog_id>              # Show full blog content
  python cli.py mark-posted <blog_id>       # Mark blog as posted
  python cli.py delete <blog_id>            # Delete a blog
  python cli.py export account_1 --output=blogs.json  # Export blogs
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # accounts command
    subparsers.add_parser('accounts', help='List all accounts')
    
    # status command
    status_parser = subparsers.add_parser('status', help='Show account statistics')
    status_parser.add_argument('account_id', help='Account ID')
    
    # list command
    list_parser = subparsers.add_parser('list', help='List blogs')
    list_parser.add_argument('account_id', help='Account ID')
    list_parser.add_argument('--status', choices=['draft', 'posted'], help='Filter by status')
    list_parser.add_argument('--limit', type=int, default=10, help='Number of blogs to show')
    
    # generate command
    gen_parser = subparsers.add_parser('generate', help='Generate blogs')
    gen_parser.add_argument('account_id', help='Account ID')
    gen_parser.add_argument('--count', type=int, default=3, help='Blogs per topic (default: 3)')
    
    # show command
    show_parser = subparsers.add_parser('show', help='Show blog content')
    show_parser.add_argument('blog_id', help='Blog ID')
    
    # mark-posted command
    mark_parser = subparsers.add_parser('mark-posted', help='Mark blog as posted')
    mark_parser.add_argument('blog_id', help='Blog ID')
    
    # delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a blog')
    delete_parser.add_argument('blog_id', help='Blog ID')
    
    # export command
    export_parser = subparsers.add_parser('export', help='Export blogs')
    export_parser.add_argument('account_id', help='Account ID')
    export_parser.add_argument('--status', choices=['draft', 'posted'], help='Filter by status')
    export_parser.add_argument('--output', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    manager = BlogManager()
    
    try:
        if args.command == 'accounts':
            manager.list_accounts()
        
        elif args.command == 'status':
            manager.account_status(args.account_id)
        
        elif args.command == 'list':
            manager.list_blogs(args.account_id, args.status, args.limit)
        
        elif args.command == 'generate':
            manager.generate_blogs(args.account_id, args.count)
        
        elif args.command == 'show':
            manager.show_blog(args.blog_id)
        
        elif args.command == 'mark-posted':
            manager.mark_posted(args.blog_id)
        
        elif args.command == 'delete':
            manager.delete_blog(args.blog_id)
        
        elif args.command == 'export':
            manager.export_blogs(args.account_id, args.status, args.output)
    
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1
    finally:
        manager.cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
