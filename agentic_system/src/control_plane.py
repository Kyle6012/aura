from typing import Dict, Any, List
from datetime import datetime
from .tools import ToolRegistry

class ControlPlane:
    """
    The central orchestration layer that manages tool execution, enforces safety rules,
    and maintains an audit log of all system actions.
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        """
        Initialize the ControlPlane.

        Args:
            tool_registry (ToolRegistry): The registry of available tools.
        """
        self.tools = tool_registry
        # define safety rules and allowed tools
        self.safety_rules = {
            "max_tools_per_request": 5,
            "allowed_tools": ["search_knowledge", "assess_understanding",
                              "update_learner_profile", "log_interaction",
                              "read_file", "list_directory",
                              "ingest_document", "analyze_image",
                              "write_file", "delete_file",
                              "web_search", "fetch_url", "execute_command", 
                              "run_code", "set_assignment"]
        }
        self.execution_log = []

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a planned action after validating it against safety rules.

        Args:
            plan (Dict[str, Any]): The action plan containing 'action' and 'parameters'.

        Returns:
            Dict[str, Any]: The result of the execution, including success status and metadata.
        """
        # validate the request against safety rules
        if not self._validate_request(plan):
            return {"error": "safety validation failed", "plan": plan}

        action = plan.get("action")
        params = plan.get("parameters", {})
        
        # route the action to the appropriate tool and execute
        result = self._route_and_execute(action, params)

        # log the execution details
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "plan": plan,
            "result": result
        })

        return {
            "success": True,
            "action": action,
            "result": result,
            "metadata": {
                "execution_count": len(self.execution_log),
                "safety_checks_passed": True
            }
        }

    def _validate_request(self, plan: Dict) -> bool:
        """
        Validate the incoming request against security policies.
        
        Args:
            plan (Dict): execution plan
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Handle dictionary plans
        if isinstance(plan, dict):
            action = plan.get("action")
        else:
            # If plan is a string, treat it as action name
            action = str(plan)
        
        # check if action is allowed (check both full name and base name)
        if action and action not in self.safety_rules["allowed_tools"]:
            # Try extracting just the tool name if it has parameters
            base_action = action.split('(')[0].strip() if '(' in action else action
            if base_action not in self.safety_rules["allowed_tools"]:
                print(f"safety violation: tool '{action}' not in allowed list")
                return False
        
        # check max tools (only for dict plans)
        if isinstance(plan, dict) and len(plan.get("parameters", {})) > 10:
            print("safety violation: too many parameters")
            return False
        
        return True

    def _route_and_execute(self, action: str, params: Dict) -> Any:
        """
        Route the validated action to the specific tool implementation.

        Args:
            action (str): The name of the action.
            params (Dict): Parameters for the action.

        Returns:
            Any: The result from the tool execution.
        """
        # map action names to tool methods
        tool_map = {
            "search_knowledge": self.tools.search_knowledge,
            "assess_understanding": self.tools.assess_understanding,
            "update_learner_profile": self.tools.update_learner_profile,
            "log_interaction": self.tools.log_interaction,
            "read_file": self.tools.read_file,
            "list_directory": self.tools.list_directory,
            "ingest_document": self.tools.ingest_document,
            "analyze_image": self.tools.analyze_image,
            "write_file": self.tools.write_file,
            "delete_file": self.tools.delete_file,
            "web_search": self.tools.web_search,
            "fetch_url": self.tools.fetch_url,
            "execute_command": self.tools.execute_command,
            "run_code": self.tools.run_code,
            "set_assignment": self.tools.set_assignment
        }
        
        tool_func = tool_map.get(action)
        if tool_func:
            return tool_func(**params)
            
        return {"error": f"unknown action: {action}"}
