#!/usr/bin/env python3
"""
MegaLLM WF2 – Content Generation Pipeline
Triggered by WF1 with a content_insight_id.
Generates LinkedIn (A/B), Twitter/X (A/B), Blog, and Newsletter content.
Stores all drafts in generated_posts, then fires WF3 webhook.
"""

import os
import json
import logging
import math
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import requests
from pymongo import MongoClient
from pymongo.collection import Collection
from bson import ObjectId
from workflow_common import LLMQuotaExceededError, bootstrap_env, resolve_api_key
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class InsightNotFoundError(Exception):
    """Raised when the requested insight_id does not exist."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class WF2Config:
    # MegaLLM / OpenAI-compatible
    api_key: str = field(default_factory=lambda: os.getenv("MEGALLM_API_KEY", os.getenv("OPENAI_API_KEY", "sk-mega-6c309f77db9167850e784c25d8f8f93b672b2173b4dd791aa5c31a5ff6bd4329")))
    api_base_url: str = "https://ai.megallm.io/v1"
    model: str = field(
        default_factory=lambda: os.getenv(
            "WF2_MODEL", os.getenv("OPENAI_MODEL", "deepseek-ai/deepseek-v3.1")
        )
    )

    # MongoDB
    mongodb_uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    mongodb_db: str = field(default_factory=lambda: os.getenv("MONGODB_DB", "megallm"))

    # Serper (SEO brief)
    serper_api_key: str = field(default_factory=lambda: os.getenv("SERPER_API_KEY", ""))
    serper_url: str = "https://google.serper.dev/search"
    serper_num_results: int = 10

    # WF3 webhook
    wf3_webhook_url: str = field(
        default_factory=lambda: os.getenv("WF3_WEBHOOK_URL", "")
    )

    # Generation params (per spec)
    linkedin_max_tokens: int = 600
    twitter_max_tokens: int = 800
    blog_max_tokens: int = 3000
    newsletter_max_tokens: int = 1500

    linkedin_temp_a: float = 0.70
    linkedin_temp_b: float = 0.85
    twitter_temp_a: float = 0.75
    twitter_temp_b: float = 0.85
    blog_temp: float = 0.65
    newsletter_temp: float = 0.72


# ---------------------------------------------------------------------------
# LLM client (OpenAI-compatible)
# ---------------------------------------------------------------------------

class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(url, headers=self._headers, json=payload, timeout=300)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as exc:
            logger.error(f"LLM HTTP error: {exc}")
            if exc.response is not None:
                logger.error(f"Body: {exc.response.text}")
                if exc.response.status_code == 429:
                    raise LLMQuotaExceededError(exc.response.text) from exc
            raise
        except requests.exceptions.RequestException as exc:
            logger.error(f"LLM request error: {exc}")
            raise


# ---------------------------------------------------------------------------
# Serper SEO brief
# ---------------------------------------------------------------------------

def fetch_seo_brief(keyword: str, config: WF2Config) -> Dict[str, Any]:
    """
    POST to Serper to get top-N ranking results for gap analysis.
    Returns a dict with organic results (title, snippet, link).
    Falls back to empty dict on any error so Blog generation still proceeds.
    """
    if not config.serper_api_key:
        logger.warning("SERPER_API_KEY not set – skipping SEO brief.")
        return {}

    headers = {
        "X-API-KEY": config.serper_api_key,
        "Content-Type": "application/json",
    }
    payload = {"q": keyword, "num": config.serper_num_results}

    try:
        resp = requests.post(
            config.serper_url, headers=headers, json=payload, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        organic = data.get("organic", [])
        brief = []
        for item in organic[: config.serper_num_results]:
            brief.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                }
            )
        logger.info(f"Fetched {len(brief)} SEO results for '{keyword}'")
        return {"keyword": keyword, "results": brief}
    except Exception as exc:
        logger.warning(f"Serper fetch failed for '{keyword}': {exc} — continuing without SEO brief.")
        return {}


# ---------------------------------------------------------------------------
# Per-platform generation functions
# ---------------------------------------------------------------------------

LINKEDIN_SYSTEM = """You are an expert B2B LinkedIn content writer for MegaLLM, an LLM inference API platform.

Audience: CTOs at $500K–$10M ARR AI startups in UK, Singapore, Australia, and New Zealand.

Format rules:
- Hook line first — must also work as a standalone tweet (≤ 220 chars).
- 4 body paragraphs expanding the insight with concrete detail.
- Soft CTA closing paragraph pointing to MegaLLM.
- Total post ≤ 1300 characters.
- No hashtag spam — maximum 3 relevant hashtags at the very end.
- Plain text. No markdown bold or bullets.

Additional quality rules:
- Write for technical decision-makers, not a general audience.
- Prefer concrete operational language (latency, cost per token, uptime, throughput, deployment risk).
- Keep each paragraph 1–3 sentences; avoid long walls of text.
- Make at least one sentence clearly decision-oriented (what the CTO should do next).
- Reference one specific metric when available from input (%, ms, $, req/sec, tokens/sec).
- Keep tone confident, concise, and implementation-aware.
- Avoid clichés and banned openers like "In today's world" or "This is important because".
- Mention MegaLLM naturally in the CTA, without hard selling.

Narrative structure requirements:
- Paragraph 1 should translate the hook into a concrete operational risk or opportunity.
- Paragraph 2 should quantify the impact with one realistic metric or benchmark framing.
- Paragraph 3 should present a practical execution path (benchmark, routing policy, failover, or migration step).
- Paragraph 4 should highlight a trade-off and how to reduce implementation risk.

Language and output constraints:
- Avoid repeating the same sentence pattern across paragraphs.
- Avoid broad claims without context.
- Keep the final text clean plain text with natural line breaks between paragraphs.
- Ensure the output is valid JSON with properly escaped quotes/newlines.

Output a single JSON object:
{"post": "<full post text>"}"""

TWITTER_SYSTEM = """You are an expert tech Twitter/X thread writer for MegaLLM.

Audience: CTOs and senior engineers at AI startups.

Format rules:
- Max 8 tweets in the thread.
- Tweet 1 ≤ 220 characters (the hook).
- At least one tweet must lead with a number or statistic.
- Each tweet is self-contained but flows with the next.
- Final tweet ends with a soft CTA to MegaLLM.

Additional quality rules:
- Write for experienced builders (CTOs, staff/principal engineers, infra leads).
- Keep every tweet specific and useful; avoid generic advice.
- Include at least one practical operator takeaway (migration, benchmarking, failover, routing, or cost control).
- Prefer short, punchy sentences and active voice.
- Ensure claim continuity across tweets: problem -> implication -> action.
- Avoid hashtags except at most one in the final tweet.
- Do not use markdown, numbering prefixes like "1/", or emojis.

Thread composition requirements:
- Tweet 2-3 should establish context quickly with concrete technical framing.
- Mid-thread tweets should include one tactical insight and one decision implication.
- Include one tweet that names a measurable KPI to monitor after implementation.
- Final CTA tweet should feel advisory, not promotional.

Output reliability rules:
- Return only a JSON array of strings.
- Ensure each tweet can stand alone if screenshotted.
- Avoid duplicated phrasing across tweets.

Output ONLY a JSON array of tweet strings, e.g.:
["Tweet 1 text", "Tweet 2 text", ...]"""

BLOG_SYSTEM = """You are an expert B2B SEO content writer for MegaLLM.

Format rules:
- Minimum 1200 words.
- H2 headings for major sections (use markdown ## syntax).
- Include an FAQ section near the end with 3–5 questions.
- Add schema hints as HTML comments, e.g. <!-- schema: FAQPage -->.
- Use internal link placeholders: [[link: <anchor text>]].
- Naturally weave in MegaLLM as the solution throughout.
- Do NOT keyword-stuff. Write for a technical CTO audience.

Additional quality rules:
- Start with a tight executive framing paragraph for startup CTOs.
- Use concrete sub-sections that cover trade-offs, implementation steps, and risks.
- Include at least one quantified example per major section when possible.
- Prefer credible ranges and assumptions over vague superlatives.
- Explain "why now" and "what to do next" for each major claim.
- Keep prose practical and architecture-aware (latency budgets, reliability targets, compliance constraints).
- Avoid repetitive phrasing and generic filler transitions.

Editorial structure requirements:
- Include a clear problem statement, then options analysis, then recommended path.
- Add one section focused on migration sequencing and rollback safety.
- Add one section focused on measurement (KPIs, baselines, and post-change validation).
- FAQ answers must be concise, implementation-minded, and non-marketing.

Style and trust requirements:
- Use neutral, credible language; avoid overclaiming.
- When numbers are illustrative, frame assumptions explicitly.
- Ensure internal link placeholders appear naturally in context.

Output the full blog post as plain markdown text (no JSON wrapper)."""

NEWSLETTER_SYSTEM = """You are writing a comprehensive, engaging B2B newsletter digest for MegaLLM.

Audience: CTOs at AI startups in UK, Singapore, Australia, New Zealand. Technical, data-driven decision makers.

Format rules (detailed 5-part structure):
1. Hook Insight — the compelling key takeaway from this week's article (3–4 sentences, build tension/context).
2. Why This Matters — specific business implications for AI startup infrastructure and operations (3–4 sentences with at least one concrete scenario).
3. Infra Takeaway — quantified infrastructure data points, benchmarks, or architecture implications (4–5 sentences, include specific numbers, percentages, latency impacts, cost examples when possible).
4. Interactive Element — one thought-provoking question, a brief comparison table concept, or a decision framework snippet that encourages action (2–3 sentences).
5. MegaLLM Angle — how MegaLLM specifically addresses this challenge (4–5 sentences, map to concrete value: cost reduction %, speed improvement, uptime guarantee, feature parity, or compliance enablement).
End with a compelling but soft CTA sentence (benchmark comparison, 30-min pilot offer, or migration readiness check).
Total: 650–850 words. Plain text, no markdown. Conversational yet technical tone.

Additional quality rules:
- Keep language engaging, technical, and action-oriented for forward-thinking CTOs.
- Use concrete examples: "reduces latency by 40ms per inference" instead of "improves performance."
- Include at least two explicit numbers or metrics in the Infra Takeaway section.
- Ensure every section drives toward a specific business outcome (cost, speed, reliability, flexibility, or compliance).
- Avoid filler phrases; every sentence should have information density.
- Create natural transitions between sections; this should read like a narrative, not a checklist.
- Interactive Element should feel relevant and not forced (e.g., "Quick self-assess: Is your team managing N GPUs across M clusters?" suggests a pain point they might relate to).
- CTA should offer a clear, low-friction next step (whitepaper download, architecture review, or live demo with specific use case)."""


def _parse_json_response(raw: str, fallback_key: str = "content") -> Any:
    """Strip markdown fences and parse JSON; return raw string on failure."""
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("[") if cleaned.lstrip().startswith("[") else cleaned.find("{")
    # prefer array over object if both present
    arr_pos = cleaned.find("[")
    obj_pos = cleaned.find("{")
    if arr_pos != -1 and (obj_pos == -1 or arr_pos < obj_pos):
        start = arr_pos
        end = cleaned.rfind("]")
    else:
        start = obj_pos
        end = cleaned.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass
    return raw  # return raw string so generation is never silently lost


def generate_linkedin(
    insight: Dict, llm: LLMClient, config: WF2Config
) -> Tuple[str, str]:
    """Returns (variant_a_text, variant_b_text)."""

    base_user = f"""Insight:
Hook: {insight.get('hook_sentence', '')}
Core claim: {insight.get('core_claim', '')}
MegaLLM tie-in: {insight.get('megallm_tie_in', '')}
Infra data point: {insight.get('infra_data_point', '')}
Value prop hook: {insight.get('value_prop_hook', '')}
CTA: {insight.get('value_prop_cta', '')}"""

    user_a = base_user + "\n\nHook style: provocative, bold claim opener."
    user_b = base_user + "\n\nHook style: analytic, data-driven opener."

    raw_a = llm.complete(LINKEDIN_SYSTEM, user_a, config.linkedin_temp_a, config.linkedin_max_tokens)
    raw_b = llm.complete(LINKEDIN_SYSTEM, user_b, config.linkedin_temp_b, config.linkedin_max_tokens)

    def extract(raw: str) -> str:
        parsed = _parse_json_response(raw)
        if isinstance(parsed, dict):
            return parsed.get("post", raw)
        return raw

    return extract(raw_a), extract(raw_b)


def generate_twitter(
    insight: Dict, llm: LLMClient, config: WF2Config
) -> Tuple[List[str], List[str]]:
    """Returns (variant_a_tweets, variant_b_tweets)."""

    base_user = f"""Insight:
Hook: {insight.get('hook_sentence', '')}
Core claim: {insight.get('core_claim', '')}
Infra data point: {insight.get('infra_data_point', '')}
MegaLLM CTA: {insight.get('value_prop_cta', '')}"""

    user_a = base_user + "\n\nThread style: bold claim opener on tweet 1."
    user_b = base_user + "\n\nThread style: question-led opener on tweet 1."

    raw_a = llm.complete(TWITTER_SYSTEM, user_a, config.twitter_temp_a, config.twitter_max_tokens)
    raw_b = llm.complete(TWITTER_SYSTEM, user_b, config.twitter_temp_b, config.twitter_max_tokens)

    def extract(raw: str) -> List[str]:
        parsed = _parse_json_response(raw)
        if isinstance(parsed, list):
            return [str(t) for t in parsed]
        # fallback: split on numbered lines
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        return lines[:8] if lines else [raw]

    return extract(raw_a), extract(raw_b)


def generate_blog(
    insight: Dict, seo_brief: Dict, llm: LLMClient, config: WF2Config
) -> str:
    """Returns full blog markdown."""

    seo_context = ""
    if seo_brief.get("results"):
        top = seo_brief["results"][:3]
        seo_context = "\n\nSEO gap analysis — top 3 ranking articles on this keyword:\n"
        for i, r in enumerate(top, 1):
            seo_context += f"{i}. {r['title']}: {r['snippet']}\n"
        seo_context += "\nYour post must cover angles these articles miss."

    user = f"""Target keyword: {insight.get('infra_data_point', insight.get('core_claim', 'LLM infrastructure'))}

Insight data:
Hook: {insight.get('hook_sentence', '')}
Core claim: {insight.get('core_claim', '')}
Angle type: {insight.get('angle_type', '')}
MegaLLM tie-in: {insight.get('megallm_tie_in', '')}
Infra data point: {insight.get('infra_data_point', '')}
{seo_context}

Write the full SEO blog post now."""

    return llm.complete(BLOG_SYSTEM, user, config.blog_temp, config.blog_max_tokens)


def generate_newsletter(
    insight: Dict, llm: LLMClient, config: WF2Config
) -> str:
    """Returns newsletter digest text."""

    user = f"""This week's insight:
Hook: {insight.get('hook_sentence', '')}
Core claim: {insight.get('core_claim', '')}
Infra data point: {insight.get('infra_data_point', '')}
MegaLLM angle: {insight.get('megallm_tie_in', '')}
CTA: {insight.get('value_prop_cta', '')}

Write the newsletter digest now."""

    return llm.complete(NEWSLETTER_SYSTEM, user, config.newsletter_temp, config.newsletter_max_tokens)


# ---------------------------------------------------------------------------
# Parallel generation orchestrator
# ---------------------------------------------------------------------------

def _run_all_platforms(
    insight: Dict,
    seo_brief: Dict,
    llm: LLMClient,
    config: WF2Config,
) -> Dict[str, Any]:
    """
    Run all platform generation tasks concurrently.
    Returns a dict keyed by task name with the raw output.
    """
    tasks = {
        "linkedin": lambda: generate_linkedin(insight, llm, config),
        "twitter": lambda: generate_twitter(insight, llm, config),
        "blog": lambda: generate_blog(insight, seo_brief, llm, config),
        "newsletter": lambda: generate_newsletter(insight, llm, config),
    }

    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    # ThreadPoolExecutor mirrors n8n's concurrent branch behaviour
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_name = {executor.submit(fn): name for name, fn in tasks.items()}

        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except LLMQuotaExceededError:
                raise  # propagate immediately — stop everything
            except Exception as exc:
                logger.error(f"Generation failed for platform '{name}': {exc}")
                errors[name] = str(exc)
                results[name] = None  # will be filtered out during payload build

    if errors:
        logger.warning(f"Some platforms failed: {list(errors.keys())}")

    return results


# ---------------------------------------------------------------------------
# Payload builder  →  generated_posts rows
# ---------------------------------------------------------------------------

def build_insert_payloads(
    insight_id: str,
    results: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Converts raw generation output into generated_posts insert documents.
    Produces up to 7 rows per insight:
      LinkedIn A, LinkedIn B, Twitter A, Twitter B, Blog, Newsletter,
      Blog SEO meta.
    """
    now = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []

    # Keep both string and ObjectId forms so downstream queries can match either schema.
    try:
        content_insight_id: Any = ObjectId(insight_id)
    except Exception:
        content_insight_id = insight_id

    # -- LinkedIn --
    linkedin = results.get("linkedin")
    if linkedin and isinstance(linkedin, tuple) and len(linkedin) == 2:
        text_a, text_b = linkedin
        for variant, text in [("A", text_a), ("B", text_b)]:
            rows.append(
                {
                    "insight_id": insight_id,
                    "content_insight_id": content_insight_id,
                    "platform": "linkedin",
                    "variant": variant,
                    "content": text,
                    "meta": {},
                    "status": "draft",
                    "created_at": now,
                }
            )

    # -- Twitter --
    twitter = results.get("twitter")
    if twitter and isinstance(twitter, tuple) and len(twitter) == 2:
        tweets_a, tweets_b = twitter
        for variant, tweets in [("A", tweets_a), ("B", tweets_b)]:
            rows.append(
                {
                    "insight_id": insight_id,
                    "content_insight_id": content_insight_id,
                    "platform": "twitter",
                    "variant": variant,
                    "content": json.dumps(tweets),   # store as JSON string
                    "meta": {"tweet_count": len(tweets)},
                    "status": "draft",
                    "created_at": now,
                }
            )

    # -- Blog --
    blog = results.get("blog")
    if blog and isinstance(blog, str):
        rows.append(
            {
                "insight_id": insight_id,
                "content_insight_id": content_insight_id,
                "platform": "blog",
                "variant": "A",          # single variant for blog
                "content": blog,
                "meta": {"word_count": len(blog.split())},
                "status": "draft",
                "created_at": now,
            }
        )
        # Blog SEO meta row
        rows.append(
            {
                "insight_id": insight_id,
                "content_insight_id": content_insight_id,
                "platform": "blog_seo_meta",
                "variant": "A",
                "content": "",
                "meta": {
                    "word_count": len(blog.split()),
                    "has_faq": "## FAQ" in blog or "## Frequently" in blog,
                    "has_schema_hints": "<!-- schema:" in blog,
                    "internal_link_placeholders": blog.count("[[link:"),
                },
                "status": "draft",
                "created_at": now,
            }
        )

    # -- Newsletter --
    newsletter = results.get("newsletter")
    if newsletter and isinstance(newsletter, str):
        rows.append(
            {
                "insight_id": insight_id,
                "content_insight_id": content_insight_id,
                "platform": "newsletter",
                "variant": "A",
                "content": newsletter,
                "meta": {"word_count": len(newsletter.split())},
                "status": "draft",
                "created_at": now,
            }
        )

    return rows


# ---------------------------------------------------------------------------
# MongoDB helpers
# ---------------------------------------------------------------------------

def fetch_insight(insight_id: str, db) -> Dict[str, Any]:
    """
    Mirrors WF1 node 2:
      SELECT ci.*, rc.full_content, rc.keywords
      FROM content_insights ci
      JOIN raw_content rc ON rc.id = ci.raw_content_id
      WHERE ci.id = <insight_id>
    MongoDB equivalent: lookup from raw_content.
    """
    try:
        oid = ObjectId(insight_id)
    except Exception:
        oid = insight_id  # allow string IDs too

    insight = db.content_insights.find_one({"_id": oid})
    if not insight:
        raise InsightNotFoundError(f"No content_insight found for id={insight_id}")

    # Enrich with raw_content fields if available
    raw_content_id = insight.get("raw_content_id")
    if raw_content_id:
        raw = db.articles.find_one({"_id": raw_content_id})
        if raw:
            insight["full_content"] = raw.get("content", "")
            insight["keywords"] = raw.get("categories", [])

    return insight


def write_posts(posts: List[Dict], collection: Collection) -> List[str]:
    """Bulk-insert generated_posts rows; returns inserted IDs as strings."""
    if not posts:
        return []
    result = collection.insert_many(posts)
    ids = [str(oid) for oid in result.inserted_ids]
    logger.info(f"Inserted {len(ids)} generated_post rows.")
    return ids


# ---------------------------------------------------------------------------
# WF3 webhook trigger
# ---------------------------------------------------------------------------

def trigger_wf3(post_ids: List[str], wf3_url: str) -> None:
    """POST generated_post IDs to WF3 webhook."""
    if not wf3_url:
        logger.info("WF3_WEBHOOK_URL not set — skipping WF3 trigger.")
        return

    payload = {"generated_post_ids": post_ids}
    try:
        resp = requests.post(wf3_url, json=payload, timeout=30)
        resp.raise_for_status()
        logger.info(f"WF3 triggered successfully (HTTP {resp.status_code}).")
    except requests.exceptions.RequestException as exc:
        # Non-fatal: WF3 can be re-triggered manually.
        logger.error(f"WF3 webhook failed: {exc}")


# ---------------------------------------------------------------------------
# Main pipeline class
# ---------------------------------------------------------------------------

class ContentGenerationPipeline:
    def __init__(self, config: WF2Config):
        self.config = config
        self.llm = LLMClient(config.api_key, config.api_base_url, config.model)
        self.mongo_client = MongoClient(config.mongodb_uri)
        self.db = self.mongo_client[config.mongodb_db]
        self.generated_posts: Collection = self.db.generated_posts

    def run(self, insight_id: str) -> List[str]:
        """
        Full WF2 execution for one insight_id.
        Returns list of inserted generated_post IDs.
        """
        logger.info(f"WF2 started for insight_id={insight_id}")

        # Node 2 — fetch insight + raw content
        insight = fetch_insight(insight_id, self.db)
        logger.info(f"Fetched insight: {insight.get('angle_type')} / {insight.get('hook_sentence', '')[:60]}")

        # Node 3 — SEO brief (blog only, runs before parallel branches)
        target_keyword = insight.get("infra_data_point") or insight.get("core_claim", "LLM inference")
        seo_brief = fetch_seo_brief(target_keyword, self.config)

        # Node 4–10 — parallel generation across all platforms
        results = _run_all_platforms(insight, seo_brief, self.llm, self.config)

        # Node 12 — build insert payloads
        posts = build_insert_payloads(insight_id, results)
        logger.info(f"Built {len(posts)} post payloads.")

        # Node 13 — write to generated_posts
        post_ids = write_posts(posts, self.generated_posts)

        # Update insight status
        from bson import ObjectId as OID
        try:
            oid = OID(insight_id)
        except Exception:
            oid = insight_id
        self.db.content_insights.update_one(
            {"_id": oid},
            {"$set": {"status": "generation_done", "post_ids": post_ids}},
        )

        # Node 14 — trigger WF3
        trigger_wf3(post_ids, self.config.wf3_webhook_url)

        logger.info(f"WF2 complete. {len(post_ids)} posts created for insight {insight_id}.")
        return post_ids

    def close(self) -> None:
        self.mongo_client.close()


# ---------------------------------------------------------------------------
# Lightweight HTTP webhook server (replaces n8n Webhook trigger node)
# ---------------------------------------------------------------------------

def run_webhook_server(config: WF2Config, host: str = "0.0.0.0", port: int = 5002) -> None:
    """
    Starts a minimal HTTP server that accepts POST /generate
    with body {"insight_id": "<id>"} and runs the pipeline.
    """
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # suppress default HTTP log spam
            logger.info(f"HTTP {self.address_string()} - {format % args}")

        def do_POST(self):
            if self.path != "/generate":
                self.send_response(404)
                self.end_headers()
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            try:
                data = json.loads(body)
                insight_id = data.get("insight_id", "").strip()
                if not insight_id:
                    raise ValueError("insight_id is required")
            except (json.JSONDecodeError, ValueError) as exc:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode())
                return

            pipeline = ContentGenerationPipeline(config)
            try:
                post_ids = pipeline.run(insight_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"status": "ok", "post_ids": post_ids}).encode()
                )
            except InsightNotFoundError as exc:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode())
            except LLMQuotaExceededError:
                self.send_response(429)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "LLM quota exceeded"}).encode())
            except Exception as exc:
                logger.exception(f"Pipeline error: {exc}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode())
            finally:
                pipeline.close()

    server = HTTPServer((host, port), Handler)
    logger.info(f"WF2 webhook server listening on http://{host}:{port}/generate")
    logger.info("Send POST requests with body: {\"insight_id\": \"<id>\"}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down webhook server.")
        server.shutdown()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_config() -> WF2Config:
    bootstrap_env(__file__)
    api_key = resolve_api_key()
    if not api_key:
        logger.error("MEGALLM_API_KEY or OPENAI_API_KEY not set.")
        raise SystemExit(1)
    cfg = WF2Config()
    cfg.api_key = api_key
    return cfg


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    cfg = _build_config()

    # --server : run as webhook server
    if args and args[0] == "--server":
        host = "0.0.0.0"
        port = 5002
        for arg in args[1:]:
            if arg.startswith("--port="):
                port = int(arg.split("=", 1)[1])
            elif arg.startswith("--host="):
                host = arg.split("=", 1)[1]
        run_webhook_server(cfg, host=host, port=port)

    # --insight <id> : run once for a given insight_id
    elif len(args) >= 2 and args[0] == "--insight":
        insight_id = args[1]
        pipeline = ContentGenerationPipeline(cfg)
        try:
            ids = pipeline.run(insight_id)
            print(json.dumps({"status": "ok", "post_ids": ids}, indent=2))
        finally:
            pipeline.close()

    else:
        script_name = os.path.basename(__file__)
        print(
            "Usage:\n"
            f"  python {script_name} --insight <insight_id>\n"
            f"  python {script_name} --server [--host=0.0.0.0] [--port=5002]\n"
        )
        raise SystemExit(0)

