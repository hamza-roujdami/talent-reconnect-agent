"""
Search Quality Evaluation

Tests precision and relevance of BM25 vs Semantic search.
"""
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.search_bm25 import search_resumes_bm25
from tools.search_semantic import search_resumes_semantic


def load_golden_dataset():
    """Load test queries from golden dataset."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


def extract_skills_from_result(result_text: str) -> set:
    """Extract skills mentioned in a search result."""
    # Simple keyword extraction - in production use NER
    common_skills = [
        "python", "javascript", "typescript", "react", "node.js", "nodejs",
        "aws", "azure", "gcp", "docker", "kubernetes", "k8s",
        "pytorch", "tensorflow", "machine learning", "ml", "ai",
        "django", "fastapi", "flask", "express",
        "sql", "postgresql", "mongodb", "redis",
        "nlp", "transformers", "bert", "gpt",
        "java", "go", "rust", "c++",
    ]
    result_lower = result_text.lower()
    return {skill for skill in common_skills if skill in result_lower}


def calculate_precision(results: str, expected_skills: list) -> float:
    """Calculate precision based on skill overlap."""
    if not results or results == "No matching candidates found.":
        return 0.0
    
    expected_set = {s.lower() for s in expected_skills}
    found_skills = extract_skills_from_result(results)
    
    if not found_skills:
        return 0.0
    
    overlap = found_skills & expected_set
    return len(overlap) / len(expected_set) if expected_set else 0.0


def run_search_eval():
    """Run search quality evaluation."""
    print("=" * 60)
    print("Search Quality Evaluation")
    print("=" * 60)
    
    dataset = load_golden_dataset()
    queries = dataset["search_queries"]
    
    bm25_scores = []
    semantic_scores = []
    
    for query_data in queries:
        query = query_data["query"]
        expected_skills = query_data["relevant_skills"]
        
        print(f"\n📝 Query: {query}")
        print(f"   Expected skills: {', '.join(expected_skills)}")
        
        # BM25 search
        bm25_results = search_resumes_bm25(query)
        bm25_precision = calculate_precision(bm25_results, expected_skills)
        bm25_scores.append(bm25_precision)
        
        # Semantic search
        semantic_results = search_resumes_semantic(query)
        semantic_precision = calculate_precision(semantic_results, expected_skills)
        semantic_scores.append(semantic_precision)
        
        print(f"   BM25 Precision: {bm25_precision:.0%}")
        print(f"   Semantic Precision: {semantic_precision:.0%}")
        
        if semantic_precision > bm25_precision:
            print(f"   ✅ Semantic wins (+{semantic_precision - bm25_precision:.0%})")
        elif bm25_precision > semantic_precision:
            print(f"   ⚠️ BM25 wins (+{bm25_precision - semantic_precision:.0%})")
        else:
            print(f"   ➡️ Tie")
    
    # Summary
    avg_bm25 = sum(bm25_scores) / len(bm25_scores) if bm25_scores else 0
    avg_semantic = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Average BM25 Precision: {avg_bm25:.0%}")
    print(f"Average Semantic Precision: {avg_semantic:.0%}")
    print(f"Semantic Improvement: {avg_semantic - avg_bm25:+.0%}")
    
    return {
        "bm25_avg_precision": avg_bm25,
        "semantic_avg_precision": avg_semantic,
        "improvement": avg_semantic - avg_bm25,
    }


if __name__ == "__main__":
    run_search_eval()
