"""
Search Quality Evaluation

Tests search tool quality using the candidate_search tool directly.
"""
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.candidate_search import search_candidates


def load_golden_dataset():
    """Load test queries from golden dataset."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


def extract_skills_from_result(result_text: str) -> set:
    """Extract skills mentioned in a search result."""
    common_skills = [
        "python", "javascript", "typescript", "react", "node.js", "nodejs",
        "aws", "azure", "gcp", "docker", "kubernetes", "k8s",
        "pytorch", "tensorflow", "machine learning", "ml", "ai",
        "django", "fastapi", "flask", "express",
        "sql", "postgresql", "mongodb", "redis",
        "nlp", "transformers", "bert", "gpt",
        "java", "go", "rust", "c++",
        "scala", "spark", "hadoop", "airflow",
        "pandas", "keras", "langchain", "snowflake",
    ]
    result_lower = result_text.lower()
    return {skill for skill in common_skills if skill in result_lower}


def calculate_precision(results: str, expected_skills: list) -> float:
    """Calculate precision based on skill overlap."""
    if not results or "no matching candidates" in results.lower():
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
    queries = dataset.get("search_queries", [])
    
    if not queries:
        print("\n⚠️ No search_queries found in golden_dataset.json")
        return {"avg_precision": 0}

    scores = []

    for query_data in queries:
        query = query_data["query"]
        expected_skills = query_data["relevant_skills"]

        print(f"\n📝 Query: {query}")
        print(f"   Expected skills: {', '.join(expected_skills)}")

        # Run search
        result = search_candidates(query, top_k=10)
        
        precision = calculate_precision(result, expected_skills)
        scores.append(precision)

        print(f"   Precision: {precision:.0%}")
        
        # Show found skills
        found = extract_skills_from_result(result)
        if found:
            print(f"   Found: {', '.join(sorted(found))}")

    avg_precision = sum(scores) / len(scores) if scores else 0

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Average Precision: {avg_precision:.0%}")
    print(f"Queries Tested: {len(scores)}")

    return {
        "avg_precision": avg_precision,
        "queries_tested": len(scores),
    }


if __name__ == "__main__":
    run_search_eval()
