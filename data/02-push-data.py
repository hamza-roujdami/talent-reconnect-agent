#!/usr/bin/env python3
"""
02 - Generate & Push Synthetic Resumes to Azure AI Search

Usage:
    python data/02-push-data.py                    # Generate & upload 1,000 resumes
    python data/02-push-data.py --count 10000      # Generate & upload 10k resumes
    python data/02-push-data.py --count 100 --dry-run  # Preview without uploading
"""

import os
import sys
import random
import argparse
from typing import List, Dict
from dotenv import load_dotenv

try:
    from faker import Faker
except ImportError:
    print("❌ Missing: pip install faker")
    sys.exit(1)

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
KEY = os.environ.get("AZURE_SEARCH_API_KEY") or os.environ.get("AZURE_SEARCH_KEY")
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "resumes")
CANDIDATE_BASE_URL = os.environ.get("CANDIDATE_BASE_URL", "https://recruiting.contoso.com/candidates")

fake = Faker(['en_US', 'en_GB', 'en_AU', 'en_IN', 'ar_AE'])

# =============================================================================
# DATA POOLS
# =============================================================================

JOB_TITLES = {
    "engineering": [
        "Software Engineer", "Senior Software Engineer", "Staff Engineer",
        "Principal Engineer", "Frontend Developer", "Backend Developer",
        "Full Stack Developer", "DevOps Engineer", "SRE Engineer",
        "Platform Engineer", "Cloud Engineer", "Infrastructure Engineer",
    ],
    "data": [
        "Data Scientist", "Senior Data Scientist", "ML Engineer",
        "Senior ML Engineer", "Data Engineer", "AI Engineer",
        "NLP Engineer", "Computer Vision Engineer", "MLOps Engineer",
    ],
    "product": [
        "Product Manager", "Senior Product Manager", "Technical Product Manager",
        "Product Owner", "Program Manager", "Project Manager",
    ],
    "management": [
        "Engineering Manager", "Director of Engineering", "VP of Engineering",
        "Tech Lead", "Team Lead", "Head of Data Science",
    ],
}

SKILLS_POOL = {
    "programming": ["Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "Scala"],
    "frontend": ["React", "Angular", "Vue.js", "Next.js", "HTML5", "CSS3", "Tailwind CSS", "Redux"],
    "backend": ["Node.js", "Django", "Flask", "FastAPI", "Spring Boot", ".NET Core", "Express.js"],
    "cloud": ["AWS", "Azure", "GCP", "Kubernetes", "Docker", "Terraform", "Jenkins", "ArgoCD"],
    "data": ["SQL", "PostgreSQL", "MongoDB", "Redis", "Kafka", "Spark", "Airflow", "Snowflake"],
    "ml": ["TensorFlow", "PyTorch", "Scikit-learn", "Keras", "Hugging Face", "LangChain", "MLflow", "Pandas"],
}

COMPANIES = [
    ("Careem", 10), ("Noon", 8), ("Talabat", 8), ("Dubizzle", 6),
    ("Emirates NBD", 8), ("FAB", 8), ("ADNOC", 6), ("Etisalat", 6),
    ("Du", 5), ("Bayanat", 4), ("G42", 6), ("Presight AI", 4),
    ("Google", 5), ("Microsoft", 5), ("Amazon", 5), ("Meta", 3),
    ("Apple", 3), ("Netflix", 2), ("Uber", 3), ("Airbnb", 2),
    ("McKinsey", 4), ("BCG", 3), ("Bain", 3), ("Deloitte", 5),
    ("Accenture", 5), ("PwC", 4), ("EY", 4), ("KPMG", 4),
]

LOCATIONS = [
    ("Dubai, UAE", 30), ("Abu Dhabi, UAE", 20), ("Sharjah, UAE", 5),
    ("Riyadh, Saudi Arabia", 10), ("Doha, Qatar", 5),
    ("London, UK", 5), ("Singapore", 5), ("Bangalore, India", 5),
    ("Remote", 10), ("New York, USA", 5),
]

EDUCATION = [
    "BSc Computer Science", "MSc Computer Science", "BSc Software Engineering",
    "MSc Machine Learning", "PhD Computer Science", "BSc Data Science",
    "MBA", "BSc Information Technology", "MSc AI",
]

UNIVERSITIES = [
    "MIT", "Stanford", "NYU Abu Dhabi", "American University of Sharjah",
    "KAUST", "NUS", "IIT Bombay", "IIT Delhi", "Cambridge", "Oxford",
    "Carnegie Mellon", "UC Berkeley", "ETH Zurich", "University of Michigan",
]

CERTIFICATIONS = [
    "AWS Solutions Architect", "AWS ML Specialty", "Azure Data Engineer",
    "Azure AI Engineer", "GCP Professional ML Engineer", "Kubernetes CKA",
    "Databricks ML Professional", "Google Cloud Professional Data Engineer",
]

# =============================================================================
# RESUME GENERATION
# =============================================================================

def weighted_choice(choices_with_weights):
    choices, weights = zip(*choices_with_weights)
    return random.choices(choices, weights=weights, k=1)[0]


def generate_skills(job_title: str) -> List[str]:
    """Generate relevant skills based on job title."""
    skills = set()
    job_lower = job_title.lower()
    
    skills.update(random.sample(SKILLS_POOL["programming"], 3))
    
    if any(x in job_lower for x in ["data", "ml", "ai", "machine learning"]):
        skills.update(random.sample(SKILLS_POOL["data"], 3))
        skills.update(random.sample(SKILLS_POOL["ml"], 4))
    elif any(x in job_lower for x in ["frontend", "ui"]):
        skills.update(random.sample(SKILLS_POOL["frontend"], 4))
    elif any(x in job_lower for x in ["backend", "api"]):
        skills.update(random.sample(SKILLS_POOL["backend"], 3))
    elif any(x in job_lower for x in ["devops", "sre", "cloud", "platform"]):
        skills.update(random.sample(SKILLS_POOL["cloud"], 5))
    elif any(x in job_lower for x in ["full stack"]):
        skills.update(random.sample(SKILLS_POOL["frontend"], 2))
        skills.update(random.sample(SKILLS_POOL["backend"], 2))
    else:
        skills.update(random.sample(SKILLS_POOL["cloud"], 2))
        skills.update(random.sample(SKILLS_POOL["backend"], 2))
    
    return list(skills)[:random.randint(6, 12)]


def generate_resume(resume_id: int) -> Dict:
    """Generate a single resume document."""
    category = random.choice(list(JOB_TITLES.keys()))
    job_title = random.choice(JOB_TITLES[category])
    
    name = fake.name()
    clean_name = name.lower().replace(' ', '.').replace("'", "")
    email = f"{clean_name}@{random.choice(['gmail.com', 'outlook.com', 'yahoo.com'])}"
    
    location = weighted_choice(LOCATIONS)
    company = weighted_choice(COMPANIES)
    experience = random.choices(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15],
        weights=[5, 10, 15, 15, 12, 10, 8, 6, 5, 4, 3, 2],
        k=1
    )[0]
    
    skills = generate_skills(job_title)
    education = f"{random.choice(EDUCATION)}, {random.choice(UNIVERSITIES)}"
    certs = random.sample(CERTIFICATIONS, k=random.randint(0, 3))
    
    summary = (
        f"Experienced {job_title} with {experience} years building scalable systems. "
        f"Strong background in {', '.join(skills[:4])}. "
        f"Passionate about solving complex problems."
    )
    
    doc_id = f"gen-{resume_id:06d}"
    
    return {
        "id": doc_id,
        "name": name,
        "email": email,
        "phone": f"+971{random.randint(500000000, 599999999)}",
        "current_title": job_title,
        "current_company": company,
        "experience_years": experience,
        "location": location,
        "skills": skills,
        "education": education,
        "certifications": certs,
        "summary": summary,
        "open_to_opportunities": random.random() < 0.4,
        "source_url": f"{CANDIDATE_BASE_URL}/{doc_id}",
    }


def generate_resumes(count: int) -> List[Dict]:
    """Generate multiple resumes."""
    resumes = []
    for i in range(1, count + 1):
        resumes.append(generate_resume(i))
        if i % 10000 == 0:
            print(f"  Generated {i:,} / {count:,}...")
    return resumes


# =============================================================================
# UPLOAD TO AZURE AI SEARCH
# =============================================================================

def upload_documents(documents: List[Dict], batch_size: int = 1000):
    """Upload documents to Azure AI Search in batches."""
    if not ENDPOINT or not KEY:
        print("❌ Missing AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_API_KEY")
        return
    
    client = SearchClient(
        endpoint=ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(KEY),
    )
    
    total = len(documents)
    success = 0
    failed = 0
    
    for i in range(0, total, batch_size):
        batch = documents[i:i + batch_size]
        try:
            results = client.upload_documents(batch)
            batch_success = sum(1 for r in results if r.succeeded)
            batch_failed = len(batch) - batch_success
            success += batch_success
            failed += batch_failed
            print(f"  Batch {i // batch_size + 1}: {batch_success} ✅, {batch_failed} ❌")
        except Exception as e:
            print(f"  Batch {i // batch_size + 1}: Error - {e}")
            failed += len(batch)
    
    client.close()
    print(f"\n✅ Done! Uploaded: {success:,}, Failed: {failed:,}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate and upload synthetic resumes")
    parser.add_argument("--count", type=int, default=1000, help="Number of resumes to generate")
    parser.add_argument("--dry-run", action="store_true", help="Generate only, don't upload")
    args = parser.parse_args()
    
    print(f"🎲 Generating {args.count:,} synthetic resumes...\n")
    resumes = generate_resumes(args.count)
    print(f"✅ Generated {len(resumes):,} resumes")
    
    # Show sample
    sample = resumes[0]
    print(f"\n📋 Sample resume:")
    print(f"  Name: {sample['name']}")
    print(f"  Title: {sample['current_title']} @ {sample['current_company']}")
    print(f"  Skills: {', '.join(sample['skills'][:5])}...")
    print(f"  Location: {sample['location']}")
    
    if args.dry_run:
        print("\n🔍 Dry run - skipping upload")
        return
    
    print(f"\n📤 Uploading {len(resumes):,} resumes to {INDEX_NAME}...")
    upload_documents(resumes)


if __name__ == "__main__":
    main()
