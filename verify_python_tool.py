import sys
import os

# Add project root to path
sys.path.append(os.path.abspath("/home/bealthguy/Public/agentic"))

from agentic_system.src.tools import ToolRegistry
from agentic_system.src.retriever import SemanticRetriever

# Mock retriever
class MockRetriever:
    def search(self, *args, **kwargs):
        return []

def test_run_python():
    registry = ToolRegistry(MockRetriever())
    
    # Test 1: Simple calculation
    code = "print(2 + 2)"
    result = registry.run_python(code)
    print(f"Test 1 Result: {result}")
    assert result["status"] == "success"
    assert result["stdout"].strip() == "4"
    
    # Test 2: Error handling
    code = "print(1/0)"
    result = registry.run_python(code)
    print(f"Test 2 Result: {result}")
    assert result["status"] == "success"  # Execution succeeded, script failed
    assert "ZeroDivisionError" in result["stderr"]
    
    print("All tests passed!")

if __name__ == "__main__":
    test_run_python()
