"""
Candidate Match Scoring

Computes a structured match score based on:
- Skills Match (40%): % of required skills found + depth bonus
- Experience (25%): How well experience years match requirements (with over-qualification penalty)
- Location (20%): Exact, regional, or different
- Title (15%): Job title relevance with seniority matching

Returns both overall % and breakdown for transparency.

Enhanced for better differentiation between candidates.
"""

from typing import List, Dict, Any
import re


# Seniority levels for title matching
SENIORITY_LEVELS = {
    "intern": 0,
    "junior": 1,
    "associate": 2,
    "mid": 3,
    "senior": 4,
    "staff": 5,
    "principal": 6,
    "lead": 5,
    "manager": 5,
    "director": 7,
    "vp": 8,
    "head": 7,
    "chief": 9,
    "cto": 9,
    "ceo": 10,
}

# Location groupings for regional matching
LOCATION_REGIONS = {
    "uae": ["uae", "dubai", "abu dhabi", "sharjah", "ajman", "fujairah", "ras al khaimah", "umm al quwain"],
    "gulf": ["saudi arabia", "ksa", "qatar", "bahrain", "kuwait", "oman"],
    "mena": ["egypt", "jordan", "lebanon", "morocco", "tunisia"],
    "us_west": ["san francisco", "sf", "bay area", "los angeles", "la", "seattle", "portland", "california", "ca"],
    "us_east": ["new york", "ny", "nyc", "boston", "dc", "washington", "miami", "atlanta"],
    "europe": ["london", "uk", "berlin", "germany", "paris", "france", "amsterdam", "netherlands"],
    "asia": ["singapore", "hong kong", "tokyo", "japan", "india", "bangalore", "mumbai"],
    "remote": ["remote", "anywhere", "distributed", "work from home", "wfh"],
}


def compute_match_score(
    candidate: Dict[str, Any],
    required_skills: List[str],
    job_title: str = "",
    min_experience: int = 0,
    preferred_location: str = "",
) -> Dict[str, Any]:
    """
    Compute structured match score for a candidate.
    
    Returns:
        {
            "overall": 85,  # Overall match %
            "breakdown": {
                "skills": {"score": 90, "matched": ["Python", "AWS"], "missing": ["Kubernetes"]},
                "experience": {"score": 100, "candidate": 7, "required": 5},
                "location": {"score": 75, "match_type": "regional"},
                "title": {"score": 80, "relevance": "similar"}
            }
        }
    """
    
    # --- Skills Match (40% weight) ---
    skills_result = _score_skills(candidate.get("skills", []), required_skills)
    
    # --- Experience Match (25% weight) ---
    exp_result = _score_experience(candidate.get("experience_years", 0), min_experience)
    
    # --- Location Match (20% weight) ---
    loc_result = _score_location(candidate.get("location", ""), preferred_location)
    
    # --- Title Match (15% weight) ---
    title_result = _score_title(candidate.get("current_title", ""), job_title)
    
    # Weighted overall score
    overall = (
        skills_result["score"] * 0.40 +
        exp_result["score"] * 0.25 +
        loc_result["score"] * 0.20 +
        title_result["score"] * 0.15
    )
    
    return {
        "overall": round(overall),
        "breakdown": {
            "skills": skills_result,
            "experience": exp_result,
            "location": loc_result,
            "title": title_result,
        }
    }


def _score_skills(candidate_skills: List[str], required_skills: List[str]) -> Dict:
    """
    Score skills match with depth scoring.
    
    - Base score: % of required skills found
    - Bonus: Extra skills in same domain
    - Penalty: Critical skills missing get heavier weight
    """
    if not required_skills:
        return {"score": 100, "matched": [], "missing": [], "bonus_skills": []}
    
    # Normalize for comparison
    candidate_lower = [s.lower().strip() for s in (candidate_skills or [])]
    
    matched = []
    missing = []
    
    # Track skill importance (first skills listed are usually more important)
    for idx, skill in enumerate(required_skills):
        skill_lower = skill.lower().strip()
        # Check for exact or partial match
        found = any(
            skill_lower in cs or cs in skill_lower or
            _skill_synonyms_match(skill_lower, cs)
            for cs in candidate_lower
        )
        if found:
            matched.append(skill)
        else:
            missing.append(skill)
    
    # Base score with weighted importance (earlier skills worth more)
    if required_skills:
        weighted_score = 0
        total_weight = 0
        for idx, skill in enumerate(required_skills):
            # First skill is 1.5x weight, decreasing to 1.0x
            weight = max(1.0, 1.5 - (idx * 0.1))
            total_weight += weight
            if skill in matched:
                weighted_score += weight
        
        base_score = (weighted_score / total_weight) * 100
    else:
        base_score = 100
    
    # Bonus for extra relevant skills (max 10 bonus points)
    bonus_skills = []
    relevant_domains = _get_skill_domains(required_skills)
    for cs in candidate_lower:
        if cs not in [s.lower() for s in matched]:
            for domain in relevant_domains:
                if _skill_in_domain(cs, domain):
                    bonus_skills.append(cs)
                    break
    
    bonus = min(10, len(bonus_skills) * 2)  # 2 points per bonus skill, max 10
    
    final_score = min(100, base_score + bonus)
    
    return {
        "score": round(final_score),
        "matched": matched,
        "missing": missing,
        "bonus_skills": bonus_skills[:3],  # Show top 3
    }


def _get_skill_domains(skills: List[str]) -> List[str]:
    """Identify skill domains from a list of skills."""
    domains = set()
    skill_to_domain = {
        "python": "backend", "java": "backend", "go": "backend", "rust": "backend",
        "javascript": "frontend", "react": "frontend", "vue": "frontend", "angular": "frontend",
        "typescript": "frontend", "css": "frontend", "html": "frontend",
        "aws": "cloud", "azure": "cloud", "gcp": "cloud", "kubernetes": "cloud", "docker": "cloud",
        "ml": "data", "machine learning": "data", "tensorflow": "data", "pytorch": "data",
        "data science": "data", "pandas": "data", "spark": "data", "sql": "data",
        "devops": "infra", "ci/cd": "infra", "jenkins": "infra", "terraform": "infra",
    }
    
    for skill in skills:
        skill_lower = skill.lower()
        for key, domain in skill_to_domain.items():
            if key in skill_lower:
                domains.add(domain)
    
    return list(domains)


def _skill_in_domain(skill: str, domain: str) -> bool:
    """Check if a skill belongs to a domain."""
    domain_skills = {
        "backend": ["python", "java", "go", "rust", "c++", "c#", "node", "express", "fastapi", "django", "flask"],
        "frontend": ["javascript", "react", "vue", "angular", "svelte", "typescript", "css", "html", "tailwind"],
        "cloud": ["aws", "azure", "gcp", "kubernetes", "docker", "terraform", "cloudformation", "lambda", "ec2"],
        "data": ["ml", "machine learning", "tensorflow", "pytorch", "pandas", "numpy", "spark", "sql", "etl", "databricks"],
        "infra": ["devops", "ci/cd", "jenkins", "github actions", "ansible", "prometheus", "grafana"],
    }
    
    return any(ds in skill.lower() for ds in domain_skills.get(domain, []))


def _skill_synonyms_match(skill1: str, skill2: str) -> bool:
    """Check if two skills are synonyms."""
    synonyms = [
        {"python", "py"},
        {"javascript", "js", "typescript", "ts"},
        {"machine learning", "ml", "deep learning", "dl"},
        {"artificial intelligence", "ai"},
        {"amazon web services", "aws"},
        {"google cloud platform", "gcp", "google cloud"},
        {"microsoft azure", "azure"},
        {"kubernetes", "k8s"},
        {"docker", "containers", "containerization"},
        {"react", "reactjs", "react.js"},
        {"node", "nodejs", "node.js"},
        {"postgres", "postgresql"},
        {"mongo", "mongodb"},
    ]
    
    for group in synonyms:
        if skill1 in group and skill2 in group:
            return True
    return False


def _score_experience(candidate_years: int, required_years: int) -> Dict:
    """
    Score experience match with over-qualification consideration.
    
    - Sweet spot: Required to Required+3 years = 100%
    - Under-qualified: Graduated penalty
    - Over-qualified: Slight penalty (may not stay, expensive)
    """
    if required_years <= 0:
        return {"score": 100, "candidate": candidate_years, "required": required_years, "fit": "any"}
    
    diff = candidate_years - required_years
    
    if diff >= 0 and diff <= 3:
        # Sweet spot - meets requirements with room to grow
        score = 100
        fit = "ideal"
    elif diff > 3 and diff <= 5:
        # Slightly over-qualified
        score = 90
        fit = "experienced"
    elif diff > 5:
        # Significantly over-qualified - may get bored or cost more
        score = 75
        fit = "over_qualified"
    elif diff >= -1:
        # Within 1 year under - acceptable
        score = 85
        fit = "slightly_under"
    elif diff >= -2:
        # Within 2 years under - stretch candidate
        score = 70
        fit = "stretch"
    else:
        # Significant gap
        score = max(40, 50 + (diff * 5))  # Scaled penalty
        fit = "under_qualified"
    
    return {
        "score": round(score),
        "candidate": candidate_years,
        "required": required_years,
        "fit": fit,
    }


def _score_location(candidate_location: str, preferred_location: str) -> Dict:
    """Score location match."""
    if not preferred_location:
        return {"score": 100, "match_type": "any"}
    
    cand_lower = candidate_location.lower().strip()
    pref_lower = preferred_location.lower().strip()
    
    # Exact match
    if pref_lower in cand_lower or cand_lower in pref_lower:
        return {"score": 100, "match_type": "exact"}
    
    # Remote preference
    if pref_lower in ["remote", "anywhere"]:
        return {"score": 100, "match_type": "remote_ok"}
    
    # Check regional match
    cand_region = _get_region(cand_lower)
    pref_region = _get_region(pref_lower)
    
    if cand_region and pref_region and cand_region == pref_region:
        # UAE-wide matches treated as exact (same country, easy commute/relocation)
        if cand_region == "uae":
            return {"score": 100, "match_type": "same_country"}
        return {"score": 75, "match_type": "regional"}
    
    # Different location - might need relocation
    return {"score": 40, "match_type": "relocation_needed"}


def _get_region(location: str) -> str:
    """Get the region for a location."""
    for region, locations in LOCATION_REGIONS.items():
        if any(loc in location for loc in locations):
            return region
    return ""


def _score_title(candidate_title: str, target_title: str) -> Dict:
    """
    Score title relevance with seniority matching.
    
    - Role match: Does the job function align?
    - Seniority match: Is the level appropriate?
    """
    if not target_title:
        return {"score": 100, "relevance": "any", "seniority_match": True}
    
    cand_lower = candidate_title.lower()
    target_lower = target_title.lower()
    
    # Extract seniority from titles
    cand_seniority = _extract_seniority(cand_lower)
    target_seniority = _extract_seniority(target_lower)
    
    # Calculate seniority match score
    seniority_diff = abs(cand_seniority - target_seniority)
    if seniority_diff == 0:
        seniority_score = 100
        seniority_match = "exact"
    elif seniority_diff == 1:
        seniority_score = 85
        seniority_match = "close"
    elif seniority_diff == 2:
        seniority_score = 65
        seniority_match = "stretch"
    else:
        seniority_score = 40
        seniority_match = "mismatch"
    
    # Extract key terms (excluding seniority words)
    stopwords = {"senior", "junior", "lead", "staff", "principal", "the", "a", "an", "at", "in", 
                 "i", "ii", "iii", "1", "2", "3", "intern", "associate", "head", "director", "vp", "chief"}
    
    target_terms = set(target_lower.replace("-", " ").split()) - stopwords
    cand_terms = set(cand_lower.replace("-", " ").split()) - stopwords
    
    if not target_terms:
        return {"score": seniority_score, "relevance": "any", "seniority_match": seniority_match}
    
    # Calculate role overlap
    overlap = len(target_terms & cand_terms)
    total = len(target_terms)
    
    if overlap == total:
        role_score = 100
        role_match = "exact"
    elif overlap > 0:
        role_score = (overlap / total) * 100
        role_match = "partial"
    else:
        # Check for related roles
        related = _are_titles_related(cand_lower, target_lower)
        if related:
            role_score = 60
            role_match = "related"
        else:
            role_score = 25
            role_match = "different"
    
    # Combine role (60%) and seniority (40%) scores
    final_score = (role_score * 0.6) + (seniority_score * 0.4)
    
    # Determine overall relevance label
    if final_score >= 90:
        relevance = "excellent"
    elif final_score >= 75:
        relevance = "good"
    elif final_score >= 55:
        relevance = "partial"
    else:
        relevance = "weak"
    
    return {
        "score": round(final_score),
        "relevance": relevance,
        "role_match": role_match,
        "seniority_match": seniority_match,
    }


def _extract_seniority(title: str) -> int:
    """Extract seniority level from a title (0-10 scale)."""
    title_lower = title.lower()
    
    # Check for explicit seniority keywords
    for keyword, level in SENIORITY_LEVELS.items():
        if keyword in title_lower:
            return level
    
    # Default to mid-level if no indicator
    return 3


def _are_titles_related(title1: str, title2: str) -> bool:
    """Check if two job titles are in related fields."""
    related_groups = [
        {"engineer", "developer", "programmer", "coder"},
        {"data scientist", "data analyst", "ml engineer", "machine learning"},
        {"devops", "sre", "site reliability", "platform engineer", "infrastructure"},
        {"frontend", "front-end", "ui", "ux", "web developer"},
        {"backend", "back-end", "api", "server"},
        {"fullstack", "full-stack", "full stack"},
        {"manager", "lead", "director", "head"},
        {"product", "pm", "product owner"},
    ]
    
    for group in related_groups:
        in_group_1 = any(term in title1 for term in group)
        in_group_2 = any(term in title2 for term in group)
        if in_group_1 and in_group_2:
            return True
    return False


def format_match_breakdown(match: Dict[str, Any]) -> str:
    """Format match breakdown for display."""
    bd = match["breakdown"]
    
    lines = []
    
    # Skills
    sk = bd["skills"]
    if sk["matched"]:
        lines.append(f"✅ Skills: {', '.join(sk['matched'][:4])}")
    if sk["missing"]:
        lines.append(f"⚠️ Missing: {', '.join(sk['missing'][:3])}")
    
    # Experience
    ex = bd["experience"]
    if ex["score"] >= 85:
        lines.append(f"✅ Experience: {ex['candidate']} yrs (need {ex['required']}+)")
    else:
        lines.append(f"⚠️ Experience: {ex['candidate']} yrs (need {ex['required']}+)")
    
    # Location
    loc = bd["location"]
    if loc["match_type"] == "exact":
        lines.append("✅ Location: Exact match")
    elif loc["match_type"] == "regional":
        lines.append("✅ Location: Same region")
    elif loc["match_type"] == "relocation_needed":
        lines.append("⚠️ Location: Relocation needed")
    
    return "\n".join(lines)
