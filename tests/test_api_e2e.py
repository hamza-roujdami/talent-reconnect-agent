#!/usr/bin/env python3
"""
End-to-end API test - starts server and runs demo via HTTP.

Usage:
    python tests/test_api_e2e.py           # Run full E2E test
    python tests/test_api_e2e.py --quick   # Quick health check only
"""
import argparse
import asyncio
import json
import sys
import time
import warnings
from contextlib import asynccontextmanager

import httpx

# Suppress aiohttp warnings
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", message="Unclosed connector")

BASE_URL = "http://localhost:8000"

# Demo conversation (same as demo_test.py)
DEMO_SCRIPT = [
    "Hire a Data Engineer in Dubai",
    "Add Azure to the required skills",
    "yes",
    "Check interview feedback for all candidates",
    "Send email to candidate 1",
]

# Colors
class C:
    H = '\033[95m'
    B = '\033[94m'
    C = '\033[96m'
    G = '\033[92m'
    Y = '\033[93m'
    R = '\033[91m'
    E = '\033[0m'
    BOLD = '\033[1m'


@asynccontextmanager
async def run_server():
    """Start the FastAPI server as a subprocess."""
    import subprocess
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=os.getcwd(),
    )

    # Wait for server to be ready
    print(f"{C.Y}⏳ Starting server...{C.E}")
    async with httpx.AsyncClient() as client:
        for _ in range(30):
            try:
                resp = await client.get(f"{BASE_URL}/health", timeout=2.0)
                if resp.status_code == 200:
                    print(f"{C.G}✅ Server ready{C.E}")
                    break
            except Exception:
                pass
            await asyncio.sleep(0.5)
        else:
            proc.terminate()
            raise RuntimeError("Server failed to start")

    try:
        yield proc
    finally:
        print(f"{C.Y}🛑 Stopping server...{C.E}")
        proc.terminate()
        proc.wait(timeout=5)


async def test_health():
    """Test health endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        print(f"{C.G}✅ Health check passed{C.E}")
        print(f"   Model: {data.get('model')}")
        print(f"   Sessions: {data.get('sessions')}")
        return data


async def test_chat_stream(message: str, session_id: str | None = None) -> tuple[str, str, list[str]]:
    """
    Send a message to /chat/stream and collect SSE events.
    
    Returns: (session_id, full_text, agents_seen)
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{BASE_URL}/chat/stream",
            json={"message": message, "session_id": session_id},
        ) as resp:
            session_id_out = session_id
            full_text = ""
            agents_seen = []
            tool_results = []

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break

                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")

                if event_type == "session":
                    session_id_out = event.get("session_id")
                elif event_type == "agent":
                    agents_seen.append(event.get("name"))
                elif event_type == "tool":
                    pass  # Tool announcement
                elif event_type == "tool_result":
                    tool_results.append(event.get("content", ""))
                elif event_type == "text":
                    full_text += event.get("content", "")
                elif event_type == "error":
                    raise RuntimeError(f"Stream error: {event.get('message')}")

            # Combine tool results and text for full response
            combined = "\n".join(tool_results) + "\n" + full_text
            return session_id_out, combined.strip(), agents_seen


async def run_demo_via_api():
    """Run the full demo script via HTTP API."""
    print(f"\n{C.H}{C.BOLD}{'='*70}{C.E}")
    print(f"{C.H}{C.BOLD}  E2E API TEST: Talent Reconnect Demo{C.E}")
    print(f"{C.H}{C.BOLD}{'='*70}{C.E}\n")

    session_id = None
    total_start = time.perf_counter()

    for i, message in enumerate(DEMO_SCRIPT, 1):
        step_start = time.perf_counter()
        print(f"\n{C.BOLD}{'─'*70}{C.E}")
        print(f"{C.BOLD}Step {i}: {message}{C.E}")
        print(f"{C.BOLD}{'─'*70}{C.E}\n")

        session_id, response, agents = await test_chat_stream(message, session_id)

        # Show agents
        for agent in agents:
            print(f"{C.C}🤖 [{agent}]{C.E}")

        # Show response (truncated)
        lines = response.split("\n")
        for line in lines[:40]:
            print(f"{C.G}{line}{C.E}")
        if len(lines) > 40:
            print(f"{C.Y}... ({len(lines) - 40} more lines){C.E}")

        step_duration = time.perf_counter() - step_start
        print(f"\n{C.B}⏱️  Step {i} latency: {step_duration:.2f}s{C.E}")

        # Assertions per step
        if i == 1:
            assert "Role" in response or "Data Engineer" in response, "Step 1 should produce role profile"
        elif i == 3:
            assert "Candidate" in response or "email" in response.lower(), "Step 3 should list candidates"
        elif i == 4:
            # Feedback step - should find history OR say no history
            assert "history" in response.lower() or "feedback" in response.lower() or "interview" in response.lower(), \
                "Step 4 should discuss feedback"
        elif i == 5:
            assert "email" in response.lower() or "draft" in response.lower(), "Step 5 should draft email"

        await asyncio.sleep(0.5)

    total_duration = time.perf_counter() - total_start

    print(f"\n{C.H}{C.BOLD}{'='*70}{C.E}")
    print(f"{C.G}{C.BOLD}  ✅ E2E API Test Complete!{C.E}")
    print(f"{C.B}  Total time: {total_duration:.1f}s{C.E}")
    print(f"{C.H}{C.BOLD}{'='*70}{C.E}\n")


async def test_sessions():
    """Test session management endpoints."""
    async with httpx.AsyncClient() as client:
        # List sessions
        resp = await client.get(f"{BASE_URL}/sessions")
        assert resp.status_code == 200
        sessions = resp.json().get("sessions", [])
        print(f"{C.G}✅ Sessions list: {len(sessions)} session(s){C.E}")

        # If we have a session, try to get its history
        if sessions:
            sid = sessions[0]["id"]
            resp = await client.get(f"{BASE_URL}/session/{sid}/history")
            assert resp.status_code == 200
            history = resp.json().get("messages", [])
            print(f"{C.G}✅ Session history: {len(history)} message(s){C.E}")


async def main():
    parser = argparse.ArgumentParser(description="E2E API Test")
    parser.add_argument("--quick", action="store_true", help="Quick health check only")
    parser.add_argument("--no-server", action="store_true", help="Skip starting server (assume already running)")
    args = parser.parse_args()

    if args.no_server:
        # Test against already-running server
        print(f"{C.Y}Testing against existing server at {BASE_URL}{C.E}")
        await test_health()
        if not args.quick:
            await run_demo_via_api()
            await test_sessions()
    else:
        # Start server and run tests
        async with run_server():
            await test_health()
            if not args.quick:
                await run_demo_via_api()
                await test_sessions()


if __name__ == "__main__":
    asyncio.run(main())

    # Suppress stderr at shutdown
    sys.stderr.flush()
    import os
    sys.stderr = open(os.devnull, "w")
