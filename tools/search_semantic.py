"""
Search Tool - Semantic Search (Neural Reranking)

Uses Azure SDK (same as MAF's AzureAISearchContextProvider).
Hybrid search with semantic understanding (+15-25% relevance).

Best for: Natural language queries, finding conceptually similar candidates.

How it works:
1. BM25 keyword search (baseline)
2. Neural reranker scores results by MEANING
3. Understands: "ML" = "Machine Learning", "UAE" ≈ "Dubai"
"""

import os
from typing import Annotated, List
from pydantic import Field
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType

from tools.scoring import compute_match_score


def search_resumes_semantic(
    skills: Annotated[List[str], Field(description="Required skills to search for (e.g., ['Python', 'FastAPI', 'Azure'])")],
    job_title: Annotated[str, Field(description="Target job title (e.g., 'Senior Python Developer')")] = "",
    min_experience: Annotated[int, Field(description="Minimum years of experience required")] = 0,
    location: Annotated[str, Field(description="Preferred location (e.g., 'UAE', 'Remote')")] = "",
    top_k: Annotated[int, Field(description="Number of candidates to return")] = 5,
    job_description: Annotated[str, Field(description="Full job description text for semantic matching. When provided, enables deeper semantic understanding of role requirements, responsibilities, and culture fit.")] = "",
) -> str:
    """
    Search resumes using semantic ranking.
    Uses Azure SDK - same as MAF's AzureAISearchContextProvider.
    Understands meaning and context - finds candidates even without exact keyword matches.
    
    When job_description is provided, uses it as the primary search text for richer
    semantic matching (understands context like "fast-paced startup", "collaborate with ML team").
    """
    
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    key = os.environ.get("AZURE_SEARCH_KEY")
    index = os.environ.get("AZURE_SEARCH_INDEX", "resumes")
    
    if not endpoint or not key:
        return "❌ Azure AI Search not configured. Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY."
    
    # Build search query - prefer full JD for richer semantic matching
    if job_description:
        # Use full JD - Azure AI Search semantic ranker understands context
        # Truncate to ~500 words to stay within query limits
        query = job_description[:2000]
    else:
        # Fallback to structured parameters
        search_terms = []
        if job_title:
            search_terms.append(job_title)
        search_terms.extend(skills)
        if location:
            search_terms.append(location)
        query = " ".join(search_terms)
    
    # Build filter for experience
    filter_expr = None
    if min_experience > 0:
        filter_expr = f"experience_years ge {min_experience}"
    
    # Create Azure SDK client (same as MAF uses)
    client = SearchClient(
        endpoint=endpoint,
        index_name=index,
        credential=AzureKeyCredential(key),
    )
    
    facets = {}  # Initialize for facet summary
    
    try:
        # Semantic search with enhancements:
        # - scoring_profile: boost title matches (2x), skills (1.5x), experience
        # - facets: get aggregated counts by location/title
        # - Synonyms are applied automatically (synonym map linked to index)
        results = client.search(
            search_text=query,
            top=top_k,
            select=["name", "current_title", "skills", "experience_years", "location", "email", "summary", "current_company", "phone", "education", "certifications", "open_to_opportunities"],
            filter=filter_expr,
            query_type=QueryType.SEMANTIC,  # Enable semantic ranking
            semantic_configuration_name="default",  # Must match index config
            scoring_profile="talent-boost",  # Custom relevance boosting
            facets=["location,count:5", "current_title,count:5"],  # Aggregated counts
        )
        
        results_list = list(results)
        
        # Extract facet counts for summary
        facets = results.get_facets() or {}
    except Exception as e:
        return f"❌ Search failed: {str(e)}"
    finally:
        client.close()
    
    if not results_list:
        return f"No candidates found matching: {query}. Try broadening your search criteria."
    
    # Compute match scores for each candidate
    scored_candidates = []
    for r in results_list:
        candidate = dict(r)
        match = compute_match_score(
            candidate=candidate,
            required_skills=skills,
            job_title=job_title,
            min_experience=min_experience,
            preferred_location=location,
        )
        scored_candidates.append((candidate, match))
    
    # Sort by match score (highest first)
    scored_candidates.sort(key=lambda x: x[1]["overall"], reverse=True)
    
    # Store for later drill-down
    store_search_results(scored_candidates)
    
    # Count by priority
    hot_count = sum(1 for _, m in scored_candidates if m["overall"] >= 85)
    warm_count = sum(1 for _, m in scored_candidates if 70 <= m["overall"] < 85)
    
    # Visual match bar helper
    def match_bar(score: int) -> str:
        filled = int(score / 10)
        return "🟩" * filled + "⬜" * (10 - filled)
    
    # Generate smart "why this match" explanation - considers full candidate profile
    def why_match(match: dict, candidate: dict) -> str:
        bd = match["breakdown"]
        overall = match["overall"]
        highlights = []
        
        # Experience years
        exp_years = candidate.get("experience_years", 0)
        exp_fit = bd["experience"].get("fit", "")
        
        # Smart highlights based on candidate profile
        candidate_skills = candidate.get("skills", [])
        candidate_title = candidate.get("current_title", "")
        candidate_company = candidate.get("current_company", "")
        candidate_summary = candidate.get("summary", "")
        
        # 1. Experience highlight (always useful)
        if exp_fit == "ideal":
            highlights.append(f"✨ {exp_years}yr ideal fit")
        elif exp_fit == "experienced":
            highlights.append(f"📈 {exp_years}yr seasoned")
        elif exp_fit == "over_qualified":
            highlights.append(f"⚡ {exp_years}yr senior")
        elif exp_years > 0:
            highlights.append(f"💼 {exp_years}yr exp")
        
        # 2. Strong skill match or notable skills (skip company - it's in Candidate column)
        matched_skills = bd["skills"]["matched"]
        bonus_skills = bd["skills"].get("bonus_skills", [])
        
        # Check for in-demand skills
        hot_skills = ["kubernetes", "aws", "azure", "gcp", "python", "golang", "rust", 
                     "pytorch", "tensorflow", "llm", "genai", "ml", "ai", "docker", 
                     "terraform", "react", "typescript"]
        
        notable_skills = []
        for skill in candidate_skills[:10]:
            if skill.lower() in hot_skills and skill not in matched_skills:
                notable_skills.append(skill)
        
        if notable_skills:
            highlights.append(f"🔥 +{', '.join(notable_skills[:2])}")
        elif bonus_skills:
            highlights.append(f"➕ {', '.join(bonus_skills[:2])}")
        
        # 3. Location insight
        loc_type = bd["location"].get("match_type", "")
        if loc_type == "exact":
            highlights.append("📍 Local")
        elif loc_type == "regional":
            highlights.append("🌍 Regional")
        
        # 4. Title relevance
        if bd["title"].get("relevance") == "excellent":
            highlights.append("✓ Title match")
        
        # Return top 3 most useful highlights
        return " · ".join(highlights[:3]) if highlights else "Good match"
    
    # Format results - Rich TA-friendly table
    output = f"""## 🔍 Found {len(scored_candidates)} Candidates

| # | Candidate | Fit | Highlights | Key Skills | Actions |
|:---:|-----------|:---:|------------|------------|:-------:|
"""
    
    # Add summary row for each candidate
    for i, (candidate, match) in enumerate(scored_candidates, 1):
        name = candidate.get("name", "Unknown")
        title = candidate.get("current_title", "N/A")
        loc = candidate.get("location", "N/A")
        exp = candidate.get("experience_years", 0)
        company = candidate.get("current_company", "N/A")
        email = candidate.get("email", "")
        linkedin = candidate.get("linkedin", "")
        overall = match["overall"]
        bd = match["breakdown"]
        
        # Priority emoji
        if overall >= 85:
            priority = "🔥"
        elif overall >= 70:
            priority = "🌡️"
        else:
            priority = "❄️"
        
        # Top skills - show candidate's actual skills (matched first, then bonus)
        matched_skills = bd["skills"]["matched"]
        bonus_skills = bd["skills"].get("bonus_skills", [])
        candidate_skills = candidate.get("skills", [])
        
        # Combine: matched skills + bonus skills + other notable skills
        top_skills = matched_skills[:2]  # First 2 matched
        if bonus_skills:
            top_skills.extend(bonus_skills[:1])  # Add 1 bonus skill
        # Fill remaining from candidate's skills (not already listed)
        for skill in candidate_skills:
            if skill not in top_skills and len(top_skills) < 4:
                top_skills.append(skill)
        skills_str = ", ".join(top_skills[:4]) if top_skills else "—"
        
        # Experience fit label
        exp_fit = bd["experience"].get("fit", "")
        fit_emoji = {
            "ideal": "✨",
            "experienced": "📈", 
            "over_qualified": "⚡",
            "slightly_under": "📊",
            "stretch": "🎯",
            "under_qualified": "⚠️",
        }.get(exp_fit, "")
        
        # Build rich candidate cell with name, title, company, location, experience
        candidate_cell = f"**{name}** {priority}<br>*{title}* @ {company}<br>📍 {loc} · {exp} yrs"
        
        # Match cell with visual bar
        match_cell = f"**{overall}%**<br>`{match_bar(overall)}`"
        
        # Why this match
        why_cell = why_match(match, candidate)
        
        # Links cell - LinkedIn search (searches for name + company)
        import urllib.parse
        linkedin_query = urllib.parse.quote(f"{name} {company}")
        linkedin_url = f"https://www.linkedin.com/search/results/people/?keywords={linkedin_query}"
        
        # Open to opportunities badge
        open_badge = "🟢" if candidate.get("open_to_opportunities", False) else ""
        
        # Build rich candidate cell - clean and scannable
        candidate_cell = f"**{name}** {open_badge}<br>*{title}*<br>🏢 {company}<br>📍 {loc}"
        
        # Fit cell - score + visual indicator
        if overall >= 90:
            fit_label = f"🔥 **{overall}%**"
        elif overall >= 80:
            fit_label = f"✅ **{overall}%**"
        elif overall >= 70:
            fit_label = f"👍 **{overall}%**"
        else:
            fit_label = f"🔍 {overall}%"
        
        # Highlights - smart insights
        highlights_cell = why_match(match, candidate)
        
        # Key skills - show what matters
        skills_cell = ", ".join(top_skills[:4]) if top_skills else "—"
        
        # Actions - quick actions
        actions_cell = f"[🔗 LinkedIn]({linkedin_url})"
        
        output += f"| {i} | {candidate_cell} | {fit_label} | {highlights_cell} | {skills_cell} | {actions_cell} |\n"
    
    # Quick stats
    output += f"\n---\n**📊 Results:** {hot_count} 🔥 excellent, {warm_count} ✅ good matches\n"
    
    # Facet summary (distribution breakdown)
    if facets:
        facet_parts = []
        if "location" in facets:
            top_locs = [f"{f['value'].split(',')[0]} ({f['count']})" for f in facets["location"][:3]]
            facet_parts.append(f"📍 {', '.join(top_locs)}")
        if "current_title" in facets:
            top_titles = [f"{f['value']} ({f['count']})" for f in facets["current_title"][:2]]
            facet_parts.append(f"💼 {', '.join(top_titles)}")
        if facet_parts:
            output += f"\n**🔍 Pool breakdown:** {' · '.join(facet_parts)}\n"
    
    # Quick actions - cleaner format
    output += """
**Quick Actions:**
- **1** → See detailed profiles
- **2** → Refine search
- **3 + #** → Contact candidate (e.g., "contact 1")
- **4** → Compare all skills
"""
    
    return output


def _format_skill_matrix(scored_candidates: list, required_skills: list) -> str:
    """Create a skill comparison matrix across all candidates."""
    if not required_skills or len(scored_candidates) < 2:
        return ""
    
    # Collect all bonus skills from candidates
    all_bonus_skills = set()
    for candidate, match in scored_candidates[:5]:
        bonus = match["breakdown"]["skills"].get("bonus_skills", [])
        all_bonus_skills.update(bonus)
    
    # Combine required and top bonus skills
    all_skills = list(required_skills[:6])  # Up to 6 required
    bonus_to_show = [s for s in all_bonus_skills if s.lower() not in [r.lower() for r in all_skills]][:4]  # Up to 4 bonus
    all_skills.extend(bonus_to_show)
    
    # Build header row with candidate names
    names = [c[0].get("name", "?").split()[0] for c in scored_candidates[:5]]  # First name only, max 5
    header = "| Skill | " + " | ".join(names) + " |"
    separator = "|-------|" + "|".join(["---"] * len(names)) + "|"
    
    rows = []
    for skill in all_skills:
        is_bonus = skill in bonus_to_show
        label = f"**{skill}**" if not is_bonus else f"*{skill}* ⭐"
        row = f"| {label} |"
        for candidate, match in scored_candidates[:5]:
            candidate_skills = [s.lower() for s in candidate.get("skills", [])]
            matched_skills = [s.lower() for s in match["breakdown"]["skills"]["matched"]]
            bonus_skills = [s.lower() for s in match["breakdown"]["skills"].get("bonus_skills", [])]
            
            skill_lower = skill.lower()
            has_skill = (
                skill_lower in matched_skills or 
                skill_lower in bonus_skills or
                any(skill_lower in s for s in candidate_skills)
            )
            if has_skill:
                row += " ✅ |"
            else:
                row += " ❌ |"
        rows.append(row)
    
    matrix = f"""
## 📋 Skill Comparison Matrix

{header}
{separator}
{chr(10).join(rows)}

*⭐ = Bonus skills (not required but valuable)*
"""
    return matrix


def _format_candidate_with_score(i: int, r: dict, match: dict) -> str:
    """Format a single candidate result with match score."""
    name = r.get("name", "Unknown")
    title = r.get("current_title", "N/A")
    company = r.get("current_company", "N/A")
    exp = r.get("experience_years", "N/A")
    loc = r.get("location", "N/A")
    email = r.get("email", "N/A")
    phone = r.get("phone", "")
    education = r.get("education", "")
    certifications = r.get("certifications", [])
    open_to_opps = r.get("open_to_opportunities", False)
    summary = r.get("summary", "")
    
    overall = match["overall"]
    bd = match["breakdown"]
    
    # Visual progress bars
    def make_bar(score: int) -> str:
        filled = int(score / 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty
    
    # Skills details
    matched_skills = bd["skills"]["matched"]
    missing_skills = bd["skills"]["missing"]
    bonus_skills = bd["skills"].get("bonus_skills", [])
    
    # Experience fit label
    exp_fit = bd["experience"].get("fit", "")
    exp_label = {
        "ideal": "✨ Ideal fit",
        "experienced": "📈 Very experienced", 
        "over_qualified": "⚡ Over-qualified",
        "slightly_under": "📊 Close fit",
        "stretch": "🎯 Stretch candidate",
        "under_qualified": "⚠️ Under-qualified",
    }.get(exp_fit, "")
    
    # Title relevance
    title_rel = bd["title"].get("relevance", "")
    seniority_match = bd["title"].get("seniority_match", "")
    
    # Priority emoji
    if overall >= 85:
        priority = "🔥 HOT"
    elif overall >= 70:
        priority = "🌡️ WARM"
    else:
        priority = "❄️ NURTURE"
    
    # Format certifications
    certs_str = ", ".join(certifications) if certifications else "—"
    
    # Open to opportunities status
    availability = "🟢 Open to opportunities" if open_to_opps else "⚪ Not actively looking"
    
    # Build output with a single comprehensive table
    output = f"""
### {i}. {name} — **{overall}% Match** {priority}

> {summary if summary else 'No summary available.'}

| | |
|---|---|
| **📍 Location** | {loc} |
| **💼 Experience** | {exp} years {exp_label} |
| **🏢 Company** | {company} |
| **👔 Role** | {title} |
| **📧 Email** | {email} |
| **📱 Phone** | {phone if phone else '—'} |
| **🎓 Education** | {education if education else '—'} |
| **📜 Certifications** | {certs_str} |
| **💼 Status** | {availability} |

| Score Breakdown | | |
|---|---|---|
| Skills (40%) | {bd['skills']['score']}% | `{make_bar(bd['skills']['score'])}` |
| Experience (25%) | {bd['experience']['score']}% | `{make_bar(bd['experience']['score'])}` |
| Location (20%) | {bd['location']['score']}% | `{make_bar(bd['location']['score'])}` |
| Title (15%) | {bd['title']['score']}% | `{make_bar(bd['title']['score'])}` |

| ✅ Matched Skills | ⚠️ Skills to Verify | ⭐ Bonus Skills |
|---|---|---|
| {', '.join(matched_skills) if matched_skills else '—'} | {', '.join(missing_skills) if missing_skills else '—'} | {', '.join(bonus_skills) if bonus_skills else '—'} |

---
"""
    return output


# Store last search results for drill-down
_last_search_results = []


def get_candidate_details(
    candidate_numbers: Annotated[List[int], Field(description="List of candidate numbers to show details for (e.g., [1, 2, 3] or [1] for single candidate)")],
) -> str:
    """
    Show detailed profiles for specific candidates from the last search.
    Call this when user asks to see details, score breakdown, or more info about candidates.
    """
    global _last_search_results
    
    if not _last_search_results:
        return "❌ No search results available. Please search for candidates first."
    
    output = "## 📋 Detailed Candidate Profiles\n"
    
    for num in candidate_numbers:
        if num < 1 or num > len(_last_search_results):
            output += f"\n⚠️ Candidate #{num} not found. Valid range: 1-{len(_last_search_results)}\n"
            continue
        
        candidate, match = _last_search_results[num - 1]
        output += _format_candidate_with_score(num, candidate, match)
    
    return output


def show_skill_comparison() -> str:
    """
    Show a skill comparison matrix for candidates from the last search.
    Call this when user asks to compare skills across candidates.
    """
    global _last_search_results
    
    if not _last_search_results:
        return "❌ No search results available. Please search for candidates first."
    
    # Get required skills from first candidate's match breakdown
    if _last_search_results:
        first_match = _last_search_results[0][1]
        required_skills = first_match["breakdown"]["skills"]["matched"] + first_match["breakdown"]["skills"]["missing"]
    else:
        required_skills = []
    
    output = _format_skill_matrix(_last_search_results, required_skills)
    
    return output
    
    return output


def store_search_results(scored_candidates: list):
    """Store search results for later drill-down."""
    global _last_search_results
    _last_search_results = scored_candidates
