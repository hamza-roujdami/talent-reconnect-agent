#!/usr/bin/env python3
"""
02 - Generate & Push Data to Azure AI Search

Generates synthetic resume data using Faker and pushes directly to Azure AI Search.
This is a complete end-to-end script for populating the index.

Usage:
    python 02-push-data.py                      # Generate & upload 1,000 resumes
    python 02-push-data.py --count 100000       # Generate & upload 100k resumes
    python 02-push-data.py --count 100000 --dry-run  # Generate only, don't upload
"""

import os
import sys
import random
import argparse
from typing import List, Dict
from dotenv import load_dotenv

# Check for Faker
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
KEY = os.environ.get("AZURE_SEARCH_KEY")
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX", "resumes")

# Initialize Faker with multiple locales
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
    # UAE Tech
    ("Careem", 10), ("Noon", 8), ("Talabat", 8), ("Dubizzle", 6),
    ("Emirates NBD", 8), ("FAB", 8), ("ADNOC", 6), ("Etisalat", 6),
    ("Du", 5), ("Bayanat", 4), ("G42", 6), ("Presight AI", 4),
    # Global Tech
    ("Google", 5), ("Microsoft", 5), ("Amazon", 5), ("Meta", 3),
    ("Apple", 3), ("Netflix", 2), ("Uber", 3), ("Airbnb", 2),
    # Consulting
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
    
    # Always add programming
    skills.update(random.sample(SKILLS_POOL["programming"], 3))
    
    # Category-specific
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
        # Mix of everything
        skills.update(random.sample(SKILLS_POOL["cloud"], 2))
        skills.update(random.sample(SKILLS_POOL["backend"], 2))
    
    return list(skills)[:random.randint(6, 12)]


def generate_resume(resume_id: int) -> Dict:
    """Generate a single resume document."""
    category = random.choice(list(JOB_TITLES.keys()))
    job_title = random.choice(JOB_TITLES[category])
    
    name = fake.name()
    email = f"{name.lower().replace(' ', '.').replace(\"'\", '')}@{random.choice(['gmail.com', 'outlook.com', 'yahoo.com'])}"
    
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
    
    # Summary template
    summary = f"Experienced {job_title} with {experience} years building scalable systems. " \
              f"Strong background in {', '.join(skills[:4])}. " \
              f"Passionate about solving complex problems."
    
    return {
        "id": f"gen-{resume_id:06d}",
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
        "open_to_opportunities": random.random() < 0.4,  # 40% open
    }


def generate_resumes(count: int) -> List[Dict]:
    """Generate multiple resumes with progress."""
    resumes = []
    for i in range(1, count + 1):
        resumes.append(generate_resume(i))
        if i % 10000 == 0:
            print(f"  Generated {i:,} / {count:,}...")
    return resumes


# =============================================================================
# UPLOAD TO AZURE AI SEARCH
# =============================================================================

def upload_to_search(resumes: List[Dict], batch_size: int = 1000):
    """Upload resumes to Azure AI Search in batches."""
    if not ENDPOINT or not KEY:
        print("❌ Missing AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_KEY")
        sys.exit(1)
    
    client = SearchClient(
        endpoint=ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(KEY),
    )
    
    print(f"\n📤 Uploading {len(resumes):,} resumes to {INDEX_NAME}...")
    
    uploaded = 0
    failed = 0
    
    for i in range(0, len(resumes), batch_size):
        batch = resumes[i:i + batch_size]
        try:
            result = client.upload_documents(documents=batch)
            batch_success = sum(1 for r in result if r.succeeded)
            batch_failed = len(batch) - batch_success
            uploaded += batch_success
            failed += batch_failed
            print(f"  Batch {i // batch_size + 1}: {batch_success} ✅, {batch_failed} ❌")
        except Exception as e:
            print(f"  Batch {i // batch_size + 1} failed: {e}")
            failed += len(batch)
    
    client.close()
    print(f"\n✅ Done! Uploaded: {uploaded:,}, Failed: {failed:,}")
    return uploaded, failed


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate & push resumes to Azure AI Search")
    parser.add_argument("--count", "-c", type=int, default=1000, help="Number of resumes (default: 1000)")
    parser.add_argument("--dry-run", action="store_true", help="Generate only, don't upload")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    args = parser.parse_args()
    
    if args.seed:
        random.seed(args.seed)
        Faker.seed(args.seed)
    
    print(f"🎲 Generating {args.count:,} synthetic resumes...")
    resumes = generate_resumes(args.count)
    print(f"✅ Generated {len(resumes):,} resumes")
    
    # Show sample
    print("\n📋 Sample resume:")
    sample = resumes[0]
    print(f"  Name: {sample['name']}")
    print(f"  Title: {sample['current_title']} @ {sample['current_company']}")
    print(f"  Skills: {', '.join(sample['skills'][:5])}...")
    print(f"  Location: {sample['location']}")
    
    if args.dry_run:
        print("\n⏸️  Dry run - skipping upload")
    else:
        upload_to_search(resumes)


if __name__ == "__main__":
    main()
