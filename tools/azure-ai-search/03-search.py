#!/usr/bin/env python3
"""
Stage 3: Search & Retrieval + Enhancements

This script demonstrates search methods and enhancements in Azure AI Search.

Usage:
    python 03-search.py                     # Run all examples
    python 03-search.py --method fulltext   # Only full-text search
    python 03-search.py --method filter     # Only filter search
    python 03-search.py --method semantic   # Only semantic search
    python 03-search.py --method facets     # Search with facets
    python 03-search.py --method synonyms   # Demo synonym map setup
    python 03-search.py --method scoring    # Demo scoring profiles
    python 03-search.py --query "ML Engineer Dubai"  # Custom query
"""

import os
import argparse
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SynonymMap,
    ScoringProfile,
    TextWeights,
    FreshnessScoringFunction,
    FreshnessScoringParameters,
    MagnitudeScoringFunction,
    MagnitudeScoringParameters,
    ScoringFunctionInterpolation,
)
from azure.search.documents.models import QueryType

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
KEY = os.environ.get("AZURE_SEARCH_KEY")
INDEX = os.environ.get("AZURE_SEARCH_INDEX", "resumes")

def get_client() -> SearchClient:
    """Create search client."""
    return SearchClient(
        endpoint=ENDPOINT,
        index_name=INDEX,
        credential=AzureKeyCredential(KEY)
    )


def get_index_client() -> SearchIndexClient:
    """Create index management client (for synonyms, scoring profiles)."""
    return SearchIndexClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY)
    )


def print_results(results, title: str, show_score: bool = True):
    """Pretty print search results."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    
    docs = list(results)
    if not docs:
        print("  No results found.")
        return
    
    for i, doc in enumerate(docs[:5], 1):
        score = doc.get("@search.score", 0)
        reranker = doc.get("@search.reranker_score")
        name = doc.get("name", "Unknown")
        title = doc.get("current_title", "Unknown")
        location = doc.get("location", "Unknown")
        exp = doc.get("experience_years", 0)
        skills = doc.get("skills", [])[:5]
        
        print(f"\n  {i}. {name}")
        print(f"     Title: {title}")
        print(f"     Location: {location} | Experience: {exp} years")
        print(f"     Skills: {', '.join(skills)}")
        if show_score:
            score_str = f"     Score: {score:.4f}"
            if reranker:
                score_str += f" | Reranker: {reranker:.4f}"
            print(score_str)
    
    print(f"\n  Total: {len(docs)} results shown")


# =============================================================================
# METHOD 1: FULL-TEXT SEARCH (BM25)
# =============================================================================

def search_fulltext(query: str):
    """
    Full-text search using BM25 algorithm.
    
    How it works:
    - Tokenizes query into terms
    - Matches terms against searchable fields
    - Scores by TF-IDF (term frequency × inverse document frequency)
    
    Good for:
    - Exact keyword matches
    - When you know the exact terms to search
    
    Limitations:
    - Misses synonyms ("ML" won't find "Machine Learning")
    - Doesn't understand intent
    """
    client = get_client()
    
    results = client.search(
        search_text=query,
        query_type=QueryType.SIMPLE,  # BM25/Lucene
        search_fields=["name", "current_title", "skills", "summary", "location"],
        select=["name", "current_title", "skills", "experience_years", "location"],
        top=5
    )
    
    print_results(results, f"FULL-TEXT SEARCH: '{query}'")


# =============================================================================
# METHOD 2: FILTER SEARCH
# =============================================================================

def search_filter(filter_expr: str, query: str = "*"):
    """
    Filter search - exact matches on filterable fields.
    
    How it works:
    - Applies OData filter expression
    - Returns only documents matching the filter
    - Can combine with full-text search
    
    Filter syntax:
    - Comparison: eq, ne, gt, ge, lt, le
    - Logical: and, or, not
    - Collections: any(), all()
    - String: search.in(), search.ismatch()
    
    Good for:
    - Exact value matches
    - Range queries (experience >= 5)
    - Boolean flags (open_to_opportunities eq true)
    """
    client = get_client()
    
    results = client.search(
        search_text=query,
        filter=filter_expr,
        select=["name", "current_title", "skills", "experience_years", "location", "open_to_opportunities"],
        top=5
    )
    
    print_results(results, f"FILTER SEARCH: {filter_expr}", show_score=False)


# =============================================================================
# METHOD 3: SEMANTIC SEARCH
# =============================================================================

def search_semantic(query: str):
    """
    Semantic search - understands meaning, not just keywords.
    
    How it works:
    1. Runs BM25 full-text search first
    2. Takes top 50 results
    3. ML model re-ranks by semantic relevance
    4. Returns reordered results with reranker scores
    
    Good for:
    - Natural language queries
    - Understanding intent ("someone who builds APIs")
    - Complex job descriptions
    
    Requirements:
    - Semantic configuration on index
    - Basic tier or higher (paid feature)
    """
    client = get_client()
    
    results = client.search(
        search_text=query,
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="default",
        select=["name", "current_title", "skills", "experience_years", "location", "summary"],
        top=5
    )
    
    print_results(results, f"SEMANTIC SEARCH: '{query}'")


# =============================================================================
# METHOD 4: COMBINED (SEMANTIC + FILTER)
# =============================================================================

def search_combined(query: str, filter_expr: str):
    """
    Combined search - semantic search with filters.
    
    This is what the talent-reconnect-agent uses:
    1. Filter to narrow candidates (location, experience, etc.)
    2. Semantic search for relevance ranking
    
    Best of both worlds:
    - Filters for hard requirements (must have 5+ years)
    - Semantic for soft matching (understands JD intent)
    """
    client = get_client()
    
    results = client.search(
        search_text=query,
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="default",
        filter=filter_expr,
        select=["name", "current_title", "skills", "experience_years", "location", "summary"],
        top=5
    )
    
    print_results(results, f"COMBINED: '{query}' + Filter: {filter_expr}")


# =============================================================================
# ENHANCEMENT 1: FACETS (Aggregated Counts)
# =============================================================================

def search_with_facets(query: str):
    """
    Faceted search - get aggregated counts for filtering UI.
    
    How it works:
    - Returns search results PLUS aggregated counts per field value
    - Useful for building filter panels ("50 in Dubai, 30 in Abu Dhabi")
    
    Good for:
    - Building filter UI with counts
    - Understanding result distribution
    - Drill-down navigation
    
    Requirements:
    - Field must be marked as 'facetable' in index schema
    """
    client = get_client()
    
    results = client.search(
        search_text=query,
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="default",
        facets=[
            "location,count:10",           # Top 10 locations
            "experience_years,interval:2", # Buckets: 0-2, 2-4, 4-6, etc.
            "current_title,count:10",      # Top 10 titles
        ],
        select=["name", "current_title", "skills", "experience_years", "location"],
        top=5
    )
    
    # Extract facets from results
    print(f"\n{'='*60}")
    print(f"  FACETED SEARCH: '{query}'")
    print(f"{'='*60}")
    
    # Print facet counts
    facets = results.get_facets()
    if facets:
        print("\n  📊 FACET COUNTS:")
        
        if "location" in facets:
            print("\n  Location:")
            for facet in facets["location"][:5]:
                print(f"    • {facet['value']}: {facet['count']}")
        
        if "experience_years" in facets:
            print("\n  Experience (years):")
            for facet in facets["experience_years"]:
                print(f"    • {facet['value']}: {facet['count']}")
        
        if "current_title" in facets:
            print("\n  Job Titles:")
            for facet in facets["current_title"][:5]:
                print(f"    • {facet['value']}: {facet['count']}")
    
    # Print results
    print("\n  📋 TOP RESULTS:")
    docs = list(results)
    for i, doc in enumerate(docs[:3], 1):
        print(f"    {i}. {doc.get('name')} - {doc.get('current_title')} ({doc.get('location')})")


# =============================================================================
# ENHANCEMENT 2: SYNONYM MAPS
# =============================================================================

def setup_synonyms(dry_run: bool = True):
    """
    Synonym maps - expand queries with equivalent terms.
    
    How it works:
    - Define mappings: "ML, Machine Learning" means they're equivalent
    - When user searches "ML", also finds "Machine Learning"
    - Applied at query time (no re-indexing needed)
    
    Mapping types:
    - Equivalent: "ML, Machine Learning" (bidirectional)
    - Explicit: "JS => JavaScript" (one direction only)
    
    Good for:
    - Abbreviations (ML → Machine Learning)
    - Common variations (K8s → Kubernetes)
    - Industry terms (SWE → Software Engineer)
    
    Requirements:
    - Create synonym map
    - Associate with field in index schema
    """
    
    # Define synonym mappings for talent search
    synonym_rules = """
# Equivalent mappings (bidirectional)
ML, Machine Learning, machine learning, machine-learning
AI, Artificial Intelligence, artificial intelligence
NLP, Natural Language Processing, natural language processing
CV, Computer Vision, computer vision
DL, Deep Learning, deep learning
DS, Data Science, data science
DE, Data Engineering, data engineering
SWE, Software Engineer, Software Engineering
JS, JavaScript, javascript
TS, TypeScript, typescript
K8s, Kubernetes, kubernetes
AWS, Amazon Web Services
GCP, Google Cloud Platform, Google Cloud
# Explicit mappings (one direction)
Jr => Junior
Sr => Senior
Mgr => Manager
"""
    
    print(f"\n{'='*60}")
    print(f"  SYNONYM MAP SETUP")
    print(f"{'='*60}")
    print("\n  Synonym rules to create:")
    print("-" * 40)
    for line in synonym_rules.strip().split("\n"):
        if line.strip() and not line.startswith("#"):
            print(f"    {line.strip()}")
    print("-" * 40)
    
    if dry_run:
        print("\n  ⚠️  DRY RUN - No changes made")
        print("  Run with --apply-synonyms to create the synonym map")
        return
    
    # Create synonym map
    index_client = get_index_client()
    
    synonym_map = SynonymMap(
        name="talent-synonyms",
        synonyms=synonym_rules
    )
    
    try:
        index_client.create_or_update_synonym_map(synonym_map)
        print("\n  ✅ Synonym map 'talent-synonyms' created/updated!")
        print("\n  📝 Next step: Associate with fields in index schema:")
        print('     field.synonym_map_names = ["talent-synonyms"]')
    except Exception as e:
        print(f"\n  ❌ Error: {e}")


# =============================================================================
# ENHANCEMENT 3: SCORING PROFILES
# =============================================================================

def setup_scoring_profile(dry_run: bool = True):
    """
    Scoring profiles - custom relevance boosting rules.
    
    How it works:
    - Define boost functions based on field values
    - Applied after BM25 scoring, before semantic reranking
    - Multiple functions can be combined
    
    Boost types:
    - magnitude: Boost by numeric value (experience_years)
    - freshness: Boost by date recency (last_updated)
    - distance: Boost by geo proximity (location)
    - tag: Boost if field matches tags (preferred locations)
    
    Good for:
    - Boosting UAE candidates
    - Preferring candidates open to opportunities
    - Weighting experience appropriately
    
    Requirements:
    - Define scoring profile in index schema
    - Reference by name in search query
    """
    
    print(f"\n{'='*60}")
    print(f"  SCORING PROFILE SETUP")
    print(f"{'='*60}")
    
    # Define the scoring profile
    print("\n  Scoring profile 'talent-boost' configuration:")
    print("-" * 50)
    print("""
    Text Weights (boost searchable fields):
      • current_title: 2.0x (job title matches matter most)
      • skills: 1.5x (skill matches important)
      • summary: 1.0x (baseline)
    
    Magnitude Functions:
      • experience_years: boost 1.5x
        - Linear interpolation from 0-15 years
        - More experience = higher score
    
    Usage in query:
      results = client.search(
          search_text=query,
          scoring_profile="talent-boost",
          ...
      )
    """)
    print("-" * 50)
    
    if dry_run:
        print("\n  ⚠️  DRY RUN - No changes made")
        print("  Run with --apply-scoring to add profile to index")
        return
    
    # Create scoring profile
    scoring_profile = ScoringProfile(
        name="talent-boost",
        text_weights=TextWeights(
            weights={
                "current_title": 2.0,
                "skills": 1.5,
                "summary": 1.0,
            }
        ),
        functions=[
            MagnitudeScoringFunction(
                field_name="experience_years",
                boost=1.5,
                interpolation=ScoringFunctionInterpolation.LINEAR,
                parameters=MagnitudeScoringParameters(
                    boosting_range_start=0,
                    boosting_range_end=15,
                    constant_boost_beyond_range=True
                )
            ),
        ]
    )
    
    try:
        index_client = get_index_client()
        index = index_client.get_index(INDEX)
        
        # Add or update scoring profile
        existing_names = [p.name for p in (index.scoring_profiles or [])]
        if "talent-boost" in existing_names:
            index.scoring_profiles = [
                p if p.name != "talent-boost" else scoring_profile 
                for p in index.scoring_profiles
            ]
        else:
            index.scoring_profiles = (index.scoring_profiles or []) + [scoring_profile]
        
        index_client.create_or_update_index(index)
        print("\n  ✅ Scoring profile 'talent-boost' added to index!")
    except Exception as e:
        print(f"\n  ❌ Error: {e}")


def search_with_scoring_profile(query: str):
    """Search using the custom scoring profile."""
    client = get_client()
    
    results = client.search(
        search_text=query,
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="default",
        scoring_profile="talent-boost",
        select=["name", "current_title", "skills", "experience_years", "location"],
        top=5
    )
    
    print_results(results, f"SEARCH WITH SCORING PROFILE: '{query}'")


# =============================================================================
# EXAMPLES
# =============================================================================

def run_examples():
    """Run all search method examples."""
    
    print("\n" + "="*60)
    print("  AZURE AI SEARCH - METHOD COMPARISON")
    print("="*60)
    
    # Example 1: Full-text search
    print("\n\n📝 EXAMPLE 1: Full-text search")
    print("   Query with exact keywords")
    search_fulltext("Python Developer Dubai")
    
    # Example 2: Filter search
    print("\n\n🔍 EXAMPLE 2: Filter search")
    print("   Find senior candidates in UAE")
    search_filter("experience_years ge 8 and location eq 'Dubai'")
    
    # Example 3: Filter with collection
    print("\n\n🔍 EXAMPLE 3: Filter on skills (collection)")
    print("   Must have Python skill")
    search_filter("skills/any(s: s eq 'Python')")
    
    # Example 4: Semantic search
    print("\n\n🧠 EXAMPLE 4: Semantic search")
    print("   Natural language query - understands intent")
    search_semantic("Someone who can build and deploy machine learning models")
    
    # Example 5: Semantic vs Full-text comparison
    print("\n\n⚖️ EXAMPLE 5: Semantic vs Full-text")
    print("   Same query, different results")
    print("\n   --- Full-text ---")
    search_fulltext("Tech leader for AI startup")
    print("\n   --- Semantic ---")
    search_semantic("Tech leader for AI startup")
    
    # Example 6: Combined (production pattern)
    print("\n\n🚀 EXAMPLE 6: Combined (Production Pattern)")
    print("   Semantic search + filters (what your agent uses)")
    search_combined(
        query="Senior ML Engineer with production experience in NLP",
        filter_expr="experience_years ge 5 and skills/any(s: s eq 'Python')"
    )
    
    print("\n\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print("""
    | Method      | Use When                              |
    |-------------|---------------------------------------|
    | Full-text   | Exact keyword search                  |
    | Filter      | Hard requirements (exp >= 5)          |
    | Semantic    | Natural language, understand intent   |
    | Combined    | Production - filters + semantic       |
    | + Facets    | Build filter UI with counts           |
    | + Synonyms  | Handle abbreviations (ML → Machine Learning) |
    | + Scoring   | Custom relevance boosting             |
    """)


# =============================================================================
# FILTER SYNTAX REFERENCE
# =============================================================================

def show_filter_reference():
    """Print OData filter syntax reference."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         ODATA FILTER SYNTAX REFERENCE                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  COMPARISON OPERATORS                                                        ║
║  ────────────────────                                                        ║
║  eq    Equal              experience_years eq 5                              ║
║  ne    Not equal          location ne 'Remote'                               ║
║  gt    Greater than       experience_years gt 5                              ║
║  ge    Greater or equal   experience_years ge 5                              ║
║  lt    Less than          experience_years lt 10                             ║
║  le    Less or equal      experience_years le 10                             ║
║                                                                              ║
║  LOGICAL OPERATORS                                                           ║
║  ─────────────────                                                           ║
║  and   Both true          experience_years ge 5 and location eq 'Dubai'      ║
║  or    Either true        location eq 'Dubai' or location eq 'Abu Dhabi'     ║
║  not   Negate             not open_to_opportunities eq false                 ║
║                                                                              ║
║  COLLECTION OPERATORS (for array fields like skills)                         ║
║  ────────────────────                                                        ║
║  any   At least one       skills/any(s: s eq 'Python')                       ║
║  all   Every item         skills/all(s: s ne 'Java')                         ║
║                                                                              ║
║  STRING FUNCTIONS                                                            ║
║  ────────────────                                                            ║
║  search.in()              search.in(location, 'Dubai,Abu Dhabi,Sharjah')     ║
║  search.ismatch()         search.ismatch('python*', 'skills')                ║
║                                                                              ║
║  EXAMPLES FOR TALENT SEARCH                                                  ║
║  ──────────────────────────                                                  ║
║                                                                              ║
║  Senior candidates in UAE:                                                   ║
║    experience_years ge 8 and search.in(location, 'Dubai,Abu Dhabi,Remote')   ║
║                                                                              ║
║  Open to opportunities with Python:                                          ║
║    open_to_opportunities eq true and skills/any(s: s eq 'Python')            ║
║                                                                              ║
║  ML specialists (5+ years, has ML skill):                                    ║
║    experience_years ge 5 and skills/any(s: search.ismatch('*ML*', s))        ║
║                                                                              ║
║  Exclude contractors:                                                        ║
║    not current_title eq 'Contractor'                                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Azure AI Search - Search Methods Demo")
    parser.add_argument("--method", choices=["fulltext", "filter", "semantic", "combined", "facets", "synonyms", "scoring", "all"],
                        default="all", help="Which search method to demonstrate")
    parser.add_argument("--query", type=str, default="Python Developer Dubai",
                        help="Search query to use")
    parser.add_argument("--filter", type=str, default="experience_years ge 5",
                        help="Filter expression for filter/combined search")
    parser.add_argument("--reference", action="store_true",
                        help="Show OData filter syntax reference")
    parser.add_argument("--apply-synonyms", action="store_true",
                        help="Actually create the synonym map (not dry run)")
    parser.add_argument("--apply-scoring", action="store_true",
                        help="Actually add scoring profile to index (not dry run)")
    
    args = parser.parse_args()
    
    if args.reference:
        show_filter_reference()
        return
    
    if args.method == "all":
        run_examples()
    elif args.method == "fulltext":
        search_fulltext(args.query)
    elif args.method == "filter":
        search_filter(args.filter, args.query)
    elif args.method == "semantic":
        search_semantic(args.query)
    elif args.method == "combined":
        search_combined(args.query, args.filter)
    elif args.method == "facets":
        search_with_facets(args.query)
    elif args.method == "synonyms":
        setup_synonyms(dry_run=not args.apply_synonyms)
    elif args.method == "scoring":
        if args.apply_scoring:
            setup_scoring_profile(dry_run=False)
            print("\n  Now you can search with: --method scoring")
        else:
            setup_scoring_profile(dry_run=True)


if __name__ == "__main__":
    main()
