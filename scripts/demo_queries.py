#!/usr/bin/env python3
"""
CV Screener - Demo Query Script

This script demonstrates the RAG pipeline by running sample queries
against the API and displaying results with timing metrics.

Usage:
    python scripts/demo_queries.py [--base-url http://localhost:8000]
"""

import argparse
import asyncio
import httpx
import json
import time
from typing import Optional


# Demo queries to showcase different capabilities
DEMO_QUERIES = [
    {
        "question": "Who has Python experience?",
        "description": "Skills search - finds candidates with Python skills"
    },
    {
        "question": "Compare the top 3 candidates for a senior developer role",
        "description": "Comparison query - analyzes and ranks candidates"
    },
    {
        "question": "Which candidate has the most years of experience?",
        "description": "Ranking query - identifies most experienced candidate"
    },
    {
        "question": "List all candidates with cloud computing experience (AWS, Azure, GCP)",
        "description": "Multi-skill search - finds cloud expertise"
    },
    {
        "question": "Summarize the profile of the strongest backend developer",
        "description": "Profile summary - detailed candidate analysis"
    }
]


async def run_query(
    client: httpx.AsyncClient,
    session_id: str,
    question: str,
    mode: str = "local"
) -> dict:
    """Execute a query against the RAG API."""
    start_time = time.perf_counter()
    
    response = await client.post(
        f"/api/sessions/{session_id}/chat",
        params={"mode": mode},
        json={"message": question}
    )
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    
    if response.status_code != 200:
        return {
            "success": False,
            "error": f"HTTP {response.status_code}: {response.text}",
            "client_time_ms": elapsed_ms
        }
    
    data = response.json()
    data["success"] = True
    data["client_time_ms"] = elapsed_ms
    return data


async def get_or_create_session(
    client: httpx.AsyncClient,
    mode: str = "local"
) -> Optional[str]:
    """Get existing session or create a new one."""
    # List sessions
    response = await client.get(f"/api/sessions", params={"mode": mode})
    if response.status_code == 200:
        sessions = response.json()
        if sessions:
            return sessions[0]["id"]
    
    # Create new session
    response = await client.post(
        "/api/sessions",
        params={"mode": mode},
        json={"name": "Demo Session", "description": "Created by demo script"}
    )
    
    if response.status_code == 200:
        return response.json()["id"]
    
    return None


def print_result(query_info: dict, result: dict):
    """Pretty print query result."""
    print("\n" + "=" * 70)
    print(f"Query: {query_info['question']}")
    print(f"Type: {query_info['description']}")
    print("-" * 70)
    
    if not result.get("success"):
        print(f"ERROR: {result.get('error')}")
        return
    
    # Print response (truncated)
    response_text = result.get("response", "")
    if len(response_text) > 500:
        response_text = response_text[:500] + "..."
    print(f"\nResponse:\n{response_text}")
    
    # Print sources
    sources = result.get("sources", [])
    if sources:
        print(f"\nSources ({len(sources)} documents):")
        for src in sources[:3]:
            print(f"  - {src.get('filename')} (relevance: {src.get('relevance', 0):.2f})")
    
    # Print metrics
    metrics = result.get("metrics", {})
    print(f"\nMetrics:")
    print(f"  - Query Understanding: {metrics.get('understanding_ms', 0):.0f}ms")
    print(f"  - Embedding: {metrics.get('embedding_ms', 0):.0f}ms")
    print(f"  - Vector Search: {metrics.get('search_ms', 0):.0f}ms")
    print(f"  - LLM Generation: {metrics.get('llm_ms', 0):.0f}ms")
    print(f"  - Total (server): {metrics.get('total_ms', 0):.0f}ms")
    print(f"  - Total (client): {result.get('client_time_ms', 0):.0f}ms")
    
    # Print confidence
    confidence = result.get("confidence_score", 0)
    print(f"  - Confidence: {confidence:.2f}")


async def main(base_url: str, mode: str):
    """Run demo queries."""
    print("=" * 70)
    print("CV Screener - Demo Query Script")
    print(f"Base URL: {base_url}")
    print(f"Mode: {mode}")
    print("=" * 70)
    
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        # Health check
        try:
            response = await client.get("/api/health")
            if response.status_code != 200:
                print("ERROR: API not healthy")
                return
            print(f"API Status: {response.json()}")
        except Exception as e:
            print(f"ERROR: Cannot connect to API - {e}")
            return
        
        # Get or create session
        session_id = await get_or_create_session(client, mode)
        if not session_id:
            print("ERROR: Could not get or create session")
            return
        
        print(f"Using session: {session_id}")
        
        # Check if session has CVs
        response = await client.get(f"/api/sessions/{session_id}", params={"mode": mode})
        if response.status_code == 200:
            session_data = response.json()
            cv_count = len(session_data.get("cvs", []))
            print(f"CVs in session: {cv_count}")
            
            if cv_count == 0:
                print("\nWARNING: No CVs in session. Please upload CVs first.")
                print("You can upload CVs through the web UI or use the API:")
                print(f"  POST {base_url}/api/sessions/{session_id}/cvs")
                return
        
        # Run demo queries
        print(f"\nRunning {len(DEMO_QUERIES)} demo queries...")
        
        for query_info in DEMO_QUERIES:
            result = await run_query(
                client,
                session_id,
                query_info["question"],
                mode
            )
            print_result(query_info, result)
            
            # Small delay between queries
            await asyncio.sleep(1)
        
        print("\n" + "=" * 70)
        print("Demo completed!")
        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CV Screener Demo Queries")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--mode",
        default="local",
        choices=["local", "cloud"],
        help="Mode to use (default: local)"
    )
    
    args = parser.parse_args()
    asyncio.run(main(args.base_url, args.mode))
