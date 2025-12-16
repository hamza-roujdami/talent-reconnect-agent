#!/usr/bin/env python3
"""
Generate Synthetic Resume Data for Talent Reconnect Agent

This script generates realistic resume data using Faker library,
matching the Azure AI Search index schema.

Usage:
    python scripts/generate_resumes.py                     # Generate 1000 resumes
    python scripts/generate_resumes.py --count 100000      # Generate 100k resumes
    python scripts/generate_resumes.py --output data.csv   # Output to CSV
    python scripts/generate_resumes.py --upload            # Generate and upload directly

Prerequisites:
    pip install faker pandas azure-search-documents python-dotenv
"""

import os
import sys
import json
import argparse
import random
from pathlib import Path
from typing import List, Dict

# Check dependencies
try:
    from faker import Faker
except ImportError:
    print("❌ Missing dependency: faker")
    print("   Run: pip install faker")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("❌ Missing dependency: pandas")
    print("   Run: pip install pandas")
    sys.exit(1)

# Initialize Faker with multiple locales for diversity
fake = Faker(['en_US', 'en_GB', 'en_AU', 'en_IN', 'ar_AE'])

# =============================================================================
# CUSTOMIZABLE DATA POOLS
# =============================================================================

# Job titles by category
JOB_TITLES = {
    "engineering": [
        "Software Engineer", "Senior Software Engineer", "Staff Engineer",
        "Principal Engineer", "Frontend Developer", "Backend Developer",
        "Full Stack Developer", "DevOps Engineer", "SRE Engineer",
        "Platform Engineer", "Cloud Engineer", "Infrastructure Engineer",
        "Mobile Developer", "iOS Developer", "Android Developer",
        "QA Engineer", "Test Automation Engineer", "Security Engineer",
    ],
    "data": [
        "Data Scientist", "Senior Data Scientist", "ML Engineer",
        "Machine Learning Engineer", "Data Engineer", "Data Analyst",
        "Business Intelligence Analyst", "AI Engineer", "NLP Engineer",
        "Computer Vision Engineer", "MLOps Engineer", "Research Scientist",
    ],
    "product": [
        "Product Manager", "Senior Product Manager", "Technical Product Manager",
        "Product Owner", "Program Manager", "Project Manager",
        "Scrum Master", "Agile Coach",
    ],
    "design": [
        "UX Designer", "UI Designer", "Product Designer", "UX Researcher",
        "Visual Designer", "Interaction Designer", "Design Lead",
    ],
    "management": [
        "Engineering Manager", "Director of Engineering", "VP of Engineering",
        "CTO", "Tech Lead", "Team Lead", "Head of Data Science",
    ],
}

# Skills by category
SKILLS_POOL = {
    "programming": [
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go",
        "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R",
    ],
    "frontend": [
        "React", "Angular", "Vue.js", "Next.js", "HTML5", "CSS3", "Sass",
        "Tailwind CSS", "Redux", "GraphQL", "Webpack", "Vite",
    ],
    "backend": [
        "Node.js", "Django", "Flask", "FastAPI", "Spring Boot", "Express.js",
        ".NET Core", "Ruby on Rails", "Laravel", "NestJS",
    ],
    "cloud": [
        "AWS", "Azure", "GCP", "Kubernetes", "Docker", "Terraform",
        "CloudFormation", "Ansible", "Jenkins", "GitHub Actions", "ArgoCD",
    ],
    "data": [
        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "Kafka", "Spark", "Hadoop", "Airflow", "dbt", "Snowflake",
    ],
    "ml": [
        "TensorFlow", "PyTorch", "Scikit-learn", "Keras", "OpenCV",
        "Hugging Face", "LangChain", "MLflow", "Pandas", "NumPy",
    ],
    "soft": [
        "Agile", "Scrum", "Leadership", "Communication", "Problem Solving",
        "Team Collaboration", "Mentoring", "Strategic Thinking",
    ],
}

# Locations (weighted towards UAE for this demo)
LOCATIONS = [
    # UAE (higher weight)
    ("Dubai, UAE", 25),
    ("Abu Dhabi, UAE", 15),
    ("Sharjah, UAE", 5),
    ("Ajman, UAE", 2),
    # GCC
    ("Riyadh, Saudi Arabia", 8),
    ("Jeddah, Saudi Arabia", 5),
    ("Doha, Qatar", 5),
    ("Manama, Bahrain", 3),
    ("Kuwait City, Kuwait", 3),
    ("Muscat, Oman", 3),
    # International
    ("London, UK", 5),
    ("New York, USA", 3),
    ("San Francisco, USA", 3),
    ("Singapore", 3),
    ("Bangalore, India", 5),
    ("Mumbai, India", 3),
    ("Remote", 4),
]

# Experience distribution (years: weight)
EXPERIENCE_WEIGHTS = {
    1: 10, 2: 15, 3: 20, 4: 15, 5: 12,
    6: 10, 7: 8, 8: 5, 9: 3, 10: 2,
    12: 2, 15: 1, 18: 1, 20: 1,
}


# =============================================================================
# RESUME GENERATION
# =============================================================================

def weighted_choice(choices_with_weights):
    """Select from a list of (choice, weight) tuples."""
    choices, weights = zip(*choices_with_weights)
    return random.choices(choices, weights=weights, k=1)[0]


def generate_skills(job_title: str, count: int = None) -> List[str]:
    """Generate relevant skills based on job title."""
    if count is None:
        count = random.randint(5, 12)
    
    skills = set()
    job_lower = job_title.lower()
    
    # Always add some programming skills
    skills.update(random.sample(SKILLS_POOL["programming"], min(3, count)))
    
    # Add category-specific skills
    if any(x in job_lower for x in ["frontend", "ui", "react", "angular"]):
        skills.update(random.sample(SKILLS_POOL["frontend"], min(4, count)))
    elif any(x in job_lower for x in ["backend", "server", "api"]):
        skills.update(random.sample(SKILLS_POOL["backend"], min(3, count)))
    elif any(x in job_lower for x in ["data", "ml", "machine learning", "ai"]):
        skills.update(random.sample(SKILLS_POOL["data"], min(3, count)))
        skills.update(random.sample(SKILLS_POOL["ml"], min(3, count)))
    elif any(x in job_lower for x in ["devops", "sre", "cloud", "platform"]):
        skills.update(random.sample(SKILLS_POOL["cloud"], min(4, count)))
    elif any(x in job_lower for x in ["full stack", "fullstack"]):
        skills.update(random.sample(SKILLS_POOL["frontend"], min(2, count)))
        skills.update(random.sample(SKILLS_POOL["backend"], min(2, count)))
    
    # Add some soft skills for senior roles
    if any(x in job_lower for x in ["senior", "lead", "manager", "director", "principal"]):
        skills.update(random.sample(SKILLS_POOL["soft"], min(2, count)))
    
    # Fill remaining with random skills
    all_skills = [s for pool in SKILLS_POOL.values() for s in pool]
    while len(skills) < count:
        skills.add(random.choice(all_skills))
    
    return list(skills)[:count]


def generate_resume(resume_id: int) -> Dict:
    """Generate a single resume."""
    # Pick job category and title
    category = random.choice(list(JOB_TITLES.keys()))
    job_title = random.choice(JOB_TITLES[category])
    
    # Generate name and email
    name = fake.name()
    email_name = name.lower().replace(" ", ".").replace("'", "")
    domains = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "company.com"]
    email = f"{email_name}@{random.choice(domains)}"
    
    # Location and experience
    location = weighted_choice(LOCATIONS)
    experience = weighted_choice(list(EXPERIENCE_WEIGHTS.items()))
    
    # Skills based on job title
    skills = generate_skills(job_title)
    
    return {
        "id": str(resume_id),
        "name": name,
        "email": email,
        "job_title": job_title,
        "experience_years": experience,
        "location": location,
        "skills": skills,
    }


def generate_resumes(count: int, show_progress: bool = True) -> List[Dict]:
    """Generate multiple resumes."""
    resumes = []
    
    for i in range(1, count + 1):
        resumes.append(generate_resume(i))
        
        if show_progress and i % 10000 == 0:
            print(f"  Generated {i:,} / {count:,} resumes...")
    
    return resumes


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def save_to_json(resumes: List[Dict], filepath: str):
    """Save resumes to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(resumes, f, indent=2)
    print(f"✅ Saved {len(resumes):,} resumes to {filepath}")


def save_to_csv(resumes: List[Dict], filepath: str):
    """Save resumes to CSV file."""
    df = pd.DataFrame(resumes)
    # Convert skills list to comma-separated string
    df['skills'] = df['skills'].apply(lambda x: ','.join(x))
    df.to_csv(filepath, index=False)
    print(f"✅ Saved {len(resumes):,} resumes to {filepath}")


def upload_to_search(resumes: List[Dict], batch_size: int = 1000):
    """Upload resumes directly to Azure AI Search."""
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError:
        print("❌ Missing dependency: azure-search-documents")
        print("   Run: pip install azure-search-documents")
        sys.exit(1)
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")
    index = os.getenv("AZURE_SEARCH_INDEX", "resumes")
    
    if not endpoint or not key:
        print("❌ Missing AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_KEY in .env")
        sys.exit(1)
    
    client = SearchClient(
        endpoint=endpoint,
        index_name=index,
        credential=AzureKeyCredential(key)
    )
    
    print(f"\n📤 Uploading {len(resumes):,} resumes to Azure AI Search...")
    
    for i in range(0, len(resumes), batch_size):
        batch = resumes[i:i + batch_size]
        result = client.upload_documents(documents=batch)
        
        success = sum(1 for r in result if r.succeeded)
        failed = len(batch) - success
        
        print(f"  Batch {i // batch_size + 1}: {success} uploaded, {failed} failed")
    
    print(f"✅ Upload complete!")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic resume data for Azure AI Search"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=1000,
        help="Number of resumes to generate (default: 1000)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="resumes.json",
        help="Output file path (supports .json or .csv)"
    )
    parser.add_argument(
        "--upload", "-u",
        action="store_true",
        help="Upload directly to Azure AI Search (requires .env credentials)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible generation"
    )
    
    args = parser.parse_args()
    
    # Set seed for reproducibility
    if args.seed:
        random.seed(args.seed)
        Faker.seed(args.seed)
        print(f"🎲 Using random seed: {args.seed}")
    
    print(f"\n🔧 Generating {args.count:,} synthetic resumes...")
    resumes = generate_resumes(args.count)
    
    # Sample output
    print(f"\n📋 Sample resume:")
    sample = resumes[0]
    print(f"   Name: {sample['name']}")
    print(f"   Email: {sample['email']}")
    print(f"   Title: {sample['job_title']}")
    print(f"   Experience: {sample['experience_years']} years")
    print(f"   Location: {sample['location']}")
    print(f"   Skills: {', '.join(sample['skills'][:5])}...")
    
    # Save to file
    output_path = Path(args.output)
    if output_path.suffix.lower() == ".csv":
        save_to_csv(resumes, args.output)
    else:
        save_to_json(resumes, args.output)
    
    # Upload if requested
    if args.upload:
        upload_to_search(resumes)
    
    print(f"\n🎉 Done!")


if __name__ == "__main__":
    main()
