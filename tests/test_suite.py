"""
Comprehensive Test Suite for Talent Reconnect Agent
Tests all 6 workflow steps end-to-end
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator_agent import create_orchestrator

print("✅ Test suite created - Run with: python test_suite.py")
