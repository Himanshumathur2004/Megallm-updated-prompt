"""Mock blog generator for offline testing."""

import logging
import random
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MockBlogGenerator:
    """Generate mock blogs for testing without API access."""
    
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        logger.info("Using MockBlogGenerator (offline mode - no real API calls)")
    
    def generate_blog(
        self,
        topic: str,
        topic_description: str,
        keywords: list,
        word_count_min: int = 500,
        word_count_max: int = 800
    ) -> Optional[Dict[str, str]]:
        """Generate a mock blog post with unique content."""
        try:
            # Create unique blog titles based on topic and random variations
            title_variations = {
                "infrastructure": [
                    "Building Robust Infrastructure: Complete Guide",
                    "Infrastructure Best Practices for Modern Systems",
                    "Scaling Infrastructure: Strategies for Growth",
                    "Infrastructure Automation: Reducing Manual Work",
                    "Infrastructure Security: Protecting Your Assets",
                    "Cloud Infrastructure Optimization",
                    "Infrastructure Monitoring and Alerting",
                    "Infrastructure as Code: Complete Guide",
                    "Disaster Recovery in Infrastructure Planning",
                    "Infrastructure Cost Optimization Strategies"
                ],
                "reliability": [
                    "Ensuring System Reliability: Best Practices",
                    "Building Reliable Systems at Scale",
                    "Reliability Engineering Fundamentals",
                    "High Availability Architecture Patterns",
                    "Reliability Testing and Validation",
                    "SLA Achievement Through Reliability",
                    "Fault Tolerance and Resilience Patterns",
                    "Reliability Metrics and Monitoring",
                    "Building Zero-Downtime Systems",
                    "Incident Response and Recovery"
                ],
                "performance": [
                    "Performance Optimization Techniques",
                    "Achieving High Performance at Scale",
                    "Performance Testing and Benchmarking",
                    "Database Performance Tuning",
                    "Application Performance Monitoring",
                    "Performance Engineering Best Practices",
                    "Caching Strategies for Performance",
                    "Load Balancing and Performance",
                    "Network Performance Optimization",
                    "Memory and CPU Optimization"
                ],
                "cost_optimization": [
                    "Cost Optimization Strategies for Cloud",
                    "Reducing Cloud Infrastructure Costs",
                    "Cost Analysis and Optimization",
                    "Resource Optimization for Savings",
                    "Cloud Spending Management",
                    "Budget Planning and Cost Control",
                    "Rightsizing Your Infrastructure",
                    "Cost Monitoring and Alerts",
                    "Automation for Cost Savings",
                    "Vendor Management and Cost Reduction"
                ]
            }
            
            # Get topic key for title variations
            topic_key = topic.lower().replace(" ", "_").replace("&", "and")
            variations = title_variations.get(topic_key, [
                f"{topic}: A Practical Guide",
                f"Mastering {topic}",
                f"{topic}: Advanced Techniques",
                f"Best Practices for {topic}",
                f"{topic}: Complete Reference"
            ])
            
            # Pick a random title variation
            title = random.choice(variations)
            
            keywords_str = ", ".join(keywords[:2]) if keywords else topic
            
            body = f"""
{title}

## Introduction

{topic_description} is a critical aspect of modern infrastructure. In this guide, we'll explore practical strategies for success while optimizing for {keywords_str}.

## Key Strategies

1. **Understanding the Fundamentals**: Start with core concepts. {keywords_str} form the foundation of any successful implementation. Understand the theory before diving into practice.

2. **Practical Implementation**: Apply these principles systematically. Consider your {keywords_str} requirements and constraints. Test thoroughly before deploying to production.

3. **Monitoring and Measurement**: Establish metrics early. Use real-world data to guide optimization efforts. Continuous monitoring reveals improvement opportunities.

4. **Iterative Improvement**: Don't expect perfection immediately. Iterate based on feedback and metrics. Small incremental improvements add up over time.

## Advanced Considerations

- Plan for scalability from the start
- Document all decisions and trade-offs
- Consider disaster recovery scenarios
- Regular audits and reviews
- Stay updated with industry trends

## Common Pitfalls to Avoid

- Over-engineering simple solutions
- Ignoring operational concerns
- Insufficient testing and validation
- Poor documentation and knowledge sharing
- Reactive instead of proactive approach

## Conclusion

{topic} is an ongoing journey, not a one-time setup. By following these practices and maintaining a commitment to continuous improvement, you can achieve significant business value. Start with the fundamentals, measure everything, and iterate based on real-world results.

Remember: the best solution is one that works for your specific context and evolves with your needs.
""".strip()
            
            logger.info(f"Generated mock blog: {title} ({len(body)} chars)")
            
            return {
                "title": title.strip(),
                "body": body.strip()
            }
        
        except Exception as e:
            logger.error(f"Mock blog generation error: {e}")
            return None
    
    def batch_generate(
        self,
        topics: Dict[str, Dict],
        blogs_per_topic: int = 1
    ) -> Dict[str, list]:
        """Generate multiple mock blogs."""
        result = {}
        
        for topic_id, topic_info in topics.items():
            result[topic_id] = []
            
            for i in range(blogs_per_topic):
                blog = self.generate_blog(
                    topic=topic_info.get("name", topic_id),
                    topic_description=topic_info.get("description", ""),
                    keywords=topic_info.get("keywords", [])
                )
                
                if blog:
                    result[topic_id].append(blog)
        
        return result
