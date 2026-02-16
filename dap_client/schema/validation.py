"""JSON schema validation for test scripts"""

import json
import logging
from typing import Optional, Dict, Any, List
from jsonschema import validate, ValidationError
import pkgutil
import os
from protocol import DAPRequest, DAPResponse

logger = logging.getLogger(__name__)

# Load schema from bundled file
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "test_script_schema.json")

_test_script_schema = None


def load_test_script_schema() -> Dict[str, Any]:
    """Load test script JSON schema"""
    global _test_script_schema
    if _test_script_schema is None:
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, 'r') as f:
                _test_script_schema = json.load(f)
        else:
            # Return default schema if file not found
            _test_script_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "DAP Test Script",
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the test script"
                    },
                    "program": {
                        "type": "string",
                        "description": "Path to the MLIR program to debug"
                    },
                    "session": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "enum": [
                                        "initialize", "launch", "setBreakpoints",
                                        "configurationDone", "continue", "disconnect"
                                    ]
                                },
                                "arguments": {
                                    "type": "object"
                                },
                                "expect": {
                                    "type": "object",
                                    "properties": {
                                        "success": {
                                            "type": "boolean"
                                        }
                                    }
                                }
                            },
                            "required": ["command"]
                        }
                    }
                },
                "required": ["name", "program", "session"]
            }
    return _test_script_schema


def validate_test_script(test_script: Dict[str, Any]) -> Optional[ValidationError]:
    """Validate a test script against schema
    
    Args:
        test_script: Test script data to validate
        
    Returns:
        ValidationError if invalid, None if valid
    """
    schema = load_test_script_schema()
    try:
        validate(instance=test_script, schema=schema)
        return None
    except ValidationError as e:
        logger.error(f"Test script validation error: {e}")
        return e


def load_test_script(filepath: str) -> Dict[str, Any]:
    """Load and validate test script from file
    
    Args:
        filepath: Path to test script file
        
    Returns:
        Loaded test script data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If test script is invalid
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Test script not found: {filepath}")
    
    with open(filepath, 'r') as f:
        test_script = json.load(f)
    
    error = validate_test_script(test_script)
    if error:
        raise error
    
    return test_script


class TestScript:
    """Test script class with validation"""
    
    def __init__(self, data: Dict[str, Any], filepath: Optional[str] = None):
        """Initialize test script from data
        
        Args:
            data: Test script data
            filepath: Optional path to the test script file
        """
        error = validate_test_script(data)
        if error:
            raise error
        
        self.data = data
        self.filepath = filepath
        self.name = data.get("name", "Unnamed Test")
        self.program = data.get("program", "")
        self.session_steps = data.get("session", [])
    
    def get_session_step(self, index: int) -> Optional[Dict[str, Any]]:
        """Get session step at index
        
        Args:
            index: Step index
            
        Returns:
            Session step data or None if index out of bounds
        """
        if 0 <= index < len(self.session_steps):
            return self.session_steps[index]
        return None
    
    def get_next_session_step(self) -> Optional[Dict[str, Any]]:
        """Get the next unexecuted session step
        
        Returns:
            Next session step or None if no more steps
        """
        for step in self.session_steps:
            if step.get("executed", False) is False:
                return step
        return None
    
    def mark_step_executed(self, step_index: int) -> bool:
        """Mark a session step as executed
        
        Args:
            step_index: Step index to mark as executed
            
        Returns:
            True if step was found and marked, False otherwise
        """
        step = self.get_session_step(step_index)
        if step:
            step["executed"] = True
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Get test script as dictionary
        
        Returns:
            Test script data
        """
        return self.data
    
    def __str__(self) -> str:
        """Get string representation
        
        Returns:
            String representation of test script
        """
        return f"TestScript(name={self.name}, program={self.program}, steps={len(self.session_steps)})"
