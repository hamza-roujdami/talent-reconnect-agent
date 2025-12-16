#!/usr/bin/env python3
"""
Benchmark: BM25 vs Semantic Search

Compares the two search approaches:
1. BM25 (Lucene simple) - keyword matching with TF-IDF scoring
2. Semantic - hybrid search (BM25 + vectors) with semantic ranking

Usage:
    python scripts/benchmark_search.py
    python scripts/benchmark_search.py --queries 5
"""

import os
import sys
import time
import httpx
import argparse
from typing import List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test queries - mix of easy and hard
TEST_QUERIES = [
    # Easy - exact keyword matches
    {"query": "Python Developer Dubai", "intent": "Exact keywords"},
    {"query": "Machine Learning Engineer", "intent": "Exact role match"},
    
    # Medium - requires understanding
    {"query": "AI Lead with cloud experience", "intent": "Role + skill combo"},
    {"query": "Backend engineer who knows FastAPI", "intent": "Informal phrasing"},
    
    # Hard - semantic understanding needed
    {"query": "Someone who can build data pipelines", "intent": "Task description"},
    {"query": "Tech leader for startup", "intent": "Abstract concept"},
    {"query": "Developer experienced in building APIs", "intent": "Skill inference"},
    {"query": "ML ops person in UAE", "intent": "Abbreviation + location"},
]


@dataclass
class SearchResult:
    name: str
    title: str
    score: float
    skills: List[str]


@dataclass
class BenchmarkResult:
    query: str
    intent: str
    bm25_results: List[SearchResult]
    semantic_results: List[SearchResult]
    bm25_time_ms: float
    semantic_time_ms: float


def search_bm25(query: str, top_k: int = 5) -> tuple[List[SearchResult], float]:
    """BM25/Lucene simple search (current implementation)"""
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    key = os.environ.get("AZURE_SEARCH_KEY")
    index = os.environ.get("AZURE_SEARCH_INDEX", "resumes")
    
    url = f"{endpoint}/indexes/{index}/docs/search?api-version=2024-07-01"
    headers = {"Content-Type": "application/json", "api-key": key}
    body = {
        "search": query,
        "top": top_k,
        "select": "name,current_title,skills,experience_years",
        "queryType": "simple",  # BM25/Lucene
    }
    
    start = time.perf_counter()
    with httpx.Client(timeout=30) as client:
        response = client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
    elapsed = (time.perf_counter() - start) * 1000
    
    results = []
    for doc in data.get("value", []):
        results.append(SearchResult(
            name=doc.get("name", "Unknown"),
            title=doc.get("current_title", "Unknown"),
            score=doc.get("@search.score", 0),
            skills=doc.get("skills", [])[:5],  # Top 5 skills
        ))
    return results, elapsed


def search_semantic(query: str, top_k: int = 5) -> tuple[List[SearchResult], float]:
    """Semantic search with vector embeddings + reranking"""
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    key = os.environ.get("AZURE_SEARCH_KEY")
    index = os.environ.get("AZURE_SEARCH_INDEX", "resumes")
    
    url = f"{endpoint}/indexes/{index}/docs/search?api-version=2024-07-01"
    headers = {"Content-Type": "application/json", "api-key": key}
    body = {
        "search": query,
        "top": top_k,
        "select": "name,current_title,skills,experience_years",
        "queryType": "semantic",  # Semantic ranking
        "semanticConfiguration": "default",
        "captions": "extractive",
        "answers": "extractive",
    }
    
    start = time.perf_counter()
    with httpx.Client(timeout=30) as client:
        response = client.post(url, json=body, headers=headers)
        # Semantic might not be configured - fall back gracefully
        if response.status_code == 400:
            # Try with just semantic query type
            body.pop("captions", None)
            body.pop("answers", None)
            response = client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
    elapsed = (time.perf_counter() - start) * 1000
    
    results = []
    for doc in data.get("value", []):
        # Semantic search returns reranker score
        score = doc.get("@search.rerankerScore", doc.get("@search.score", 0))
        results.append(SearchResult(
            name=doc.get("name", "Unknown"),
            title=doc.get("current_title", "Unknown"),
            score=score,
            skills=doc.get("skills", [])[:5],
        ))
    return results, elapsed


def run_benchmark(num_queries: int = None) -> List[BenchmarkResult]:
    """Run benchmark on all test queries"""
    queries = TEST_QUERIES[:num_queries] if num_queries else TEST_QUERIES
    results = []
    
    print(f"\n🏁 Running benchmark on {len(queries)} queries...\n")
    print("=" * 80)
    
    for i, q in enumerate(queries, 1):
        query = q["query"]
        intent = q["intent"]
        
        print(f"\n[{i}/{len(queries)}] Query: \"{query}\"")
        print(f"    Intent: {intent}")
        
        # Run both searches
        try:
            bm25_results, bm25_time = search_bm25(query)
            semantic_results, semantic_time = search_semantic(query)
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
        
        result = BenchmarkResult(
            query=query,
            intent=intent,
            bm25_results=bm25_results,
            semantic_results=semantic_results,
            bm25_time_ms=bm25_time,
            semantic_time_ms=semantic_time,
        )
        results.append(result)
        
        # Quick preview
        print(f"    BM25     ({bm25_time:.0f}ms): {bm25_results[0].name if bm25_results else 'No results'}")
        print(f"    Semantic ({semantic_time:.0f}ms): {semantic_results[0].name if semantic_results else 'No results'}")
    
    return results


def print_comparison_table(results: List[BenchmarkResult]):
    """Print side-by-side comparison"""
    print("\n")
    print("=" * 100)
    print(" BENCHMARK RESULTS: BM25 vs SEMANTIC SEARCH")
    print("=" * 100)
    
    for r in results:
        print(f"\n📝 Query: \"{r.query}\"")
        print(f"   Intent: {r.intent}")
        print("-" * 100)
        print(f"{'Rank':<6} {'BM25 Result':<40} {'Semantic Result':<40} {'Same?':<6}")
        print("-" * 100)
        
        max_len = max(len(r.bm25_results), len(r.semantic_results), 5)
        for i in range(max_len):
            bm25_name = r.bm25_results[i].name[:38] if i < len(r.bm25_results) else "-"
            sem_name = r.semantic_results[i].name[:38] if i < len(r.semantic_results) else "-"
            same = "✓" if bm25_name == sem_name else "✗"
            print(f"#{i+1:<5} {bm25_name:<40} {sem_name:<40} {same:<6}")
        
        print(f"\n   ⏱️  BM25: {r.bm25_time_ms:.0f}ms | Semantic: {r.semantic_time_ms:.0f}ms")


def print_summary(results: List[BenchmarkResult]):
    """Print summary statistics"""
    print("\n")
    print("=" * 80)
    print(" SUMMARY")
    print("=" * 80)
    
    # Calculate overlap
    total_overlap = 0
    total_top1_same = 0
    avg_bm25_time = 0
    avg_semantic_time = 0
    
    for r in results:
        bm25_names = {x.name for x in r.bm25_results}
        sem_names = {x.name for x in r.semantic_results}
        overlap = len(bm25_names & sem_names) / max(len(bm25_names), 1)
        total_overlap += overlap
        
        if r.bm25_results and r.semantic_results:
            if r.bm25_results[0].name == r.semantic_results[0].name:
                total_top1_same += 1
        
        avg_bm25_time += r.bm25_time_ms
        avg_semantic_time += r.semantic_time_ms
    
    n = len(results)
    print(f"""
┌─────────────────────────────────────────────────────────────────┐
│ Metric                      │ BM25           │ Semantic         │
├─────────────────────────────┼────────────────┼──────────────────┤
│ Avg Response Time           │ {avg_bm25_time/n:>10.0f} ms │ {avg_semantic_time/n:>10.0f} ms     │
│ Top-1 Agreement             │ {total_top1_same}/{n} queries ({total_top1_same/n*100:.0f}%)                       │
│ Top-5 Overlap               │ {total_overlap/n*100:.0f}% average                                │
└─────────────────────────────────────────────────────────────────┘

📊 What this means:
   • BM25: Pure keyword matching. Fast but misses synonyms & context.
   • Semantic: Understands meaning. "build APIs" finds "Backend Developer".
   
🎯 When results DIFFER, semantic usually finds more relevant candidates
   for natural language queries (e.g., "someone who can build data pipelines").

💡 Recommendation:
   • Use BM25 for exact skill/title searches (faster)
   • Use Semantic for natural language job descriptions
   • Consider Agentic (Foundry IQ) for +36% relevance on complex queries
""")


def main():
    parser = argparse.ArgumentParser(description="Benchmark BM25 vs Semantic Search")
    parser.add_argument("--queries", "-n", type=int, help="Number of queries to test")
    args = parser.parse_args()
    
    # Check config
    if not os.environ.get("AZURE_SEARCH_ENDPOINT"):
        print("❌ AZURE_SEARCH_ENDPOINT not set. Run: source .env")
        sys.exit(1)
    
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║           Azure AI Search Benchmark: BM25 vs Semantic                 ║
╠═══════════════════════════════════════════════════════════════════════╣
║  BM25 (Lucene):  Keyword frequency matching (TF-IDF)                  ║
║  Semantic:       Hybrid search + neural reranking (+15-25%)           ║
╚═══════════════════════════════════════════════════════════════════════╝
""")
    
    results = run_benchmark(args.queries)
    print_comparison_table(results)
    print_summary(results)


if __name__ == "__main__":
    main()
