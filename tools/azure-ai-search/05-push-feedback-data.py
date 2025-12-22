"""
Push sample feedback data to Azure AI Search.

This script:
1. Fetches some candidate IDs from the 'resumes' index
2. Creates sample interview feedback for those candidates
3. Uploads to the 'feedback' index

Usage:
    python 05-push-feedback-data.py
"""
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

load_dotenv()

# Azure AI Search configuration
SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_KEY"]
RESUMES_INDEX = "resumes"
FEEDBACK_INDEX = "feedback"

# Sample interviewers
INTERVIEWERS = [
    "Sarah Chen", "Ahmed Hassan", "Maria Garcia", "James Wilson",
    "Priya Patel", "Michael Johnson", "Fatima Al-Said", "David Kim"
]

# Sample feedback templates
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
    "",  # No concerns
]

NOTES_TEMPLATES = [
    "Would be a great fit for the team culture",
    "Recommend fast-tracking if available",
    "Consider for senior role in 6-12 months",
    "Good technical skills, needs mentorship on soft skills",
    "Strong candidate, competitive offer recommended",
    "",
]


def get_sample_candidates(n: int = 50) -> list[dict]:
    """Fetch random candidates from resumes index."""
    client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=RESUMES_INDEX,
        credential=AzureKeyCredential(SEARCH_KEY),
    )
    
    # Search for candidates with various skills
    results = client.search(
        search_text="*",
        select=["id", "name", "email", "current_title", "skills"],
        top=n,
    )
    
    candidates = []
    for r in results:
        candidates.append({
            "id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "title": r.get("current_title", "Unknown"),
            "skills": r.get("skills", []),
        })
    
    return candidates


def generate_feedback(candidate: dict, interview_num: int = 1) -> dict:
    """Generate a feedback record for a candidate."""
    
    # Random interview date in the past year
    days_ago = random.randint(30, 365)
    interview_date = datetime.now() - timedelta(days=days_ago)
    
    # Pick a skill to highlight
    skills = candidate.get("skills", ["Python"])
    highlight_skill = random.choice(skills) if skills else "technical"
    
    # Generate recommendation (weighted towards positive)
    rec_weights = [
        ("strong_hire", 15),
        ("hire", 40),
        ("maybe", 30),
        ("no_hire", 15),
    ]
    recommendation = random.choices(
        [r[0] for r in rec_weights],
        weights=[r[1] for r in rec_weights],
    )[0]
    
    # Score based on recommendation
    score_ranges = {
        "strong_hire": (85, 100),
        "hire": (70, 84),
        "maybe": (55, 69),
        "no_hire": (30, 54),
    }
    score_range = score_ranges[recommendation]
    score = random.randint(*score_range)
    
    # Generate text
    strengths = random.choice(STRENGTH_TEMPLATES).format(skill=highlight_skill)
    concerns = random.choice(CONCERN_TEMPLATES) if recommendation != "strong_hire" else ""
    notes = random.choice(NOTES_TEMPLATES)
    
    return {
        "id": f"{candidate['id']}_feedback_{interview_num}",
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
    }


def push_feedback_data(num_candidates: int = 50, feedback_per_candidate: int = 1):
    """Generate and push feedback data."""
    
    print(f"📥 Fetching {num_candidates} candidates from '{RESUMES_INDEX}'...")
    candidates = get_sample_candidates(num_candidates)
    print(f"   Found {len(candidates)} candidates")
    
    # Generate feedback records
    feedback_records = []
    for candidate in candidates:
        # Most candidates get 1 interview, some get 2
        num_interviews = 2 if random.random() < 0.2 else 1
        for i in range(num_interviews):
            feedback = generate_feedback(candidate, i + 1)
            feedback_records.append(feedback)
    
    print(f"\n📝 Generated {len(feedback_records)} feedback records")
    
    # Upload to feedback index
    client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=FEEDBACK_INDEX,
        credential=AzureKeyCredential(SEARCH_KEY),
    )
    
    # Upload in batches
    batch_size = 100
    for i in range(0, len(feedback_records), batch_size):
        batch = feedback_records[i:i + batch_size]
        result = client.upload_documents(documents=batch)
        succeeded = sum(1 for r in result if r.succeeded)
        print(f"   Uploaded batch {i//batch_size + 1}: {succeeded}/{len(batch)} succeeded")
    
    # Print summary
    print(f"\n✅ Done! Uploaded {len(feedback_records)} feedback records")
    
    # Show sample
    print("\n📊 Sample feedback:")
    for rec in feedback_records[:3]:
        print(f"   {rec['candidate_name']}: {rec['recommendation']} ({rec['score']}/100)")
        print(f"      Strengths: {rec['strengths'][:60]}...")
    
    # Show distribution
    print("\n📈 Recommendation distribution:")
    recs = [r["recommendation"] for r in feedback_records]
    for rec_type in ["strong_hire", "hire", "maybe", "no_hire"]:
        count = recs.count(rec_type)
        pct = count / len(recs) * 100
        print(f"   {rec_type}: {count} ({pct:.0f}%)")


if __name__ == "__main__":
    push_feedback_data(num_candidates=50)
