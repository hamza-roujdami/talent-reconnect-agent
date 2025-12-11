"""
Search Tool - Resume Search and Matching

Searches resumes and generates comparison table.
"""

from typing import Annotated, List
from pydantic import Field
from data import MOCK_RESUMES


def search_and_match_resumes(
    job_title: Annotated[str, Field(description="The job title to search for")],
    required_skills: Annotated[List[str], Field(description="List of required functional skills")],
    min_experience: Annotated[int, Field(description="Minimum years of experience required")],
    screening_questions: Annotated[List[str], Field(description="Resume mining/screening questions")],
    location_preference: Annotated[str, Field(description="Preferred location")] = "UAE"
) -> str:
    """
    Search resumes and generate a comparison table matching candidates against JD requirements.
    Returns top 5 candidates in a markdown table format.
    """
    
    # Score and filter candidates
    scored_candidates = []
    
    for resume in MOCK_RESUMES:
        # Skip candidates not open to opportunities
        if not resume.get("open_to_opportunities", True):
            continue
            
        # Calculate match score
        score = 0
        
        # Experience match (0-25 points)
        if resume["experience_years"] >= min_experience:
            score += 25
        elif resume["experience_years"] >= min_experience - 2:
            score += 15
            
        # Skills match (0-35 points)
        candidate_skills = [s.lower() for s in resume["skills"]]
        matched_skills = sum(1 for skill in required_skills if skill.lower() in candidate_skills or any(skill.lower() in cs for cs in candidate_skills))
        skill_score = min(35, (matched_skills / max(len(required_skills), 1)) * 35)
        score += skill_score
        
        # Location match (0-15 points)
        if location_preference.lower() in resume["location"].lower():
            score += 15
        elif "remote" in resume["location"].lower():
            score += 10
            
        # Certifications (0-10 points)
        if resume["certifications"]:
            score += min(10, len(resume["certifications"]) * 5)
            
        # GenAI/Modern experience (0-15 points)
        if resume.get("genai_experience"):
            score += 10
        if resume.get("maf_experience"):
            score += 5
            
        scored_candidates.append({
            "resume": resume,
            "score": score,
            "matched_skills": matched_skills
        })
    
    # Sort by score and get top 5
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = scored_candidates[:5]
    
    if not top_candidates:
        return "No matching candidates found. Try adjusting the requirements."
    
    # Build the comparison table
    table = f"""
## 🎯 Top {len(top_candidates)} Matching Candidates for {job_title}

| Criteria | """
    
    # Header row with candidate names
    for i, c in enumerate(top_candidates, 1):
        table += f"**Candidate {i}**<br>{c['resume']['name']} | "
    table = table.rstrip(" | ") + "\n"
    
    # Separator
    table += "|" + "---|" * (len(top_candidates) + 1) + "\n"
    
    # Required Qualifications section
    table += "| **REQUIRED QUALIFICATIONS** |" + " |" * len(top_candidates) + "\n"
    
    # Experience
    table += "| Years of Experience |"
    for c in top_candidates:
        years = c['resume']['experience_years']
        status = "✅" if years >= min_experience else "⚠️"
        table += f" {status} {years} years |"
    table += "\n"
    
    # Education
    table += "| Education |"
    for c in top_candidates:
        table += f" {c['resume']['education']} |"
    table += "\n"
    
    # Location
    table += "| Location |"
    for c in top_candidates:
        loc = c['resume']['location']
        status = "✅" if location_preference.lower() in loc.lower() else "📍"
        table += f" {status} {loc} |"
    table += "\n"
    
    # Functional Skills section
    table += "| **FUNCTIONAL SKILLS** |" + " |" * len(top_candidates) + "\n"
    
    for i, skill in enumerate(required_skills[:6], 1):
        table += f"| F{i}: {skill} |"
        for c in top_candidates:
            candidate_skills = [s.lower() for s in c['resume']['skills']]
            has_skill = skill.lower() in candidate_skills or any(skill.lower() in cs for cs in candidate_skills)
            table += f" {'✅' if has_skill else '❌'} |"
        table += "\n"
    
    # Preferred Qualifications
    table += "| **PREFERRED QUALIFICATIONS** |" + " |" * len(top_candidates) + "\n"
    
    # Certifications
    table += "| P1: Relevant Certifications |"
    for c in top_candidates:
        certs = c['resume']['certifications']
        if certs:
            table += f" ✅ {len(certs)} cert(s) |"
        else:
            table += " ❌ None |"
    table += "\n"
    
    # Advanced degree
    table += "| P2: Advanced Degree (MS/PhD) |"
    for c in top_candidates:
        edu = c['resume']['education'].lower()
        has_advanced = "master" in edu or "phd" in edu or "ph.d" in edu
        table += f" {'✅' if has_advanced else '❌'} |"
    table += "\n"
    
    # GenAI experience
    table += "| P3: GenAI/LLM Experience |"
    for c in top_candidates:
        table += f" {'✅' if c['resume'].get('genai_experience') else '❌'} |"
    table += "\n"
    
    # Historical Feedback
    table += "| **HISTORICAL FEEDBACK** |" + " |" * len(top_candidates) + "\n"
    table += "| ATS/CRM History |"
    for c in top_candidates:
        feedback = c['resume'].get('historical_feedback', 'No record')
        if len(feedback) > 40:
            feedback = feedback[:37] + "..."
        table += f" {feedback} |"
    table += "\n"
    
    # Current Whereabouts
    table += "| **CURRENT WHEREABOUTS** |" + " |" * len(top_candidates) + "\n"
    
    table += "| Current Company |"
    for c in top_candidates:
        table += f" {c['resume']['current_company']} |"
    table += "\n"
    
    table += "| Current Title |"
    for c in top_candidates:
        table += f" {c['resume']['current_title']} |"
    table += "\n"
    
    # Screening Questions
    table += "| **SCREENING QUESTIONS** |" + " |" * len(top_candidates) + "\n"
    
    screening_checks = [
        ("Q1: ML Production Deploy", "ml_production"),
        ("Q2: GenAI/LLM Apps", "genai_experience"),
        ("Q3: E2E ML Pipelines", "e2e_pipelines"),
        ("Q4: Azure AI Experience", "azure_experience"),
    ]
    
    for label, key in screening_checks:
        table += f"| {label} |"
        for c in top_candidates:
            table += f" {'✅' if c['resume'].get(key) else '❌'} |"
        table += "\n"
    
    # Match Score Summary
    table += "| **OVERALL MATCH SCORE** |"
    for c in top_candidates:
        score = int(c['score'])
        if score >= 80:
            emoji = "🌟"
        elif score >= 60:
            emoji = "✅"
        else:
            emoji = "⚠️"
        table += f" {emoji} **{score}%** |"
    table += "\n"
    
    # Summary
    table += f"""
---
### 📊 Summary
- **Total Candidates Screened:** {len(MOCK_RESUMES)}
- **Matching Candidates:** {len(scored_candidates)}
- **Top Candidates Shown:** {len(top_candidates)}

**Ready to send outreach emails to these candidates?** Just say "send emails to X candidates" (e.g., "send emails to top 3 candidates").
"""
    
    return table
