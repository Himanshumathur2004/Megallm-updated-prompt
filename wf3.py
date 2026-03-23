#!/usr/bin/env python3
"""
MegaLLM WF3 – Quality Control Pipeline
Triggered by WF2 with a list of generated_post_ids.
Scores each post, rewrites if 5–6.9, shelves if < 5 or still < 7 after rewrite.
Approved posts trigger WF4. Shelved posts notify Slack #content-ops.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional, Tuple

import requests
from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from workflow_common import LLMQuotaExceededError, bootstrap_env, resolve_api_key

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class WF3Config:
    # Scorer model — cheaper, high-volume
    scorer_api_key: str = ""
    scorer_base_url: str = "https://ai.megallm.io/v1"
    scorer_model: str = field(default_factory=lambda: os.getenv("WF3_SCORER_MODEL", "deepseek-ai/deepseek-v3.1"))

    # Rewrite model — consistent voice with WF2
    rewrite_api_key: str = ""
    rewrite_base_url: str = "https://ai.megallm.io/v1"
    rewrite_model: str = field(default_factory=lambda: os.getenv("WF3_REWRITE_MODEL", "deepseek-ai/deepseek-v3.1"))

    # MongoDB
    mongodb_uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    mongodb_db: str = field(default_factory=lambda: os.getenv("MONGODB_DB", "megallm"))

    # Slack
    slack_webhook_url: str = field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", ""))
    slack_channel: str = "#content-ops"

    # WF4 webhook
    wf4_webhook_url: str = field(default_factory=lambda: os.getenv("WF4_WEBHOOK_URL", ""))

    # Scoring thresholds
    approve_threshold: float = 7.0
    rewrite_threshold: float = 5.0
    max_qc_attempts: int = 2          # hard cap: 1 original + 1 rewrite

    # Token budgets
    scorer_max_tokens: int = 500
    rewrite_max_tokens: int = 1200
    rewrite_temperature: float = 0.7


# ---------------------------------------------------------------------------
# LLM client (OpenAI-compatible, reused pattern from WF1/WF2)
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
        temperature: float = 0.3,
        max_tokens: int = 500,
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
            resp = requests.post(url, headers=self._headers, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None:
                logger.error(f"LLM HTTP {exc.response.status_code}: {exc.response.text[:300]}")
                if exc.response.status_code == 429:
                    raise LLMQuotaExceededError(exc.response.text) from exc
            raise
        except requests.exceptions.RequestException as exc:
            logger.error(f"LLM request error: {exc}")
            raise


# ---------------------------------------------------------------------------
# Scoring rubric prompts
# ---------------------------------------------------------------------------

SCORER_SYSTEM = """You are a senior content quality evaluator for MegaLLM, an LLM inference API.

ICP: CTOs at $500K–$10M ARR AI startups in UK, Singapore, Australia, and New Zealand.

Score the post on exactly 5 dimensions, each 1–10:

1. hook_strength (weight 25%)
   Does the first line create a strong reason to keep reading?
   Would it stop a CTO mid-scroll? Punish vague openers.

2. specificity (weight 25%)
   Are all claims concrete and numerical?
   Penalise phrases like "many companies", "significant cost", "some teams".

3. icp_resonance (weight 20%)
   Would a CTO at a $500K–$10M ARR AI startup in UK/SG/AU/NZ genuinely care?
   Penalise generic tech content with no inference/ops angle.

4. brand_fit (weight 20%)
   Does the MegaLLM tie-in feel natural and earned?
   Is the CTA subtle — not salesy or forced?

5. engagement_signal (weight 10%)
   Does it invite replies, shares, or saves?
   Is there a clear point of view that sparks discussion?

Weighted total = (hook*0.25 + specificity*0.25 + icp*0.20 + brand*0.20 + engagement*0.10)
Round to 1 decimal place.

Return ONLY valid JSON, no markdown, no preamble:
{
  "hook_strength": <1-10>,
  "specificity": <1-10>,
  "icp_resonance": <1-10>,
  "brand_fit": <1-10>,
  "engagement_signal": <1-10>,
  "weighted_total": <float, 1 decimal>,
  "critique": "<2-4 sentences: what is weakest and exactly how to fix it>"
}

CALIBRATION NOTES
- Score 5 means average and not publish-ready; rewrite should still be recommended.
- Score 7 means clearly useful but missing one high-impact improvement.
- Score 9+ requires concrete metrics and a strong decision signal for CTOs.

CRITIQUE REQUIREMENTS
- Name the single weakest dimension first.
- Provide at least one exact rewrite instruction (what to add/remove/change).
- Prefer operational guidance (metric, architecture implication, implementation step).
- Avoid generic feedback like "be more engaging" without specifics.

EVALUATION CONSISTENCY RULES
- Penalize marketing-heavy language that lacks technical evidence.
- Penalize unclear CTA or forced brand mention.
- Reward posts that convert insight into a clear next action.
- Reward precise numbers with units and context.

Strictly output JSON only."""


def _score_post(
    post: Dict[str, Any],
    scorer: LLMClient,
    config: WF3Config,
) -> Dict[str, Any]:
    """
    Node 4 — call scorer model.
    Returns parsed score dict. On parse failure returns a default 5.0 score
    so the post always enters the rewrite path rather than crashing.
    """
    platform = post.get("platform", "unknown")
    content = post.get("content", "")

    # Twitter posts are stored as JSON arrays — flatten for the scorer
    if platform == "twitter":
        try:
            tweets = json.loads(content)
            if isinstance(tweets, list):
                content = "\n\n".join(f"Tweet {i+1}: {t}" for i, t in enumerate(tweets))
        except (json.JSONDecodeError, TypeError):
            pass

    user_prompt = f"""Platform: {platform}
Variant: {post.get('variant', 'A')}

--- POST CONTENT START ---
{content}
--- POST CONTENT END ---

Score this post now."""

    raw = None
    try:
        raw = scorer.complete(
            SCORER_SYSTEM,
            user_prompt,
            temperature=0.3,
            max_tokens=config.scorer_max_tokens,
        )
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in scorer response")
        scores = json.loads(cleaned[start : end + 1])

        # Validate all required keys exist
        required = ["hook_strength", "specificity", "icp_resonance",
                    "brand_fit", "engagement_signal", "weighted_total", "critique"]
        missing = [k for k in required if k not in scores]
        if missing:
            raise ValueError(f"Missing score keys: {missing}")

        scores["weighted_total"] = float(scores["weighted_total"])
        return scores

    except Exception as exc:
        # Node 5 parse-fail default: score 5.0 → triggers rewrite path
        logger.warning(f"Score parse failed for post {post.get('_id')}: {exc}. Defaulting to 5.0.")
        return {
            "hook_strength": 5,
            "specificity": 5,
            "icp_resonance": 5,
            "brand_fit": 5,
            "engagement_signal": 5,
            "weighted_total": 5.0,
            "critique": f"Score parse failed ({exc}). Automatic rewrite triggered.",
            "raw_response": raw,
        }


# ---------------------------------------------------------------------------
# Platform-specific rewrite system prompts (must match WF2 voice)
# ---------------------------------------------------------------------------

_REWRITE_SYSTEM_BY_PLATFORM = {
    "linkedin": """You are an expert B2B LinkedIn content writer for MegaLLM, an LLM inference API platform.
Audience: CTOs at $500K–$10M ARR AI startups in UK, Singapore, Australia, and New Zealand.
Format: Hook line ≤ 220 chars, 4 body paragraphs, soft CTA, total ≤ 1300 chars, max 3 hashtags.
Additional quality rules: write for technical decision-makers; include concrete operational language
(latency, token cost, uptime, throughput); keep paragraphs concise; include at least one
decision-oriented sentence; avoid generic intros/filler; keep CTA soft and implementation-aware.
Rewrite emphasis: preserve core angle while sharpening specificity and execution guidance.
Ensure at least one paragraph gives an immediate practical next step.
Avoid repetitive sentence openings; keep tone confident and technical.
Output a single JSON object: {"post": "<full post text>"}""",

    "twitter": """You are an expert tech Twitter/X thread writer for MegaLLM.
Audience: CTOs and senior engineers at AI startups.
Format: Max 8 tweets, Tweet 1 ≤ 220 chars, one number-forward tweet, soft CTA last.
Additional quality rules: keep each tweet self-contained and specific; maintain logical flow
from problem to implication to action; include at least one practical infra takeaway; avoid
generic advice, markdown, numbering prefixes, and emojis.
Rewrite emphasis: maximize clarity-per-character and remove low-signal wording.
Include one concrete KPI or benchmark implication in the thread body.
Keep final CTA advisory and low-pressure.
Output ONLY a JSON array of tweet strings.""",

    "blog": """You are an expert B2B SEO content writer for MegaLLM.
Format: Min 1200 words, H2 headings (## syntax), FAQ section, schema hints as HTML comments,
internal link placeholders [[link: ...]]. Write for technical CTO audience.
Additional quality rules: include architecture-level trade-offs, quantified examples where
possible, and actionable implementation guidance; avoid keyword stuffing and generic filler.
Rewrite emphasis: improve structure and credibility without changing thesis.
Add stronger transitions from insight to implementation decisions.
Ensure each major section provides at least one concrete takeaway.
Keep language practical, precise, and non-promotional.""",

    "newsletter": """You are writing a B2B newsletter digest for MegaLLM.
Audience: CTOs at AI startups in UK, Singapore, Australia, New Zealand.
Structure: 1) Hook Insight, 2) Infra Takeaway, 3) MegaLLM Angle. Single CTA at end. 300–400 words.
Additional quality rules: make the infra takeaway concrete and numeric where possible; keep tone
concise, technical, and decision-focused; avoid generic commentary.
Rewrite emphasis: tighten signal density and keep each section distinct.
Prefer one strong metric over multiple weak facts.
Ensure CTA is specific enough to act on this week.
Maintain plain text and strict structure.""",
}


def _rewrite_post(
    post: Dict[str, Any],
    critique: str,
    rewriter: LLMClient,
    config: WF3Config,
) -> str:
    """
    Node 10 — rewrite using critique as explicit instructions.
    Returns rewritten content string.
    """
    platform = post.get("platform", "linkedin")
    # Fall back to linkedin prompt for unknown platforms
    system = _REWRITE_SYSTEM_BY_PLATFORM.get(platform, _REWRITE_SYSTEM_BY_PLATFORM["linkedin"])

    user_prompt = f"""--- ORIGINAL POST ---
{post.get('content', '')}
--- END ORIGINAL POST ---

QC CRITIQUE:
{critique}

INSTRUCTION: Rewrite this post specifically fixing every point raised in the critique above.
Do NOT change the core angle, the MegaLLM tie-in, or the target keyword.
Keep the same platform format rules."""

    return rewriter.complete(
        system,
        user_prompt,
        temperature=config.rewrite_temperature,
        max_tokens=config.rewrite_max_tokens,
    )


# ---------------------------------------------------------------------------
# MongoDB helpers
# ---------------------------------------------------------------------------

def _to_oid(id_val: Any) -> Any:
    """Convert string to ObjectId if possible, otherwise return as-is."""
    try:
        return ObjectId(str(id_val))
    except Exception:
        return id_val


def fetch_draft_posts(post_ids: List[str], collection: Collection) -> List[Dict]:
    """
    Node 2 — SELECT * FROM generated_posts WHERE id = ANY(post_ids) AND status = 'draft'
    """
    oids = [_to_oid(pid) for pid in post_ids]
    posts = list(collection.find({"_id": {"$in": oids}, "status": "draft"}))
    logger.info(f"Fetched {len(posts)} draft posts out of {len(post_ids)} requested.")
    return posts


def _approve_post(
    post_id: Any,
    scores: Dict[str, Any],
    collection: Collection,
) -> None:
    """Node 7 — UPDATE status = 'approved' with score fields."""
    collection.update_one(
        {"_id": _to_oid(post_id)},
        {
            "$set": {
                "status": "approved",
                "virality_score": scores.get("weighted_total"),
                "hook_score": scores.get("hook_strength"),
                "specificity_score": scores.get("specificity"),
                "icp_score": scores.get("icp_resonance"),
                "brand_fit_score": scores.get("brand_fit"),
                "engagement_score": scores.get("engagement_signal"),
                "qc_critique": scores.get("critique"),
                "qc_attempts": scores.get("_attempt", 1),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    logger.info(f"Approved post {post_id} (score {scores.get('weighted_total')})")


def _shelve_post(
    post_id: Any,
    scores: Dict[str, Any],
    attempts: int,
    collection: Collection,
) -> None:
    """Node 13 — UPDATE status = 'shelved'."""
    collection.update_one(
        {"_id": _to_oid(post_id)},
        {
            "$set": {
                "status": "shelved",
                "virality_score": scores.get("weighted_total"),
                "qc_critique": scores.get("critique"),
                "qc_attempts": attempts,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    logger.info(f"Shelved post {post_id} (score {scores.get('weighted_total')}, attempts {attempts})")


def _save_rewrite(
    post_id: Any,
    new_content: str,
    collection: Collection,
) -> None:
    """Persist rewritten content back to generated_posts before re-scoring."""
    collection.update_one(
        {"_id": _to_oid(post_id)},
        {
            "$set": {
                "content": new_content,
                "rewritten_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


# ---------------------------------------------------------------------------
# WF4 trigger + Slack alert
# ---------------------------------------------------------------------------

def _trigger_wf4(post_id: str, wf4_url: str) -> None:
    """Node 8 — POST approved post ID to WF4."""
    if not wf4_url:
        logger.info(f"WF4_WEBHOOK_URL not set — skipping WF4 trigger for {post_id}.")
        return
    try:
        resp = requests.post(wf4_url, json={"post_id": post_id}, timeout=30)
        resp.raise_for_status()
        logger.info(f"WF4 triggered for post {post_id} (HTTP {resp.status_code}).")
    except requests.exceptions.RequestException as exc:
        logger.error(f"WF4 trigger failed for {post_id}: {exc}")


def _slack_shelve_alert(
    post: Dict[str, Any],
    scores: Dict[str, Any],
    attempts: int,
    slack_url: str,
    channel: str,
) -> None:
    """Node 14 — Slack notification for shelved posts."""
    if not slack_url:
        logger.info(f"SLACK_WEBHOOK_URL not set — skipping Slack alert for post {post.get('_id')}.")
        return

    content_preview = (post.get("content", "") or "")[:300]
    if len(post.get("content", "")) > 300:
        content_preview += "…"

    message = {
        "channel": channel,
        "text": f":no_entry: *Post shelved after QC* — manual review needed",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚫 Post Shelved — Manual Review Required"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Post ID:*\n`{post.get('_id')}`"},
                    {"type": "mrkdwn", "text": f"*Platform:*\n{post.get('platform', 'unknown').upper()}  Variant {post.get('variant', '?')}"},
                    {"type": "mrkdwn", "text": f"*Final Score:*\n{scores.get('weighted_total', '?')}/10"},
                    {"type": "mrkdwn", "text": f"*QC Attempts:*\n{attempts}/{2}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Critique:*\n_{scores.get('critique', 'N/A')}_",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Content preview:*\n```{content_preview}```",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"  Hook: {scores.get('hook_strength', '?')}/10  |"
                        f"  Specificity: {scores.get('specificity', '?')}/10  |"
                        f"  ICP: {scores.get('icp_resonance', '?')}/10  |"
                        f"  Brand fit: {scores.get('brand_fit', '?')}/10  |"
                        f"  Engagement: {scores.get('engagement_signal', '?')}/10"
                    ),
                },
            },
        ],
    }

    try:
        resp = requests.post(slack_url, json=message, timeout=15)
        resp.raise_for_status()
        logger.info(f"Slack alert sent for shelved post {post.get('_id')}.")
    except requests.exceptions.RequestException as exc:
        logger.error(f"Slack alert failed: {exc}")


# ---------------------------------------------------------------------------
# Per-post QC logic  (nodes 4–14)
# ---------------------------------------------------------------------------

def _process_one_post(
    post: Dict[str, Any],
    scorer: LLMClient,
    rewriter: LLMClient,
    config: WF3Config,
    collection: Collection,
) -> Dict[str, Any]:
    """
    Full QC decision tree for a single post.

    Returns a result summary dict for the pipeline log.
    """
    post_id = post["_id"]
    platform = post.get("platform", "unknown")
    logger.info(f"QC: scoring post {post_id} ({platform} variant {post.get('variant', '?')})")

    # ── Attempt 1: score original ─────────────────────────────────────────
    scores = _score_post(post, scorer, config)
    scores["_attempt"] = 1
    total = scores["weighted_total"]
    logger.info(f"  Attempt 1 score: {total}")

    # Node 6 — gate ≥ 7.0
    if total >= config.approve_threshold:
        _approve_post(post_id, scores, collection)
        _trigger_wf4(str(post_id), config.wf4_webhook_url)
        return {"post_id": str(post_id), "outcome": "approved", "score": total, "attempts": 1}

    # Node 9 — gate ≥ 5.0 (rewrite?) vs immediate shelve
    if total < config.rewrite_threshold:
        _shelve_post(post_id, scores, attempts=1, collection=collection)
        _slack_shelve_alert(post, scores, attempts=1,
                            slack_url=config.slack_webhook_url, channel=config.slack_channel)
        return {"post_id": str(post_id), "outcome": "shelved_no_rewrite", "score": total, "attempts": 1}

    # ── Attempt 2: rewrite then re-score ─────────────────────────────────
    logger.info(f"  Score {total} triggers rewrite (threshold {config.rewrite_threshold}–{config.approve_threshold}).")
    critique = scores.get("critique", "Improve hook strength and specificity.")

    rewritten_content = _rewrite_post(post, critique, rewriter, config)
    _save_rewrite(post_id, rewritten_content, collection)

    # Update local dict so re-scorer sees new content
    rewritten_post = dict(post)
    rewritten_post["content"] = rewritten_content

    # Node 11 — re-score
    rescores = _score_post(rewritten_post, scorer, config)
    rescores["_attempt"] = 2
    new_total = rescores["weighted_total"]
    logger.info(f"  Attempt 2 score: {new_total}")

    # Node 12 — re-score gate ≥ 7.0
    if new_total >= config.approve_threshold:
        _approve_post(post_id, rescores, collection)
        _trigger_wf4(str(post_id), config.wf4_webhook_url)
        return {"post_id": str(post_id), "outcome": "approved_after_rewrite", "score": new_total, "attempts": 2}

    # Still below 7.0 after rewrite → shelve
    _shelve_post(post_id, rescores, attempts=config.max_qc_attempts, collection=collection)
    _slack_shelve_alert(rewritten_post, rescores, attempts=config.max_qc_attempts,
                        slack_url=config.slack_webhook_url, channel=config.slack_channel)
    return {"post_id": str(post_id), "outcome": "shelved_after_rewrite", "score": new_total, "attempts": 2}


# ---------------------------------------------------------------------------
# Main pipeline class
# ---------------------------------------------------------------------------

class QualityControlPipeline:
    def __init__(self, config: WF3Config):
        self.config = config
        # Node 4/11 scorer — cheaper model
        self.scorer = LLMClient(
            config.scorer_api_key,
            config.scorer_base_url,
            config.scorer_model,
        )
        # Node 10 rewriter — consistent voice model
        self.rewriter = LLMClient(
            config.rewrite_api_key,
            config.rewrite_base_url,
            config.rewrite_model,
        )
        self.mongo_client = MongoClient(config.mongodb_uri)
        self.db = self.mongo_client[config.mongodb_db]
        self.generated_posts: Collection = self.db.generated_posts

    def run(self, post_ids: List[str]) -> Dict[str, Any]:
        """
        Full WF3 execution for a batch of post IDs.
        Node 3 — processes one by one (batch size 1) to avoid context bleed.
        Returns summary statistics.
        """
        logger.info(f"WF3 started for {len(post_ids)} post IDs.")

        # Node 2 — fetch drafts only
        posts = fetch_draft_posts(post_ids, self.generated_posts)
        if not posts:
            logger.info("No draft posts found — nothing to QC.")
            return {"total": 0, "approved": 0, "shelved": 0, "errors": 0, "results": []}

        results = []
        approved = shelved = errors = 0

        # Node 3 — sequential, one post at a time
        for post in posts:
            try:
                result = _process_one_post(
                    post,
                    self.scorer,
                    self.rewriter,
                    self.config,
                    self.generated_posts,
                )
                results.append(result)
                if "approved" in result["outcome"]:
                    approved += 1
                else:
                    shelved += 1
            except LLMQuotaExceededError:
                logger.error("LLM quota exceeded — stopping WF3 early.")
                errors += 1
                break
            except Exception as exc:
                logger.error(f"Unexpected error on post {post.get('_id')}: {exc}")
                errors += 1

        summary = {
            "total": len(posts),
            "approved": approved,
            "shelved": shelved,
            "errors": errors,
            "results": results,
        }

        logger.info("=" * 50)
        logger.info("WF3 Summary:")
        logger.info(f"  Total posts:  {len(posts)}")
        logger.info(f"  Approved:     {approved}")
        logger.info(f"  Shelved:      {shelved}")
        logger.info(f"  Errors:       {errors}")
        logger.info("=" * 50)

        return summary

    def close(self) -> None:
        self.mongo_client.close()


# ---------------------------------------------------------------------------
# Webhook server
# ---------------------------------------------------------------------------

def run_webhook_server(config: WF3Config, host: str = "0.0.0.0", port: int = 5003) -> None:
    """
    Minimal HTTP server: POST /qc with body {"post_ids": ["id1", "id2", ...]}
    """

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            logger.info(f"HTTP {self.address_string()} - {fmt % args}")

        def do_POST(self):
            if self.path != "/qc":
                self.send_response(404)
                self.end_headers()
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            try:
                data = json.loads(body)
                post_ids = data.get("post_ids", [])
                if not isinstance(post_ids, list) or not post_ids:
                    raise ValueError("post_ids must be a non-empty array")
            except (json.JSONDecodeError, ValueError) as exc:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode())
                return

            pipeline = QualityControlPipeline(config)
            try:
                summary = pipeline.run(post_ids)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(summary).encode())
            except Exception as exc:
                logger.exception(f"WF3 pipeline error: {exc}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode())
            finally:
                pipeline.close()

    server = HTTPServer((host, port), Handler)
    logger.info(f"WF3 QC webhook server listening on http://{host}:{port}/qc")
    logger.info('Send: POST /qc  body: {"post_ids": ["id1", "id2"]}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down WF3 server.")
        server.shutdown()


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def _build_config() -> WF3Config:
    bootstrap_env(__file__)

    api_key = resolve_api_key()
    if not api_key:
        logger.error("MEGALLM_API_KEY or OPENAI_API_KEY not set.")
        raise SystemExit(1)

    cfg = WF3Config()
    cfg.scorer_api_key = api_key
    # Rewrite model may use same key unless a separate one is configured
    cfg.rewrite_api_key = os.getenv("REWRITE_API_KEY", api_key)
    return cfg


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    cfg = _build_config()

    # --server [--host=...] [--port=...]
    if args and args[0] == "--server":
        host, port = "0.0.0.0", 5003
        for arg in args[1:]:
            if arg.startswith("--port="):
                port = int(arg.split("=", 1)[1])
            elif arg.startswith("--host="):
                host = arg.split("=", 1)[1]
        run_webhook_server(cfg, host=host, port=port)

    # --posts id1 id2 id3 ...
    elif len(args) >= 2 and args[0] == "--posts":
        post_ids = args[1:]
        pipeline = QualityControlPipeline(cfg)
        try:
            summary = pipeline.run(post_ids)
            print(json.dumps(summary, indent=2, default=str))
        finally:
            pipeline.close()

    else:
        script_name = os.path.basename(__file__)
        print(
            "Usage:\n"
            f"  python {script_name} --posts <id1> <id2> ...\n"
            f"  python {script_name} --server [--host=0.0.0.0] [--port=5003]\n"
        )
        raise SystemExit(0)
