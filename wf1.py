#!/usr/bin/env python3
"""
OpenRouter Content Intelligence Pipeline
Replaces n8n workflow with Python implementation
Uses OpenRouter API (OpenAI-compatible) at https://openrouter.ai/api/v1
"""

import os
import json
import math
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple  # FIX 1: Added Tuple import (was using tuple[...] without import)
from dataclasses import dataclass, field  # FIX 2: Added field import (needed for mutable default in dataclass)

import requests
from pymongo import MongoClient
from pymongo.collection import Collection
from workflow_common import LLMQuotaExceededError, bootstrap_env, resolve_api_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class Config:
    # OpenRouter API (OpenAI-compatible)
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))  # or OPENAI_API_KEY
    openai_base_url: str = "https://openrouter.ai/api/v1"
    openai_model: str = field(
        default_factory=lambda: os.getenv(
            "WF1_OPENAI_MODEL", os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus-preview:free")
        )
    )

    # MongoDB
    mongodb_uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI"))
    mongodb_db: str = field(default_factory=lambda: os.getenv("MONGODB_DB", "megallm"))
    scrape_run_id: str = field(default_factory=lambda: os.getenv("WF1_SCRAPE_RUN_ID", ""))

    # Qdrant
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_collection: str = "content_embeddings"

    # Processing
    batch_size: int = 10
    dedup_threshold: float = 0.85
    icp_threshold: float = 3.0
    max_articles: int = 200

    # FIX 3: Mutable default (dict) in dataclass must use field(default_factory=...)
    value_prop_map: Dict = field(default_factory=lambda: {
        "model_launch": {
            "hook": "New model just dropped — here's what your inference bill will look like",
            "cta": "Switch your default model in MegaLLM and benchmark in 5 min"
        },
        "outage": {
            "hook": "Another provider went down. Is your stack resilient?",
            "cta": "MegaLLM's automatic failover means zero downtime for your users"
        },
        "pricing": {
            "hook": "Pricing changed again — your costs just shifted",
            "cta": "Lock in stable pricing with MegaLLM's committed-use plans"
        },
        "benchmark": {
            "hook": "The benchmarks are in — latency winners and losers",
            "cta": "Run your own benchmark on MegaLLM in under 10 minutes"
        },
        "compliance": {
            "hook": "Data residency just got more complex for UK/SG/AU teams",
            "cta": "MegaLLM offers in-region data processing with full GDPR compliance"
        },
        "default": {
            "hook": "The LLM infrastructure landscape just shifted",
            "cta": "See how MegaLLM adapts to keep your stack optimised"
        }
    })


# ============================================================================
# OPENROUTER API CLIENT (OpenAI-compatible)
# ============================================================================

class OpenRouterClient:
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def chat_completion(self, system_prompt: str, user_prompt: str,
                        temperature: float = 0.7, max_tokens: int = 600) -> str:
        """Make OpenRouter API request (OpenAI-compatible endpoint)."""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenRouter API error: {e}")
            if e.response is not None:
                body = e.response.text
                logger.error(f"Response: {body}")
                if e.response.status_code == 429:
                    raise LLMQuotaExceededError(body) from e
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API error: {e}")
            # FIX 4: e.response may be None; guard before accessing .text
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    def generate_angle(self, article: Dict) -> Dict[str, Any]:
        """Generate content angle for article."""
        system_prompt = """You are a senior AI content strategist for technology companies.
    Your job is to transform each input article into one sharp, high-conviction content angle for technical decision-makers.

    CONTEXT: WHO YOU ARE WRITING FOR
    Ideal Customer Profile (ICP):

    Primary persona: CTOs / Founding Engineers at AI startups
    Company stage: approximately $500K-$10M ARR
    Regions: UK, Singapore, Australia, New Zealand
    Decision priorities:
    Lowering inference cost without sacrificing output quality
    Achieving low latency for real-time user experiences
    Maximizing production reliability and uptime
    Meeting compliance and data-residency requirements
    Preserving model optionality (avoiding vendor lock-in)

    OPENROUTER POSITIONING (USE WHEN RELEVANT)

    Cost: Free tier with fair usage
    Speed: Fast inference with multiple model options
    Reliability: Stable API service
    Flexibility: 100+ models through one API
    Compliance: Privacy-focused, no data training
    INPUT
    Title: {{ $json.title || 'N/A' }}
    Summary: {{ $json.contentSnippet || 'N/A' }}
    Categories: {{ ($json.categories || []).join(', ') }}
    Link: {{ $json.link || 'N/A' }}

    TASK
    Generate exactly one high-signal content angle that:

    Frames the article through a startup CTO lens
    Surfaces a decision-relevant technical or business implication
    Connects that implication to one concrete OpenRouter advantage
    Includes one quantitative infrastructure data point
    ALLOWED angle_type VALUES

    cost_saving
    speed_benchmark
    model_comparison
    outage_lesson
    pricing_shift
    new_model
    compliance
    infra_scaling
    OUTPUT FORMAT
    Return ONLY valid JSON (single object, no markdown, no prose, no extra keys):

    {
    "angle_type": "<cost_saving|speed_benchmark|model_comparison|outage_lesson|pricing_shift|new_model|compliance|infra_scaling>",
    "hook_sentence": "<max 15 words, present tense, high-urgency technical opener>",
    "core_claim": "<one sentence: actionable implication for startup CTO decisions>",
    "megallm_tie_in": "<one sentence mapping issue to one specific MegaLLM value prop>",
    "infra_data_point": "<one concrete numeric fact: %, ms, $, tokens/sec, req/sec, etc.>"
    }

    QUALITY REQUIREMENTS

    Hook:
    Must be punchy and scroll-stopping (tweet-style energy)
    Must avoid generic intros and filler
    Must not exceed 15 words
    Core claim:
    Must be prescriptive or decision-oriented, not descriptive summary
    Must reflect startup execution constraints (speed, burn, reliability, compliance)
    MegaLLM tie-in:
    Must map to exactly one primary MegaLLM advantage
    Must be concrete and implementation-relevant
    Infra data point:
    Must contain at least one explicit number and unit/context
    Prefer realistic operational metrics (latency, cost, throughput, uptime, error rate)
    STRICT RULES

    Do not say "this article discusses" or similar low-signal phrasing.
    Do not output multiple options.
    Do not include markdown fences.
    Do not include explanations outside the JSON.
    If input is weak/ambiguous, still return best-effort JSON using the most plausible angle_type.
    Keep language concise, technical, and decision-focused for startup CTOs.
    Only output JSON.

    DECISION QUALITY RUBRIC (INTERNAL)
    - Prefer implications that affect next-week execution, not abstract strategy.
    - Prioritize arguments tied to budget, latency SLOs, incident risk, or compliance exposure.
    - If multiple angles are possible, choose the one with the clearest operational trade-off.
    - Keep claims falsifiable and specific enough to benchmark.

    STYLE GUARDRAILS
    - Write in active voice.
    - Avoid hype words such as "revolutionary", "game-changing", or "best-in-class".
    - Avoid repeating the same value proposition across core_claim and megallm_tie_in.
    - Do not include rhetorical questions.

    FIELD-LEVEL PRECISION
    - angle_type must be one allowed value only.
    - hook_sentence should imply urgency without fear-mongering.
    - core_claim must include an explicit decision implication.
    - megallm_tie_in must map to one primary MegaLLM lever: cost OR speed OR reliability OR flexibility OR compliance.
    - infra_data_point must include a number and context (unit + what it measures).

    ROBUSTNESS RULE
    If the article is incomplete, infer the most plausible CTO-relevant angle and still return valid JSON."""

        user_prompt = f"""Article title: {article.get('title', 'N/A')}
Summary: {article.get('contentSnippet', 'N/A')}
Categories: {json.dumps(article.get('categories', []))}
Source: {article.get('source', 'N/A')}"""

        response = None  # FIX 5: Initialise response before try block so except can always reference it
        try:
            response = self.chat_completion(system_prompt, user_prompt, temperature=0.7, max_tokens=600)

            # Clean and parse JSON
            cleaned = response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1:
                cleaned = cleaned[start:end + 1]

            parsed = json.loads(cleaned)

            # Validate required fields
            required = ['angle_type', 'hook_sentence', 'core_claim', 'megallm_tie_in', 'infra_data_point']
            missing = [f for f in required if f not in parsed or not parsed[f]]

            if missing:
                return {
                    "status": "angle_failed",
                    "angle_error": f"Missing fields: {', '.join(missing)}",
                    "raw_response": response
                }

            parsed["angle_ok"] = True
            return parsed

        except json.JSONDecodeError as e:
            return {
                "status": "angle_failed",
                "angle_error": f"JSON parse error: {str(e)}",
                "raw_response": response
            }
        except LLMQuotaExceededError:
            raise
        except Exception as e:
            return {
                "status": "angle_failed",
                "angle_error": str(e),
                "raw_response": response
            }

    def score_icp_relevance(self, article: Dict, angle: Dict) -> Dict[str, Any]:
        """Score ICP relevance of content angle."""
        system_prompt = """You are an ICP (Ideal Customer Profile) relevance evaluator for MegaLLM.

ICP Definition: CTOs at AI startups with $500K-$10M ARR based in UK, Singapore, Australia, or New Zealand. They care about:
- Cost efficiency and reducing inference spend
- Low latency for real-time applications
- Reliability and uptime for production systems
- Compliance and data residency
- Model flexibility and avoiding vendor lock-in

Score this content angle on relevance to our ICP. Return ONLY a JSON object:
{
  "cost_relevance": <1-10>,
  "latency_relevance": <1-10>,
  "reliability_relevance": <1-10>,
  "compliance_relevance": <1-10>,
  "decision_maker_appeal": <1-10>,
  "geo_relevance": <1-10>,
  "weighted_total": <weighted average, 1 decimal>,
  "reasoning": "<brief explanation of the score>"
}

Weights: cost 25%, latency 20%, reliability 20%, compliance 15%, decision maker 15%, geo 5%.

SCORING GUIDELINES
- 1-3: weak relevance, mostly generic, little startup CTO decision value.
- 4-6: moderate relevance, partially useful but missing specificity or actionability.
- 7-8: strong relevance, clear CTO implications and credible operational framing.
- 9-10: exceptional relevance, highly specific, urgent, and decision-enabling for ICP.

CALIBRATION RULES
- Penalize non-numeric or vague claims in cost/latency/reliability narratives.
- Penalize geo_relevance if UK/SG/AU/NZ context is absent when regional compliance is central.
- Reward explicit connection to startup constraints: runway, small teams, production risk.
- Reward practical implications (what to adopt, benchmark, de-risk, or migrate).

REASONING RULES
- Keep reasoning concise and concrete.
- Mention the single biggest weakness first, then one improvement suggestion.
- Return JSON only; no markdown fences or extra keys."""

        user_prompt = f"""Article title: {article.get('title', 'N/A')}
Summary: {article.get('contentSnippet', 'N/A')}
Angle type: {angle.get('angle_type', 'N/A')}
Core claim: {angle.get('core_claim', 'N/A')}
MegaLLM tie-in: {angle.get('megallm_tie_in', 'N/A')}"""

        try:
            response = self.chat_completion(system_prompt, user_prompt, temperature=0.3, max_tokens=400)

            cleaned = response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1:
                cleaned = cleaned[start:end + 1]

            scores = json.loads(cleaned)
            return {
                "icp_scores": scores,
                "icp_score": scores.get("weighted_total", 5.0)
            }

        except LLMQuotaExceededError:
            raise
        except Exception as e:
            return {
                "icp_scores": {"weighted_total": 5.0, "reasoning": f"parse error: {str(e)}"},
                "icp_score": 5.0
            }

    def generate_infra_insight(self, article: Dict, angle: Dict) -> str:
        """Generate infrastructure data point."""
        system_prompt = """You are a technical research assistant for MegaLLM. Extract or generate ONE specific, verifiable infrastructure data point related to LLMs from the article context.

Examples of good data points:
- "OpenAI's GPT-4 Turbo costs $10 per million input tokens"
- "Average latency for Claude 3 Opus is 850ms for 1K tokens"
- "Running Llama 3 70B requires approximately 140GB VRAM"
- "AWS g5.2xlarge instances cost $1.006 per hour for GPU inference"
- "DeepSeek-V3 achieves 60 tokens per second on H100 GPUs"

Return ONLY the data point as a plain string (max 100 characters). No JSON, no markdown, no explanation. Just the raw fact.

QUALITY BAR
- Prefer numbers that include unit and scope (e.g., p50 latency, per million tokens, per hour).
- Prefer claims useful for infra decisions (capacity, throughput, cost, reliability, memory footprint).
- Keep wording compact and unambiguous.

SAFETY + VALIDITY
- Do not invent impossible values; use realistic estimates if exact values are unavailable.
- Avoid unverifiable superlatives.
- If article evidence is weak, provide a conservative industry-typical metric.
- Output must be one line only."""

        user_prompt = f"""Article title: {article.get('title', 'N/A')}
Content snippet: {article.get('contentSnippet', 'N/A')}
Angle type: {angle.get('angle_type', 'N/A')}
Core claim: {angle.get('core_claim', 'N/A')}"""

        try:
            response = self.chat_completion(system_prompt, user_prompt, temperature=0.6, max_tokens=150)
            return response.strip()
        except LLMQuotaExceededError:
            raise
        except Exception as e:
            logger.error(f"Infra insight generation failed: {e}")
            return "N/A"


# ============================================================================
# QDRANT CLIENT
# ============================================================================

class QdrantClient:
    def __init__(self, base_url: str, collection_name: str):
        self.base_url = base_url.rstrip('/')
        self.collection_name = collection_name
        self.enabled = True

    def search_similar(self, vector: List[float], limit: int = 5,
                       score_threshold: float = 0.0) -> List[Dict]:
        """Search for similar vectors in Qdrant."""
        if not self.enabled:
            return []

        url = f"{self.base_url}/collections/{self.collection_name}/points/search"

        payload = {
            "vector": vector,
            "limit": limit,
            "with_payload": False,
            "score_threshold": score_threshold
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("result", [])
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
                self.enabled = False
                logger.warning(
                    "Qdrant collection not found (%s). Disabling dedup checks for this run.",
                    self.collection_name
                )
                return []
            logger.error(f"Qdrant search error: {e}")
            return []


# ============================================================================
# EMBEDDING UTILS
# ============================================================================

def generate_mock_embedding(text: str, dim: int = 1536) -> List[float]:
    """Generate deterministic mock embedding from text."""
    words = text.lower().split()[:200]
    normalized_text = ' '.join(words)

    hash_val = hashlib.md5(normalized_text.encode()).hexdigest()
    seed = int(hash_val, 16) % (2 ** 31)

    embedding = []
    for idx in range(dim):
        x = math.sin(seed * (idx + 1)) * 43758.5453123
        val = x - math.floor(x)
        val = (val - 0.5) * 2
        embedding.append(val)

    norm = math.sqrt(sum(v * v for v in embedding))
    if norm > 0:
        embedding = [v / norm for v in embedding]

    return embedding


# ============================================================================
# MAIN PIPELINE
# ============================================================================

class ContentIntelligencePipeline:
    def __init__(self, config: Config):
        self.config = config
        self.llm = OpenRouterClient(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            model=config.openai_model
        )
        self.qdrant = QdrantClient(config.qdrant_url, config.qdrant_collection)

        self.mongo_client = MongoClient(config.mongodb_uri)
        self.db = self.mongo_client[config.mongodb_db]
        self.articles: Collection = self.db.articles
        self.content_insights: Collection = self.db.content_insights

    def fetch_pending_articles(self) -> List[Dict]:
        """Fetch pending articles from MongoDB, optionally scoped to a scrape run id."""
        query: Dict[str, Any] = {"status": "pending"}
        if self.config.scrape_run_id:
            query["scrape_run_id"] = self.config.scrape_run_id

        cursor = self.articles.find(query).sort("isoDate", -1).limit(self.config.max_articles)

        articles = list(cursor)
        if self.config.scrape_run_id:
            logger.info(
                f"Fetched {len(articles)} pending articles for scrape_run_id={self.config.scrape_run_id} "
                "(sorted by most recent)"
            )
        else:
            logger.info(f"Fetched {len(articles)} pending articles (sorted by most recent)")
        return articles

    def check_duplicate(self, article: Dict) -> Tuple[bool, float]:  # FIX 6: Tuple (capital T) from typing, not built-in tuple[...]
        """Check if article is duplicate using Qdrant."""
        text = f"{article.get('title', '')} {article.get('contentSnippet', '')} {article.get('content', '')}"
        embedding = generate_mock_embedding(text)

        article['embedding'] = embedding

        results = self.qdrant.search_similar(embedding, limit=5, score_threshold=0.0)

        if not results:
            return False, 0.0

        max_score = max(r.get('score', 0) for r in results)
        is_duplicate = max_score > self.config.dedup_threshold

        return is_duplicate, max_score

    def mark_duplicate(self, article: Dict, score: float):
        """Mark article as duplicate in MongoDB."""
        self.articles.update_one(
            {"_id": article["_id"]},
            {"$set": {
                "status": "duplicate",
                "is_duplicate": True,
                "dedup_score": score
            }}
        )
        logger.info(f"Marked article {article['_id']} as duplicate (score: {score:.3f})")

    def determine_value_prop(self, article: Dict) -> Dict[str, str]:
        """Determine value proposition based on categories."""
        categories = ' '.join(article.get('categories', [])).lower()

        if any(k in categories for k in ['price', 'pricing', 'cost']):
            key = "pricing"
        elif any(k in categories for k in ['outage', 'down']):
            key = "outage"
        elif any(k in categories for k in ['launch', 'release', 'model']):
            key = "model_launch"
        elif any(k in categories for k in ['benchmark', 'latency', 'speed']):
            key = "benchmark"
        elif any(k in categories for k in ['compliance', 'gdpr', 'privacy']):
            key = "compliance"
        else:
            key = "default"

        vp = self.config.value_prop_map[key]
        return {
            "value_prop_key": key,
            "value_prop_hook": vp["hook"],
            "value_prop_cta": vp["cta"]
        }

    def process_article(self, article: Dict) -> Optional[Dict]:
        """Process single article through pipeline."""
        article_id = article["_id"]
        logger.info(f"Processing article: {article_id}")

        # Step 1: Check for duplicates
        is_dup, dup_score = self.check_duplicate(article)
        if is_dup:
            self.mark_duplicate(article, dup_score)
            return None

        # Step 2: Generate angle
        angle_result = self.llm.generate_angle(article)
        if angle_result.get("status") == "angle_failed":
            logger.warning(f"Angle generation failed for {article_id}: {angle_result.get('angle_error')}")
            self.articles.update_one(
                {"_id": article_id},
                {"$set": {"status": "angle_failed", **angle_result}}
            )
            return None

        # Step 3: Score ICP relevance
        icp_result = self.llm.score_icp_relevance(article, angle_result)
        icp_score = icp_result["icp_score"]

        # Step 4: ICP Gate
        if icp_score < self.config.icp_threshold:
            logger.info(f"Article {article_id} below ICP threshold ({icp_score} < {self.config.icp_threshold})")
            self.articles.update_one(
                {"_id": article_id},
                {"$set": {
                    "status": "low_icp",
                    "icp_score": icp_score,
                    "icp_scores": icp_result["icp_scores"]
                }}
            )
            return None

        # Step 5: Value prop lookup
        vp = self.determine_value_prop(article)

        # Step 6: Generate infra insight
        infra_data = self.llm.generate_infra_insight(article, angle_result)

        # Step 7: Prepare insight document
        insight_doc = {
            "raw_content_id": article_id,
            "angle_type": angle_result["angle_type"],
            "hook_sentence": angle_result["hook_sentence"],
            "core_claim": angle_result["core_claim"],
            "megallm_tie_in": angle_result["megallm_tie_in"],
            "icp_score": icp_score,
            "icp_scores": icp_result["icp_scores"],
            "infra_data_point": infra_data,
            "value_prop_key": vp["value_prop_key"],
            "value_prop_hook": vp["value_prop_hook"],
            "value_prop_cta": vp["value_prop_cta"],
            "status": "pending_generation",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Step 8: Insert insight
        result = self.content_insights.insert_one(insight_doc)
        insight_id = result.inserted_id

        # Step 9: Update article status
        self.articles.update_one(
            {"_id": article_id},
            {"$set": {
                "status": "intelligence_done",
                "insight_id": insight_id
            }}
        )

        logger.info(f"Successfully processed article {article_id} -> insight {insight_id}")
        return insight_doc

    def run(self):
        """Run the full pipeline."""
        logger.info("Starting Content Intelligence Pipeline")
        logger.info(f"Using OpenRouter API: {self.config.openai_base_url}")
        logger.info(f"Model: {self.config.openai_model}")

        articles = self.fetch_pending_articles()
        if not articles:
            logger.info("No pending articles to process")
            return

        total = len(articles)
        processed = 0
        failed = 0
        duplicates = 0
        low_icp = 0
        success = 0
        quota_exhausted = False

        for i in range(0, total, self.config.batch_size):
            batch = articles[i:i + self.config.batch_size]
            logger.info(f"Processing batch {i // self.config.batch_size + 1}/{math.ceil(total / self.config.batch_size)}")

            for article in batch:
                try:
                    result = self.process_article(article)
                    processed += 1

                    if result is None:
                        # FIX 7: Re-fetching from Qdrant to classify None result is wasteful and
                        # unreliable — the article's updated status is already written to MongoDB.
                        # Read it from there directly instead of calling check_duplicate again.
                        updated = self.articles.find_one({"_id": article["_id"]})
                        if updated is None:
                            failed += 1
                        elif updated.get("status") == "duplicate":
                            duplicates += 1
                        elif updated.get("status") == "low_icp":
                            low_icp += 1
                        else:
                            failed += 1
                    else:
                        success += 1

                except Exception as e:
                    if isinstance(e, LLMQuotaExceededError):
                        logger.error("LLM daily quota exceeded; stopping pipeline early.")
                        quota_exhausted = True
                        break
                    logger.error(f"Unexpected error processing article {article['_id']}: {e}")
                    failed += 1

            if quota_exhausted:
                break

        if quota_exhausted:
            logger.warning("Pipeline stopped early due to LLM quota exhaustion.")

        logger.info("=" * 50)
        logger.info("Pipeline Summary:")
        logger.info(f"  Total articles: {total}")
        logger.info(f"  Processed: {processed}")
        logger.info(f"  Successful: {success}")
        logger.info(f"  Duplicates: {duplicates}")
        logger.info(f"  Low ICP: {low_icp}")
        logger.info(f"  Failed: {failed}")
        logger.info("=" * 50)

    def close(self):
        """Close connections."""
        self.mongo_client.close()


# ============================================================================
# SCHEDULER / MAIN
# ============================================================================

def run_pipeline():
    """Run pipeline once."""
    # Load .env before constructing Config so all env-based settings are applied.
    bootstrap_env(__file__)

    config = Config()

    # Force read from .env to override any cached environ vars
    api_key = None
    env_path = Path('.env')
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.startswith('OPENROUTER_API_KEY='):
                api_key = line.split('=', 1)[1].strip().strip('"\'')
                break
            if line.startswith('OPENAI_API_KEY='):
                api_key = line.split('=', 1)[1].strip().strip('"\'')
                break
    
    if not api_key:
        # Fallback to resolve_api_key if .env doesn't have it
        api_key = resolve_api_key()
    
    if not api_key:
        logger.error("OPENROUTER_API_KEY or OPENAI_API_KEY not found")
        logger.error("Set one of the following and re-run:")
        logger.error("  export OPENROUTER_API_KEY='sk-or-v1-...'")
        logger.error("  # or")
        logger.error("  export OPENAI_API_KEY='your_api_key_here'")
        logger.error("You can also create a .env file in this folder with either key.")
        return

    config.openai_api_key = api_key
    logger.info(f"Using API key from .env: {api_key[:20]}...")

    pipeline = ContentIntelligencePipeline(config)
    try:
        pipeline.run()
    finally:
        pipeline.close()


def run_scheduler(interval_hours: int = 2):
    """Run pipeline on schedule."""
    import time
    import schedule

    logger.info(f"Starting scheduler (interval: {interval_hours} hours)")
    logger.info(f"MegaLLM API Endpoint: https://ai.megallm.io/v1")

    schedule.every(interval_hours).hours.do(run_pipeline)

    # Run immediately on start
    run_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        run_scheduler(interval_hours=2)
    else:
        run_pipeline()
