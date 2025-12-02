import os
import json
import subprocess
import requests
import tempfile
from typing import Dict, Optional, List
from datetime import datetime
from .retriever import SemanticRetriever
from .db import DatabaseManager
from .document_processor import DocumentProcessor

class ToolRegistry:
    """
    A registry of tools available to the agent, handling knowledge retrieval,
    assessment, profile management, interaction logging, and filesystem access.
    """
    
    def __init__(self, retriever: SemanticRetriever):
        """
        Initialize the ToolRegistry.

        Args:
            retriever (SemanticRetriever): The retrieval system to use for knowledge searches.
        """
        self.retriever = retriever
        self.db = None
        self.doc_processor = DocumentProcessor()
        
        # security settings
        self.safe_write_directories = ["/app/uploads", "/tmp"]
        self.command_whitelist = ["ls", "pwd", "cat", "grep", "find", "wc", "head", "tail"]
        
        try:
            self.db = DatabaseManager()
        except Exception as e:
            print(f"warning: database not available, falling back to in-memory storage. error: {e}")
            
        self.interaction_log = []
        # track user state including current level and covered topics
        self.user_state = {"proficiency": "fundamental", "topics_covered": []}

    def search_knowledge(self, query: str, filters: Optional[Dict] = None, session_id: str = None) -> Dict:
        """
        Search the knowledge base for relevant information.

        Args:
            query (str): The search query.
            filters (Optional[Dict]): Metadata filters to apply to results.
            session_id (str): Optional session ID to filter by.

        Returns:
            Dict: The search results including content and metadata.
        """
        # Prepare filters
        search_filters = filters or {}
        if session_id:
            search_filters['session_id'] = session_id
            
        # retrieve documents based on query using search method (fixed from retrieve)
        docs = self.retriever.search(query, top_k=3, filters=search_filters)
        
        return {
            "tool": "search_knowledge",
            "results": [{"content": d.content, "metadata": d.metadata} for d in docs],
            "count": len(docs)
        }

    def assess_understanding(self, topic: str) -> Dict:
        """
        Generate assessment questions for a specific topic.

        Args:
            topic (str): The topic to assess (e.g., 'python', 'ml').

        Returns:
            Dict: A set of assessment questions.
        """
        # predefined questions for assessment
        questions = {
            "python": ["what keyword defines a function?", "how do you create a variable?"],
            "ml": ["what is supervised learning?", "name two types of ml algorithms."],
            "math": ["what is a vector?", "explain matrix multiplication."]
        }
        
        return {
            "tool": "assess_understanding",
            "topic": topic,
            "questions": questions.get(topic, ["general comprehension check."])
        }

    def update_learner_profile(self, topic: str, proficiency: str) -> Dict:
        """
        Update the learner's profile with new topics and proficiency levels.

        Args:
            topic (str): The topic currently being learned.
            proficiency (str): The new proficiency level (e.g., 'fundamental', 'intermediate', 'expert').

        Returns:
            Dict: The updated profile status.
        """
        if self.db:
            profile = self.db.update_profile(proficiency=proficiency, topic=topic)
            self.user_state = profile
        else:
            # fallback to in-memory
            if topic not in self.user_state["topics_covered"]:
                self.user_state["topics_covered"].append(topic)
            self.user_state["proficiency"] = proficiency
        
        return {
            "tool": "update_learner_profile",
            "status": "updated",
            "profile": self.user_state.copy()
        }

    def log_interaction(self, event: str, details: Dict) -> Dict:
        """
        Log an interaction event for audit and debugging purposes.

        Args:
            event (str): The name of the event.
            details (Dict): Detailed context about the event.

        Returns:
            Dict: Confirmation of the log entry.
        """
        entry_id = -1
        if self.db:
            entry_id = self.db.log_interaction(event, details)
        
        # keep in-memory log as well for immediate session access
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "details": details
        }
        self.interaction_log.append(log_entry)
        
        return {
            "tool": "log_interaction", 
            "status": "logged", 
            "entry_id": entry_id if entry_id != -1 else len(self.interaction_log)
        }

    def read_file(self, path: str) -> Dict:
        """
        Read the content of a file from the filesystem.

        Args:
            path (str): The absolute path to the file.

        Returns:
            Dict: The file content or error message.
        """
        try:
            if not os.path.exists(path):
                return {"error": f"file not found: {path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "tool": "read_file",
                "path": path,
                "content": content[:5000] + "... (truncated)" if len(content) > 5000 else content
            }
        except Exception as e:
            return {"error": f"failed to read file: {str(e)}"}

    def list_directory(self, path: str) -> Dict:
        """
        List the contents of a directory.

        Args:
            path (str): The absolute path to the directory.

        Returns:
            Dict: A list of files and directories.
        """
        try:
            if not os.path.exists(path):
                return {"error": f"directory not found: {path}"}
            
            items = os.listdir(path)
            return {
                "tool": "list_directory",
                "path": path,
                "items": items
            }
        except Exception as e:
            return {"error": f"failed to list directory: {str(e)}"}

    def ingest_document(self, path: str, session_id: str = None) -> Dict:
        """
        Process and ingest document into knowledge base.
        
        Args:
            path (str): path to document file
            session_id (str): optional session ID to associate with
            
        Returns:
            Dict: processing result
        """
        try:
            if not os.path.exists(path):
                return {"error": f"file not found: {path}"}
            
            # extract text from document
            result = self.doc_processor.process_file(path)
            
            if "error" in result:
                return result
            
            # add to knowledge base
            filename = os.path.basename(path)
            metadata = {
                "source": filename,
                "type": result["type"],
                "proficiency": "intermediate"
            }
            if session_id:
                metadata["session_id"] = session_id
                
            self.retriever.add_document(
                content=result["text"],
                metadata=metadata
            )
            
            return {
                "tool": "ingest_document",
                "status": "success",
                "filename": filename,
                "chars_extracted": result["length"]
            }
        except Exception as e:
            return {"error": f"failed to ingest document: {str(e)}"}
    
    def analyze_image(self, image_path: str, question: str, agent=None) -> Dict:
        """
        Analyze image using vision model.
        
        Args:
            image_path (str): path to image
            question (str): question about the image
            agent: TutorAgent instance with vision capabilities
            
        Returns:
            Dict: analysis result
        """
        try:
            if not os.path.exists(image_path):
                return {"error": f"image not found: {image_path}"}
            
            if agent is None:
                return {
                    "tool": "analyze_image",
                    "status": "no_agent_instance",
                    "message": "agent instance required for vision"
                }
            
            # use agent's vision capability
            result = agent.analyze_image_with_llm(image_path, question)
            
            return {
                "tool": "analyze_image",
                "status": "success",
                "image": image_path,
                "question": question,
                "analysis": result
            }
        except Exception as e:
            return {"error": f"failed to analyze image: {str(e)}"}
    
    def write_file(self, path: str, content: str) -> Dict:
        """
        Write content to file (with safety checks).
        
        Args:
            path (str): target file path
            content (str): content to write
            
        Returns:
            Dict: operation result
        """
        try:
            # security check: only allow writing to safe directories
            abs_path = os.path.abspath(path)
            is_safe = any(abs_path.startswith(safe_dir) for safe_dir in self.safe_write_directories)
            
            if not is_safe:
                return {
                    "error": f"permission denied: can only write to {self.safe_write_directories}",
                    "path": path
                }
            
            # ensure directory exists
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            # write file
            with open(abs_path, 'w') as f:
                f.write(content)
            
            return {
                "tool": "write_file",
                "status": "success",
                "path": abs_path,
                "bytes_written": len(content)
            }
        except Exception as e:
            return {"error": f"failed to write file: {str(e)}"}
    
    def delete_file(self, path: str) -> Dict:
        """
        Delete file (with safety checks).
        
        Args:
            path (str): file to delete
            
        Returns:
            Dict: operation result
        """
        try:
            abs_path = os.path.abspath(path)
            is_safe = any(abs_path.startswith(safe_dir) for safe_dir in self.safe_write_directories)
            
            if not is_safe:
                return {"error": "permission denied: can only delete from safe directories"}
            
            if not os.path.exists(abs_path):
                return {"error": f"file not found: {path}"}
            
            os.remove(abs_path)
            
            return {
                "tool": "delete_file",
                "status": "success",
                "path": abs_path
            }
        except Exception as e:
            return {"error": f"failed to delete file: {str(e)}"}
    
    def web_search(self, query: str) -> Dict:
        """
        Search the web (using DuckDuckGo HTML scraping).
        
        Args:
            query (str): search query
            
        Returns:
            Dict: search results
        """
        try:
            # use duckduckgo html endpoint (no API key needed)
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return {"error": f"search failed with status {response.status_code}"}
            
            # simple parsing - extract first few results
            results = []
            lines = response.text.split('<a rel="nofollow" class="result__a"')
            
            for line in lines[1:6]:  # first 5 results
                try:
                    title = line.split('</a>')[0].split('>')[-1]
                    href = line.split('href="')[1].split('"')[0]
                    results.append({"title": title, "url": href})
                except:
                    continue
            
            return {
                "tool": "web_search",
                "status": "success",
                "query": query,
                "results": results
            }
        except Exception as e:
            return {"error": f"web search failed: {str(e)}"}
    
    def fetch_url(self, url: str) -> Dict:
        """
        Fetch content from URL.
        
        Args:
            url (str): URL to fetch
            
        Returns:
            Dict: page content
        """
        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            
            if response.status_code != 200:
                return {"error": f"fetch failed with status {response.status_code}"}
            
            # limit content size
            content = response.text[:50000]  # first 50KB
            
            return {
                "tool": "fetch_url",
                "status": "success",
                "url": url,
                "content": content,
                "content_type": response.headers.get('content-type', 'unknown')
            }
        except Exception as e:
            return {"error": f"failed to fetch URL: {str(e)}"}
    
    def execute_command(self, command: str, args: List[str] = None) -> Dict:
        """
        Execute system command (with strict whitelist).
        
        Args:
            command (str): command name
            args (List[str]): command arguments
            
        Returns:
            Dict: command output
        """
        try:
            if command not in self.command_whitelist:
                return {
                    "error": f"command not allowed. whitelist: {self.command_whitelist}",
                    "command": command
                }
            
            # build command
            cmd_list = [command]
            if args:
                cmd_list.extend(args)
            
            # execute with timeout
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=10,
                cwd="/app"
            )
            
            return {
                "tool": "execute_command",
                "status": "success",
                "command": " ".join(cmd_list),
                "stdout": result.stdout[:1000],  # limit output
                "stderr": result.stderr[:1000],
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "command timed out (10s limit)"}
        except Exception as e:
            return {"error": f"failed to execute command: {str(e)}"}

    def run_code(self, code: str, language: str = "python") -> Dict:
        """
        Execute code in multiple programming languages.
        
        Args:
            code (str): Code to execute.
            language (str): Programming language (python, javascript, go, rust, c, cpp).
            
        Returns:
            Dict: Execution result (stdout, stderr).
        """
        try:
            # Language configuration
            lang_config = {
                "python": {"ext": ".py", "cmd": ["python3"]},
                "javascript": {"ext": ".js", "cmd": ["node"]},
                "go": {"ext": ".go", "cmd": ["go", "run"]},
                "rust": {"ext": ".rs", "compile": True},
                "c": {"ext": ".c", "compile": True, "compiler": "gcc"},
                "cpp": {"ext": ".cpp", "compile": True, "compiler": "g++"}
            }
            
            if language not in lang_config:
                return {"error": f"unsupported language: {language}. Supported: {list(lang_config.keys())}"}
            
            config = lang_config[language]
            
            # Write code to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix=config["ext"], delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            # Compile if needed (Rust, C, C++)
            if config.get("compile"):
                output_path = temp_path.replace(config["ext"], "")
                
                if language == "rust":
                    compile_cmd = ["rustc", temp_path, "-o", output_path]
                else:  # C or C++
                    compile_cmd = [config["compiler"], temp_path, "-o", output_path]
                
                compile_result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if compile_result.returncode != 0:
                    os.remove(temp_path)
                    return {
                        "tool": "run_code",
                        "status": "compilation_error",
                        "language": language,
                        "stderr": compile_result.stderr,
                        "return_code": compile_result.returncode
                    }
                
                # Execute compiled binary
                exec_cmd = [output_path]
            else:
                # Execute directly (Python, JS, Go)
                exec_cmd = config["cmd"] + [temp_path]
            
            # Execute
            result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Clean up
            os.remove(temp_path)
            if config.get("compile") and os.path.exists(output_path):
                os.remove(output_path)
            
            return {
                "tool": "run_code",
                "status": "success",
                "language": language,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if config.get("compile") and 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
            return {"error": "code execution timed out (10s limit for execution, 30s for compilation)"}
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if config.get("compile") and 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
            return {"error": f"failed to run {language} code: {str(e)}"}
    
    def set_assignment(self, description: str, language: str = "python") -> Dict:
        """
        Set a coding assignment for the student (displayed in workspace).
        
        Args:
            description (str): Assignment description/instructions.
            language (str): Target programming language.
            
        Returns:
            Dict: Confirmation.
        """
        # Store in session state (will be accessed by app.py)
        return {
            "tool": "set_assignment",
            "status": "assignment_set",
            "description": description,
            "language": language,
            "message": "Assignment has been set in the coding workspace."
        }
