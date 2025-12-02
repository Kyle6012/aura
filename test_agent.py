import os
import sys
from dotenv import load_dotenv
from agentic_system.src.retriever import SemanticRetriever
from agentic_system.src.tools import ToolRegistry
from agentic_system.src.control_plane import ControlPlane
from agentic_system.src.agent import TutorAgent

def test_system():
    load_dotenv()
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("FAIL: TOGETHER_API_KEY not found")
        sys.exit(1)

    print("Initializing components...")
    try:
        retriever = SemanticRetriever()
        tool_registry = ToolRegistry(retriever)
        control_plane = ControlPlane(tool_registry)
        tutor = TutorAgent(control_plane, api_key)
    except Exception as e:
        print(f"FAIL: Initialization error: {e}")
        sys.exit(1)

    query = "What is the purpose of this system?"
    print(f"Testing query: '{query}'")
    
    try:
        response = tutor.teach(query)
        print(f"Response: {response}")
        if response and len(response) > 10:
            print("PASS: System generated a valid response")
        else:
            print("FAIL: Response was empty or too short")
    except Exception as e:
        print(f"FAIL: Execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_system()
