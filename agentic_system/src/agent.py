import os
from typing import List, Dict
from together import Together
from .control_plane import ControlPlane

class TutorAgent:
    """
    An AI-powered tutor agent that uses a Control Plane to orchestrate tools
    and a Large Language Model (LLM) to interact with students.
    """
    
    def __init__(self, control_plane, api_key: str):
        """
        initialize the tutor agent.
        
        Args:
            control_plane: control plane instance for tool execution
            api_key: together api key
        """
        self.control_plane = control_plane
        self.client = Together(api_key=api_key)
        self.conversation_history = []
        self.model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

    def teach(self, student_query: str, session_id: str = None, session_context: List[Dict] = None, session_documents: List[Dict] = None) -> str:
        """
        Process a student's query and generate a response.

        Args:
            student_query (str): The student's question or request.
            session_id (str): The current session ID.
            session_context (List[Dict]): Previous messages in the session.
            session_documents (List[Dict]): Documents uploaded in this session.

        Returns:
            str: The tutor's response.
        """
        # plan actions based on the query
        action_names = self._plan_actions(student_query, session_context, session_documents)
        results = []
        
        # convert action names to proper format and execute
        # convert action names to proper format and execute
        for action_name in action_names:
            # Clean action name
            action_name = action_name.strip()
            print(f"DEBUG: Processing action '{action_name}'")
            
            # create proper action dictionary
            params = {}
            
            # Map query to expected parameters based on tool
            if action_name == "assess_understanding":
                # Extract potential topic from query or use query itself
                topic = student_query.lower()
                if "python" in topic: topic = "python"
                elif "javascript" in topic: topic = "javascript"
                elif "go" in topic: topic = "go"
                elif "rust" in topic: topic = "rust"
                elif "c++" in topic: topic = "c++"
                elif "c" in topic: topic = "c"
                params = {"topic": topic}
            elif action_name == "update_learner_profile":
                params = {"topic": student_query, "proficiency": "fundamental"}
            elif action_name == "set_assignment":
                params = {"description": student_query, "language": "python"}
            elif action_name == "ingest_document":
                # This tool usually needs a path, which isn't in the query. 
                # Skip if no path provided or handle gracefully.
                params = {"path": ""} 
            elif action_name == "analyze_image":
                params = {"image_path": "", "question": student_query}
            elif action_name == "read_file":
                params = {"path": student_query}
            elif action_name == "write_file":
                params = {"path": "output.txt", "content": student_query}
            else:
                # Default for search_knowledge, web_search, etc.
                params = {"query": student_query}
            
            print(f"DEBUG: Action '{action_name}' params: {params}")
            
            # Inject session_id if available and supported by the tool
            supported_tools = ["search_knowledge", "ingest_document", "set_assignment"]
            if session_id and action_name in supported_tools:
                params["session_id"] = session_id
                
            action_plan = {
                "action": action_name,
                "parameters": params,
                "context": {"intent": "teaching"}
            }
            result = self.control_plane.execute(action_plan)
            results.append(result)

        # synthesize a response using the results
        response = self._synthesize_response(student_query, results, session_context, session_documents)

        # update conversation history
        self.conversation_history.append({
            "query": student_query,
            "plan": action_names,
            "results": results,
            "response": response
        })
        return response
    
    def _plan_actions(self, query: str, session_context: List[Dict] = None, session_documents: List[Dict] = None) -> List[str]:
        """
        plan which tools to use based on user query.
        
        Args:
            query (str): user's question
            session_context (List[Dict]): previous session messages
            session_documents (List[Dict]): uploaded documents
            
        Returns:
            List[str]: list of tool actions
        """
        # Format session history for context
        history_str = ""
        if session_context:
            history_str = "\n**SESSION HISTORY:**\n"
            # Take last 5 messages for context
            for msg in session_context[-5:]:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:200]  # Truncate long messages
                history_str += f"- {role}: {content}\n"
        
        # Format session documents
        docs_str = ""
        if session_documents:
            docs_str = "\n**SESSION DOCUMENTS (You can reference these):**\n"
            for doc in session_documents:
                docs_str += f"- {doc.get('filename', 'unknown')}: {doc.get('doc_type', 'document')}\n"

        prompt = f"""You are Aura, an AI Tutor with a structured, interactive teaching approach.

**TEACHING PHILOSOPHY:**
1. REMEMBER CONTEXT - Review the session history below before responding
2. BE INTERACTIVE - Ask the student questions to guide their learning
3. TEST UNDERSTANDING - Give quizzes, request code/diagrams to verify learning
4. USE THE WORKSPACE - Assign coding tasks using set_assignment for practice (do this frequently for coding topics)
5. BUILD ON PREVIOUS LESSONS - Reference what you've already taught

**AVAILABLE TOOLS:**
- search_knowledge: Look up concepts
- assess_understanding: Generate quiz questions
- update_learner_profile: Track student's progress
- ingest_document: Learn from uploaded files
- analyze_image: Review diagrams/screenshots
- read_file / write_file: Access/create files
- web_search: Find current resources
- set_assignment: Push coding tasks to the Interactive Workspace
- run_code: Execute code demonstrations{history_str}{docs_str}
**CURRENT QUESTION:** {query}

**IMPORTANT INSTRUCTIONS:**
1. If the student asks for coding help or practice, use 'set_assignment' to give them a task
2. Reference the session history to build on what you've already discussed
3. Ask follow-up questions to check understanding
4. Be encouraging and patient

List the tools you need (one per line, from the list above):"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            actions_text = response.choices[0].message.content
            actions = [line.strip() for line in actions_text.split('\n') if line.strip()]
            return actions[:5]
        except Exception as e:
            print(f"error planning actions: {e}")
            return ["search_knowledge"]
    
    def _synthesize_response(self, query: str, results: List[Dict], session_context: List[Dict] = None, session_documents: List[Dict] = None) -> str:
        """
        generate final response using llm with gathered context, maintaining tutor persona.
        
        Args:
            query (str): user's question
            results (List[Dict]): gathered context from tools
            session_context (List[Dict]): previous session messages
            
        Returns:
            str: agent response
        """
        # extract context from results
        context = []
        for result in results:
            if isinstance(result, dict):
                context.append(str(result))
        
        context_str = "\n".join([f"- {item}" for item in context])
        
        # Format session history
        history_str = ""
        if session_context and len(session_context) > 1:
            history_str = "\n**YOUR CONVERSATION WITH THE STUDENT SO FAR:**\n"
            for msg in session_context[-6:]:  # Last 6 messages
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                role_label = "YOU (Aura)" if role == "assistant" else "STUDENT"
                # Show more context
                content_preview = content[:300] + "..." if len(content) > 300 else content
                history_str += f"{role_label}: {content_preview}\n\n"
        
        # Format session documents
        docs_str = ""
        if session_documents:
            docs_str = "\n**UPLOADED DOCUMENTS (Reference these when relevant):**\n"
            for doc in session_documents:
                docs_str += f"- {doc.get('filename', 'unknown')}: {doc.get('doc_type', 'document')}\n"
        
        prompt = f"""You are Aura, a dedicated AI coding tutor. You are having a conversation with a student.

**TEACHING CONTEXT FROM TOOLS:**
{context_str}
{history_str}{docs_str}
**STUDENT'S CURRENT QUESTION:**
{query}

**CRITICAL INSTRUCTIONS:**
1. **REMEMBER THE CONVERSATION** - Look at the chat history above. Reference what you've already discussed!
2. **BE INTERACTIVE** - Don't just answer. Ask "Do you have any questions?" or "Would you like to practice this?"
3. **USE THE WORKSPACE SILENTLY** - If you set an assignment, just say "I've updated the workspace for you" or similar, don't be repetitive.
4. **CHECK UNDERSTANDING** - After explaining, ask the student to explain it back or try a problem
5. **BE ENCOURAGING** - Recognize their effort and progress
6. **EVALUATE CODE** - If the student has written code (visible in history or context), evaluate it! Give feedback.

**NEGATIVE CONSTRAINTS (DO NOT DO THIS):**
- **NEVER** say "I remember you said..." or "I remember we were...". You are a tutor, you just KNOW the context.
- **NEVER** say "As I mentioned earlier..." repeatedly.
- **NEVER** announce "I have set up a coding assignment" if you've already done it recently. Just say "Try the new task below".

**RESPONSE STRUCTURE:**
- Acknowledge their question/code (reference previous conversation if relevant)
- Teach the concept clearly with examples OR evaluate their code
- **IMPORTANT**: End with an interactive question like:
  * "Does this make sense? Do you have any questions?"
  * "How would you approach X?"
  * "Try the exercise in the workspace!"

**TONE:** Natural, friendly, and concise. Be like a helpful human pair programmer.

Respond as Aura:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_content = response.choices[0].message.content
            return response_content
        except Exception as e:
            return f"error generating response: {str(e)}\n\nraw context:\n{context_str}"
    
    def analyze_image_with_llm(self, image_path: str, question: str) -> str:
        """
        Analyze image using Together API vision model.
        
        Args:
            image_path (str): path to image
            question (str): question about the image
            
        Returns:
            str: analysis result
        """
        try:
            import base64
            
            # encode image to base64
            with open(image_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # use vision model (Together supports vision models like Llama 3.2 Vision)
            response = self.client.chat.completions.create(
                model="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ]
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"error analyzing image: {e}"
