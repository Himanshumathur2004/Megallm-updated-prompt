#!/usr/bin/env python3
"""Run WF1 -> WF2 -> WF3 end-to-end with a single command."""

import argparse
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from bson import ObjectId

import wf1
import wf2
import wf3
from workflow_common import bootstrap_env


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _to_oid(id_val: str) -> Any:
    try:
        return ObjectId(id_val)
    except Exception:
        return id_val


def _fetch_pending_generation_insight_ids(db, limit: int) -> List[str]:
    query = {"status": "pending_generation"}
    cursor = db.content_insights.find(query, {"_id": 1}).sort("_id", 1)
    if limit > 0:
        cursor = cursor.limit(limit)
    return [str(doc["_id"]) for doc in cursor]


def _run_wf1() -> None:
    logger.info("[WF1] Starting content intelligence pipeline...")
    wf1.run_pipeline()
    logger.info("[WF1] Finished.")


def _post_status_counts(collection, post_ids: List[str]) -> Dict[str, int]:
    if not post_ids:
        return {"approved": 0, "shelved": 0, "draft": 0, "other": 0}

    oids = [_to_oid(pid) for pid in post_ids]
    approved = collection.count_documents({"_id": {"$in": oids}, "status": "approved"})
    shelved = collection.count_documents({"_id": {"$in": oids}, "status": "shelved"})
    draft = collection.count_documents({"_id": {"$in": oids}, "status": "draft"})
    other = max(len(post_ids) - approved - shelved - draft, 0)
    return {"approved": approved, "shelved": shelved, "draft": draft, "other": other}


def _run_wf2(limit: int) -> Dict[str, List[str]]:
    logger.info("[WF2] Looking for insights with status=pending_generation...")
    cfg = wf2._build_config()
    pipeline = wf2.ContentGenerationPipeline(cfg)
    generated_by_insight: Dict[str, List[str]] = {}

    try:
        insight_ids = _fetch_pending_generation_insight_ids(pipeline.db, limit)
        if not insight_ids:
            logger.info("[WF2] No pending_generation insights found.")
            return {}

        logger.info(f"[WF2] Found {len(insight_ids)} insights to process.")
        for insight_id in insight_ids:
            try:
                post_ids = pipeline.run(insight_id)
                generated_by_insight[insight_id] = post_ids

                # Persist generation metadata at insight level.
                pipeline.db.content_insights.update_one(
                    {"_id": _to_oid(insight_id)},
                    {
                        "$set": {
                            "generated_post_ids": post_ids,
                            "posts_generated_count": len(post_ids),
                            "post_generation_status": "generated",
                            "post_generation_completed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    },
                )
            except wf2.LLMQuotaExceededError:
                logger.error("[WF2] LLM quota exceeded. Stopping WF2 early.")
                break
            except Exception as exc:
                logger.error(f"[WF2] Failed insight {insight_id}: {exc}")

    finally:
        pipeline.close()

    total_posts = sum(len(v) for v in generated_by_insight.values())
    logger.info(f"[WF2] Generated {total_posts} posts across {len(generated_by_insight)} insights.")
    return generated_by_insight


def _run_wf3(generated_by_insight: Dict[str, List[str]], max_passes: int) -> Dict[str, Any]:
    if not generated_by_insight:
        logger.info("[WF3] No generated posts to quality-check.")
        return {"total": 0, "approved": 0, "shelved": 0, "errors": 0, "results": []}

    total_post_ids = [pid for ids in generated_by_insight.values() for pid in ids]
    logger.info(f"[WF3] Running quality control for {len(total_post_ids)} posts...")
    cfg = wf3._build_config()
    pipeline = wf3.QualityControlPipeline(cfg)

    merged = {"total": 0, "approved": 0, "shelved": 0, "errors": 0, "results": []}
    try:
        for insight_id, post_ids in generated_by_insight.items():
            remaining = list(post_ids)
            for _ in range(max_passes):
                if not remaining:
                    break
                summary = pipeline.run(remaining)
                merged["total"] += summary.get("total", 0)
                merged["approved"] += summary.get("approved", 0)
                merged["shelved"] += summary.get("shelved", 0)
                merged["errors"] += summary.get("errors", 0)
                merged["results"].extend(summary.get("results", []))

                counts = _post_status_counts(pipeline.generated_posts, post_ids)
                if counts["draft"] == 0:
                    break

                # Retry only those still in draft state.
                cursor = pipeline.generated_posts.find(
                    {"_id": {"$in": [_to_oid(pid) for pid in post_ids]}, "status": "draft"},
                    {"_id": 1},
                )
                remaining = [str(doc["_id"]) for doc in cursor]

            final_counts = _post_status_counts(pipeline.generated_posts, post_ids)
            qc_status = "scored" if final_counts["draft"] == 0 else "qc_incomplete"
            pipeline.db.content_insights.update_one(
                {"_id": _to_oid(insight_id)},
                {
                    "$set": {
                        "qc_status": qc_status,
                        "qc_approved_count": final_counts["approved"],
                        "qc_shelved_count": final_counts["shelved"],
                        "qc_pending_count": final_counts["draft"],
                        "qc_last_run_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )

        return merged
    finally:
        pipeline.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run WF1 -> WF2 -> WF3 in one command.",
    )
    parser.add_argument(
        "--skip-wf1",
        action="store_true",
        help="Skip WF1 and start from existing pending_generation insights.",
    )
    parser.add_argument(
        "--limit-insights",
        type=int,
        default=0,
        help="Maximum number of pending_generation insights for WF2 (0 = all).",
    )
    parser.add_argument(
        "--qc-max-passes",
        type=int,
        default=3,
        help="Max WF3 retry passes per insight to score remaining draft posts.",
    )
    args = parser.parse_args()

    bootstrap_env(__file__)

    if not args.skip_wf1:
        _run_wf1()

    generated_by_insight = _run_wf2(limit=args.limit_insights)
    summary = _run_wf3(generated_by_insight, max_passes=max(args.qc_max_passes, 1))
    total_posts = sum(len(v) for v in generated_by_insight.values())

    logger.info("=" * 60)
    logger.info("Automation Summary")
    logger.info(f"Insights processed in WF2: {len(generated_by_insight)}")
    logger.info(f"Posts sent to WF3: {total_posts}")
    logger.info(f"WF3 approved: {summary.get('approved', 0)}")
    logger.info(f"WF3 shelved: {summary.get('shelved', 0)}")
    logger.info(f"WF3 errors: {summary.get('errors', 0)}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
