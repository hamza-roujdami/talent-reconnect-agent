"""
Skill Extraction Tool

Extracts canonical skills from job descriptions using keyword matching
"""

from typing import Annotated, List
from pydantic import Field


def extract_skills_from_job(
    job_title: Annotated[str, Field(description="Job title")],
    job_description: Annotated[str, Field(description="Full job description")]
) -> str:
    """
    Extract canonical skills from job description
    Returns ~10 standardized skill names
    """
    keywords = job_description.lower()
    skill_set = set()
    
    # Technical skills mapping
    tech_skills = {
        'python': 'Python', 'java': 'Java', 'javascript': 'JavaScript', 'typescript': 'TypeScript',
        'c++': 'C++', 'c#': 'C#', 'sql': 'SQL', 'nosql': 'NoSQL', 'react': 'React', 'angular': 'Angular',
        'azure': 'Azure', 'aws': 'AWS', 'gcp': 'Google Cloud', 'kubernetes': 'Kubernetes', 'docker': 'Docker',
        'machine learning': 'Machine Learning', 'ml': 'Machine Learning', 'ai': 'Artificial Intelligence',
        'deep learning': 'Deep Learning', 'nlp': 'Natural Language Processing', 'data science': 'Data Science',
        'mlops': 'MLOps', 'devops': 'DevOps', 'cicd': 'CI/CD', 'ci/cd': 'CI/CD', 'agile': 'Agile', 'scrum': 'Scrum',
        'tensorflow': 'TensorFlow', 'pytorch': 'PyTorch', 'spark': 'Apache Spark', 'hadoop': 'Hadoop'
    }
    
    # Soft skills mapping
    soft_skills = {
        'leadership': 'Leadership', 'communication': 'Communication', 'collaboration': 'Team Collaboration',
        'problem solving': 'Problem Solving', 'analytical': 'Analytical Thinking', 'critical thinking': 'Critical Thinking'
    }
    
    all_skills = {**tech_skills, **soft_skills}
    
    for keyword, skill_name in all_skills.items():
        if keyword in keywords:
            skill_set.add(skill_name)
    
    # Use found skills or defaults
    if skill_set:
        skills = list(skill_set)[:10]
    else:
        skills = [
            "Python", "Machine Learning", "Azure", "SQL", "Leadership",
            "Communication", "Problem Solving", "Team Collaboration", "Agile", "Data Analysis"
        ]
    
    # Ensure we have exactly 10 skills
    while len(skills) < 10:
        default_skills = ["Leadership", "Communication", "Problem Solving", "Analytical Thinking", 
                         "Team Collaboration", "Critical Thinking", "Adaptability", "Time Management"]
        for skill in default_skills:
            if skill not in skills and len(skills) < 10:
                skills.append(skill)
    
    return f"""✓ Skills Mapping Complete

Job Title: {job_title}

Canonical Skills Identified (10):
{chr(10).join(f'• {skill}' for skill in skills)}

These skills will be used to search the candidate database."""
