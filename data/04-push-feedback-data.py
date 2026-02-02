#!/usr/bin/env python3
"""
04 - Generate & Push Interview Feedback to Azure AI Search

Usage:
    python data/04-push-feedback-data.py                    # Generate feedback for all candidates
    python data/04-push-feedback-data.py --total-feedback 2000  # Generate specific amount
    python data/04-push-feedback-data.py --dry-run          # Preview without uploading
"""
import os
import random
import argparse
import math
from datetime import datetime, timedelta
from typing import List, Dict, Iterable
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ.get("AZURE_SEARCH_API_KEY") or os.environ.get("AZURE_SEARCH_KEY")
if not SEARCH_KEY:
    raise RuntimeError("Set AZURE_SEARCH_API_KEY before running this script.")

RESUMES_INDEX = os.environ.get("AZURE_SEARCH_INDEX_NAME", "resumes")
FEEDBACK_INDEX = os.environ.get("AZURE_FEEDBACK_INDEX_NAME", "feedback")
FEEDBACK_BASE_URL = os.environ.get("FEEDBACK_BASE_URL", "https://recruiting.contoso.com/feedback")

# =============================================================================
# DATA POOLS
# =============================================================================

INTERVIEWERS = [
    "Sarah Chen", "Ahmed Hassan", "Maria Garcia", "James Wilson",
    "Priya Patel", "Michael Johnson", "Fatima Al-Said", "David Kim",
]

STRENGTH_TEMPLATES = [
    "Strong {skill} expertise, excellent problem-solving abilities",
    "Deep knowledge of {skill}, great communicator and team player",
    "Impressive {skill} background, demonstrated leadership potential",
    "Solid {skill} skills, quick learner with growth mindset",
    "Expert-level {skill} knowledge, excellent system design capabilities",
]

CONCERN_TEMPLATES = [
    "Limited experience with production systems at scale",
    "Salary expectations slightly above budget",
    "Communication could be more concise",
    "Prefers remote-only, may need flexibility discussion",
    "Would benefit from more leadership experience",
    "",  # No concerns
    "",
]

NOTES_TEMPLATES = [
    "Would be a great fit for the team culture",
    "Recommend fast-tracking if available",
    "Consider for senior role in 6-12 months",
    "Good technical skills, needs mentorship on soft skills",
    "Strong candidate, competitive offer recommended",
    "",  # No notes
]

# =============================================================================
# CANDIDATE FETCHING
# =============================================================================

def fetch_candidates(max_candidates: int) -> List[Dict]:
    """Page through the resumes index to build a candidate pool."""
    if max_candidates <= 0:
        return []

    client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=RESUMES_INDEX,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    candidates = []
    page_size = 1000
    skip = 0
    max_skip = 100000  # Azure Search limit

    while len(candidates) < max_candidates and skip < max_skip:
        remaining = max_candidates - len(candidates)
        current_top = min(page_size, remaining)

        try:
            results = client.search(
                search_text="*",
                select=["id", "name", "email", "current_title", "skills"],
                top=current_top,
                skip=skip,
            )
        except HttpResponseError as exc:
            raise RuntimeError(f"Search failed: {exc}")

        page = list(results)
        if not page:
            break

        for record in page:
            candidates.append({
                "id": record["id"],
                "name": record.get("name", "Unknown"),
                "email": record.get("email", "noreply@example.com"),
                "title": record.get("current_title", "Unknown"),
                "skills": record.get("skills", []),
            })
            if len(candidates) >= max_candidates:
                break

        skip += len(page)

    return candidates


# =============================================================================
# FEEDBACK GENERATION
# =============================================================================

def generate_feedback(candidate: Dict, interview_num: int) -> Dict:
    """Create a single interview feedback document."""
    
    days_ago = random.randint(30, 365)
    interview_date = datetime.utcnow() - timedelta(days=days_ago)
    skills = candidate.get("skills") or ["Python"]
    highlight_skill = random.choice(skills)

    recommendation = random.choices(
        population=["strong_hire", "hire", "maybe", "no_hire"],
        weights=[15, 40, 30, 15],
    )[0]

    score_ranges = {
        "strong_hire": (85, 100),
        "hire": (70, 84),
        "maybe": (55, 69),
        "no_hire": (30, 54),
    }
    score = random.randint(*score_ranges[recommendation])

    strengths = random.choice(STRENGTH_TEMPLATES).format(skill=highlight_skill)
    concerns = random.choice(CONCERN_TEMPLATES) if recommendation != "strong_hire" else ""
    notes = random.choice(NOTES_TEMPLATES)

    feedback_id = f"{candidate['id']}_feedback_{interview_num}"
    
    return {
        "id": feedback_id,
        "candidate_id": candidate["id"],
        "candidate_email": candidate["email"],
        "candidate_name": candidate["name"],
        "interview_date": interview_date.isoformat() + "Z",
        "interviewer": random.choice(INTERVIEWERS),
        "role": candidate["title"],
        "strengths": strengths,
        "concerns": concerns,
        "recommendation": recommendation,
        "score": score,
        "notes": notes,
        "source_url": f"{FEEDBACK_BASE_URL}/{feedback_id}",
    }


def build_feedback_records(
    candidates: Iterable[Dict],
    total_feedback: int,
    extra_interview_prob: float,
) -> List[Dict]:
    """Generate feedback ensuring at least one interview per candidate."""

    candidate_list = list(candidates)
    if not candidate_list:
        return []

    interview_counts = {candidate["id"]: 0 for candidate in candidate_list}
    records = []

    # First pass: one interview per candidate
    for candidate in candidate_list:
        interview_counts[candidate["id"]] = 1
        records.append(generate_feedback(candidate, 1))

    if len(records) >= total_feedback:
        return records[:total_feedback]

    # Second pass: add extra interviews
    remaining = total_feedback - len(records)
    extra_candidates = [c for c in candidate_list if random.random() < extra_interview_prob]
    if not extra_candidates:
        extra_candidates = candidate_list[:]
    random.shuffle(extra_candidates)

    idx = 0
    while remaining > 0:
        candidate = extra_candidates[idx % len(extra_candidates)]
        idx += 1
        interview_counts[candidate["id"]] += 1
        records.append(generate_feedback(candidate, interview_counts[candidate["id"]]))
        remaining -= 1

        if idx % len(extra_candidates) == 0:
            random.shuffle(extra_candidates)

    return records


# =============================================================================
# UPLOAD
# =============================================================================

def upload_feedback(records: List[Dict], batch_size: int = 1000):
    """Upload feedback documents to Azure AI Search."""
    client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=FEEDBACK_INDEX,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        result = client.upload_documents(documents=batch)
        succeeded = sum(1 for r in result if r.succeeded)
        print(f"  Batch {i // batch_size + 1}: {succeeded}/{len(batch)} succeeded")


def summarize(records: List[Dict]):
    """Print summary of generated feedback."""
    print(f"\n✅ Generated {len(records):,} feedback documents")
    
    print("\n📋 Sample entries:")
    for rec in records[:3]:
        print(f"  {rec['candidate_name']} → {rec['recommendation']} ({rec['score']}/100)")
        print(f"    Strengths: {rec['strengths'][:60]}...")

    distribution = {"strong_hire": 0, "hire": 0, "maybe": 0, "no_hire": 0}
    for rec in records:
        distribution[rec["recommendation"]] += 1

    print("\n📊 Recommendation distribution:")
    for key, value in distribution.items():
        pct = (value / len(records)) * 100 if records else 0
        print(f"  {key:<12} {value:>6} ({pct:4.1f}%)")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate and upload interview feedback")
    parser.add_argument("--total-feedback", type=int, default=0, 
                       help="Target feedback count (0 = one per candidate)")
    parser.add_argument("--candidate-pool", type=int, default=100000,
                       help="Max candidates to fetch from resumes index")
    parser.add_argument("--extra-interview-prob", type=float, default=0.2,
                       help="Probability of extra interview per candidate")
    parser.add_argument("--batch-size", type=int, default=1000,
                       help="Upload batch size")
    parser.add_argument("--dry-run", action="store_true",
                       help="Generate without uploading")
    args = parser.parse_args()

    print(f"📥 Fetching candidates from '{RESUMES_INDEX}'...")
    candidates = fetch_candidates(args.candidate_pool)
    if not candidates:
        raise SystemExit("No candidates found in resumes index.")
    print(f"  Retrieved {len(candidates):,} candidates")

    # Set total_feedback to candidate count if not specified
    total = args.total_feedback if args.total_feedback > 0 else len(candidates)
    
    print(f"\n🎲 Generating {total:,} feedback records...")
    records = build_feedback_records(
        candidates=candidates,
        total_feedback=total,
        extra_interview_prob=args.extra_interview_prob,
    )

    summarize(records)

    if args.dry_run:
        print("\n🔍 Dry run - skipping upload")
        return

    print(f"\n📤 Uploading to '{FEEDBACK_INDEX}'...")
    upload_feedback(records, batch_size=args.batch_size)
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
