import os
import sys
import time
from dotenv import load_dotenv
from agentic_system.src.retriever import SemanticRetriever
from agentic_system.src.tools import ToolRegistry
from agentic_system.src.control_plane import ControlPlane
from agentic_system.src.agent import TutorAgent
from agentic_system.src.voice import VoiceInterface

def run_interactive_system():
    # load environment variables
    load_dotenv()
    
    print("=" * 70)
    print("agentic ai tutor: interactive voice system (together api)")
    print("=" * 70)

    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("error: TOGETHER_API_KEY environment variable not found.")
        print("please set it in .env or export it.")
        sys.exit(1)

    # initialize components
    print("initializing system components...")
    retriever = SemanticRetriever()
    tool_registry = ToolRegistry(retriever)
    control_plane = ControlPlane(tool_registry)
    
    try:
        tutor = TutorAgent(control_plane, api_key)
        voice = VoiceInterface()
    except Exception as e:
        print(f"failed to initialize components: {e}")
        sys.exit(1)

    print("system ready. listening for commands...")
    voice.speak("system initialized. i am ready to help you learn.")

    while True:
        try:
            # listen for user input
            user_input = voice.listen()
            
            if not user_input:
                continue
                
            print(f"user: {user_input}")
            
            # check for exit commands
            if any(cmd in user_input.lower() for cmd in ["exit", "quit", "stop", "goodbye"]):
                print("exiting system...")
                voice.speak("goodbye. happy learning.")
                break
            
            # process query with agent
            response = tutor.teach(user_input)
            print(f"tutor: {response}")
            
            # speak response
            voice.speak(response)
            
        except KeyboardInterrupt:
            print("\nstopping system...")
            break
        except Exception as e:
            print(f"error in main loop: {e}")
            voice.speak("i encountered an error. please try again.")

    print("\n" + "=" * 70)
    print("system state summary")
    print("=" * 70)
    print(f"total executions: {len(control_plane.execution_log)}")
    print(f"logged interactions: {len(tool_registry.interaction_log)}")
    print(f"user profile: {tool_registry.user_state}")

if __name__ == "__main__":
    run_interactive_system()
