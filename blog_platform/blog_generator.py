"""Blog generation using OpenRouter API."""

import json
import logging
from typing import Dict, Optional
import requests
import random

logger = logging.getLogger(__name__)


class BlogGenerator:
    """Generate blog posts using OpenRouter API."""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_blog(
        self,
        topic: str,
        topic_description: str,
        keywords: list,
        word_count_min: int = 500,
        word_count_max: int = 800
    ) -> Optional[Dict[str, str]]:
        """
        Generate a blog post for a specific topic.
        
        Returns:
            {"title": str, "body": str} or None on error
        """
        # Randomly decide whether to mention MegaLLM in the title (30% chance)
        mention_megallm_in_title = random.random() < 0.3
        
        title_instruction = (
            "should mention MegaLLM in the title"
            if mention_megallm_in_title
            else "title should focus on the problem/solution WITHOUT mentioning MegaLLM - make it sound like organic technical content"
        )
        
        system_prompt = f"""You are a technical content writer writing for a tech blog.

MegaLLM Context (use only in body, not always):
- MegaLLM is a unified LLM router and optimization platform
- It helps CTOs and AI teams reduce costs, improve performance, and ensure reliability
- MegaLLM provides multi-model support, automatic failover, and intelligent routing
- Target audience: CTOs at AI startups building LLM-powered applications

Write a blog post about: {topic}

Description: {topic_description}

Requirements:
- Title: max 10 words, {title_instruction}
- Body: {word_count_min}-{word_count_max} words
- Focus on: The problem, solution approaches, best practices
- Include: Practical examples, specific metrics, or real-world scenarios
- Optional: Can mention MegaLLM in body if relevant to the discussion
- Use simple, clear technical language
- Target CTOs at AI startups

Return ONLY valid JSON (no markdown):
{{
  "title": "Your title here",
  "body": "Your blog post here..."
}}"""
        
        user_prompt = f"""Write a technical blog post for CTOs about:
Topic: {topic}
Key points: {', '.join(keywords)}

IMPORTANT: This blog should:
1. Explain why {topic} matters for LLM applications
2. Discuss practical solutions and best practices
3. Include specific benefits or tradeoffs
4. Provide actionable tips or examples
5. Be relevant to AI startups building with LLMs
6. Sound natural and informative (not promotional)

{'Note: You may mention MegaLLM in the body if it fits the discussion naturally.' if not mention_megallm_in_title else ''}

Return valid JSON with title and body fields only."""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.65,
                    "max_tokens": 2000
                },
                timeout=120
            )
            
            logger.info(f"API Response Status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            raw_response = data["choices"][0]["message"]["content"]
            
            # Parse JSON response
            cleaned = raw_response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            
            if start == -1 or end == -1:
                logger.error(f"Invalid JSON format in response: {raw_response[:200]}")
                return None
            
            parsed = json.loads(cleaned[start:end+1])
            
            # Validate fields
            if "title" not in parsed or "body" not in parsed:
                logger.error(f"Missing title or body in response: {parsed}")
                return None
            
            return {
                "title": parsed["title"].strip(),
                "body": parsed["body"].strip()
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"API HTTP error: {e.response.status_code} - {e.response.reason}")
            logger.error(f"Response body: {e.response.text[:500]}")
            if e.response.status_code == 429:
                logger.error("Rate limit exceeded (429)")
            elif e.response.status_code == 401:
                logger.error("Unauthorized - check API key")
            elif e.response.status_code == 400:
                logger.error("Bad request - check model name and parameters")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw response was: {raw_response[:300] if 'raw_response' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Blog generation error: {type(e).__name__}: {e}")
            return None
    
    def batch_generate(
        self,
        topics: Dict[str, Dict],
        blogs_per_topic: int = 1
    ) -> Dict[str, list]:
        """
        Generate multiple blogs across topics.
        
        Args:
            topics: Dict mapping topic_id -> {name, description, keywords}
            blogs_per_topic: Number of blogs per topic
        
        Returns:
            {topic_id -> [list of generated blogs]}
        """
        result = {}
        
        for topic_id, topic_info in topics.items():
            result[topic_id] = []
            logger.info(f"Generating {blogs_per_topic} blogs for topic: {topic_id}")
            
            for i in range(blogs_per_topic):
                blog = self.generate_blog(
                    topic=topic_info.get("name", topic_id),
                    topic_description=topic_info.get("description", ""),
                    keywords=topic_info.get("keywords", [])
                )
                
                if blog:
                    result[topic_id].append(blog)
                    logger.info(f"✓ Generated blog {i+1}/{blogs_per_topic} for {topic_id}")
                else:
                    logger.error(f"✗ Failed to generate blog {i+1}/{blogs_per_topic} for {topic_id}")
        
        return result
