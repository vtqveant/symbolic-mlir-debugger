#!/usr/bin/env python3
"""
Minimal DAP (Debug Adapter Protocol) server for MLIR symbolic debugging.
Communicates via stdin/stdout using JSON-RPC.
"""

import json
import re
import sys
import threading
import traceback
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(__file__))
from interpreter.stepper import ExecutionStepper

# Set up logging to stderr
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class DAPRequest:
    """Represents a DAP request."""

    seq: int
    command: str
    arguments: Optional[Dict[str, Any]] = None


@dataclass
class DAPResponse:
    """Represents a DAP response."""

    seq: int
    request_seq: int
    success: bool
    command: str
    message: Optional[str] = None
    body: Optional[Dict[str, Any]] = None


@dataclass
class DAPEvent:
    """Represents a DAP event."""

    seq: int
    event: str
    body: Optional[Dict[str, Any]] = None


class MLIRDebugSession:
    """Manages debug session for an MLIR program using ExecutionStepper."""

    def __init__(self):
        self.breakpoints: Dict[str, List[int]] = {}  # uri -> line numbers
        self.stepper: Optional[ExecutionStepper] = None
        self.program_path: Optional[str] = None
        self.stopped = True  # Start in stopped state

    def launch(self, program: str, args: Optional[List[str]] = None) -> None:
        """Launch debug session for MLIR program."""
        self.program_path = program
        logger.info(f"Launching program: {program}")

        # Parse concrete inputs from args
        concrete_inputs = {}
        if args:
            # Simple parsing: assume args are key=value pairs
            for arg in args:
                if "=" in arg:
                    key, val = arg.split("=", 1)
                    try:
                        concrete_inputs[key] = int(val)
                    except ValueError:
                        logger.warning(f"Could not parse argument {arg} as integer")

        # Create ExecutionStepper
        try:
            self.stepper = ExecutionStepper(program, concrete_inputs)
            logger.info(f"Created stepper for function: {self.stepper.func_name}")

            # Apply any existing breakpoints for this program
            program_uri = f"file://{program}"
            if program_uri in self.breakpoints:
                lines = self.breakpoints[program_uri]
                self.stepper.set_breakpoints(lines)
                logger.info(f"Applied {len(lines)} breakpoints")

        except Exception as e:
            logger.error(f"Failed to create ExecutionStepper: {e}")
            raise

    def set_breakpoints(self, uri: str, lines: List[int]) -> List[Dict[str, Any]]:
        """Set breakpoints for a file."""
        self.breakpoints[uri] = lines
        logger.info(f"Set breakpoints for {uri}: {lines}")

        # If stepper is already created for this program, update it
        if self.stepper and self.program_path:
            program_uri = f"file://{self.program_path}"
            if uri == program_uri:
                self.stepper.set_breakpoints(lines)

        # Return breakpoint information
        return [
            {
                "verified": True,
                "line": line,
                "source": {"path": uri.replace("file://", "")},
            }
            for line in lines
        ]

    def continue_execution(self) -> bool:
        """Continue execution until next breakpoint or completion.

        Returns True if execution stopped at a breakpoint, False if terminated.
        """
        logger.info("Continuing execution")
        if not self.stepper:
            logger.warning("No stepper created yet")
            return False

        # Run until breakpoint
        location = self.stepper.run_until_breakpoint()

        # Check if execution terminated
        if location["line"] == 0 and location["operation"] is None:
            logger.info("Execution terminated")
            return False
        else:
            logger.info(f"Stopped at line {location['line']}")
            return True

    def step_next(self) -> bool:
        """Step to next operation.

        Returns True if execution continues, False if terminated.
        """
        logger.info("Stepping to next operation")
        if not self.stepper:
            logger.warning("No stepper created yet")
            return False

        location = self.stepper.step_next()

        # Check if execution terminated
        if location["line"] == 0 and location["operation"] is None:
            logger.info("Execution terminated")
            return False
        else:
            logger.info(f"Stopped at line {location['line']}")
            return True

    def get_threads(self) -> List[Dict[str, Any]]:
        """Get thread information."""
        return [{"id": 1, "name": "MLIR Execution Thread"}]

    def get_stack_trace(self, thread_id: int) -> List[Dict[str, Any]]:
        """Get stack trace for thread."""
        if not self.stepper:
            return [{"id": 1, "name": "main", "line": 1, "column": 1}]

        location = self.stepper.get_current_location()

        # Build descriptive frame name
        frame_name = self.stepper.func_name
        if location.get("block"):
            frame_name += f" [{location['block']}]"
            if location.get("operation"):
                frame_name += f" ({location['operation']})"

        # Create a stack frame with current location
        frame = {
            "id": 1,
            "name": frame_name,
            "line": location["line"],
            "column": 1,
            "source": {
                "path": self.program_path or "",
                "name": os.path.basename(self.program_path) if self.program_path else "unknown",
            },
        }

        # Add presentation hint for MLIR context
        frame["presentationHint"] = "normal"

        return [frame]

    def get_scopes(self, frame_id: int) -> List[Dict[str, Any]]:
        """Get scopes for a stack frame."""
        # For MLIR, we have a single scope "Variables" that includes all variables
        # We'll use reference ID 1 for the top-level variables
        return [
            {
                "name": "Variables",
                "variablesReference": 1,
                "expensive": False,
                "presentationHint": "locals",
            }
        ]

    def get_variables(self, variables_reference: int = 1) -> List[Dict[str, Any]]:
        """Get variables for the given reference (1 for top-level)."""
        if not self.stepper:
            return []

        variables = self.stepper.get_variables()
        result = []

        # Track variables reference IDs for nested structures
        # Simple implementation: memory regions get reference ID 1000+
        ref_id_counter = 1000

        for name, info in variables.items():
            # Skip internal debug markers
            if name.startswith("_") or info.get("_skip_dap", False):
                continue

            # Clean up display names
            display_name = name
            if info.get("_memory_region", False):
                # Extract memref name from "mem (memory)" format
                if " (" in name:
                    display_name = name.split(" (")[0] + " (memory)"
                else:
                    display_name = name.replace("_memory", " (memory)")
            elif info.get("_memory_cell", False):
                # Keep cell names as-is (e.g., "mem[0]")
                display_name = name

            var_entry = {
                "name": display_name,
                "value": info.get("value", "?"),
                "type": info.get("type", "unknown"),
            }

            # Add presentation hint if available
            if "presentationHint" in info:
                var_entry["presentationHint"] = info["presentationHint"]

            # Handle memory regions as expandable containers
            if info.get("_memory_region", False):
                var_entry["type"] = "memory_region"
                var_entry["value"] = info.get("value", "memory region")
                var_entry["presentationHint"] = "data"
                var_entry["variablesReference"] = ref_id_counter
                # Store mapping for later expansion
                if not hasattr(self, "_variable_refs"):
                    self._variable_refs = {}
                self._variable_refs[ref_id_counter] = {
                    "type": "memory_region",
                    "memref_name": info.get("_memref_name", name),
                }
                ref_id_counter += 1
            elif info.get("_memory_cell", False):
                # Memory cells are leaf nodes
                var_entry["variablesReference"] = 0
            elif info.get("type") == "path_conditions":
                # Path conditions expandable container
                var_entry["type"] = "path_conditions"
                var_entry["presentationHint"] = "data"
                var_entry["variablesReference"] = ref_id_counter
                if not hasattr(self, "_variable_refs"):
                    self._variable_refs = {}
                self._variable_refs[ref_id_counter] = {
                    "type": "path_conditions",
                    "constraints": info.get("constraints", []),
                }
                ref_id_counter += 1
            elif info.get("type") == "memory_map":
                # Memory map expandable container
                var_entry["type"] = "memory_map"
                var_entry["presentationHint"] = "data"
                var_entry["variablesReference"] = ref_id_counter
                if not hasattr(self, "_variable_refs"):
                    self._variable_refs = {}
                self._variable_refs[ref_id_counter] = {
                    "type": "memory_map",
                    "details": info.get("details", {}),
                }
                ref_id_counter += 1
            else:
                # Regular variables - check if they have nested structure
                # For now, assume leaf nodes
                var_entry["variablesReference"] = 0

            result.append(var_entry)

        return result

    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of execution state (for debugging)."""
        if not self.stepper:
            return {"stepper": None}
        return self.stepper.get_state_summary()

    def get_variable_children(self, variables_reference: int) -> List[Dict[str, Any]]:
        """Get child variables for a reference ID (e.g., memory region expansion)."""
        if not self.stepper or not hasattr(self, "_variable_refs"):
            return []

        ref_info = self._variable_refs.get(variables_reference)
        if not ref_info:
            return []

        if ref_info["type"] == "memory_region":
            # Return memory cells for this region
            memref_name = ref_info["memref_name"]
            variables = self.stepper.get_variables()
            result = []

            for name, info in variables.items():
                if info.get("_memory_cell", False) and name.startswith(memref_name + "["):
                    var_entry = {
                        "name": name,
                        "value": info.get("value", "?"),
                        "type": info.get("type", "unknown"),
                        "variablesReference": 0,
                    }
                    if "presentationHint" in info:
                        var_entry["presentationHint"] = info["presentationHint"]
                    result.append(var_entry)

            # Sort memory cells by name (indices) for consistent display
            result.sort(key=lambda x: x["name"])
            return result
        elif ref_info["type"] == "path_conditions":
            # Return individual constraints
            constraints = ref_info.get("constraints", [])
            result = []
            for i, constraint in enumerate(constraints):
                var_entry = {
                    "name": f"[{i}]",
                    "value": constraint,
                    "type": "constraint",
                    "variablesReference": 0,
                    "presentationHint": "text",
                }
                result.append(var_entry)
            return result
        elif ref_info["type"] == "memory_map":
            # Return memory regions with cell counts
            details = ref_info.get("details", {})
            result = []
            for memref_name, cell_count in details.items():
                var_entry = {
                    "name": memref_name,
                    "value": f"{cell_count} cells",
                    "type": "memory_region_summary",
                    "variablesReference": 0,  # Could make expandable but already have memory regions
                    "presentationHint": "data",
                }
                result.append(var_entry)
            # Sort memory regions by name for consistent display
            result.sort(key=lambda x: x["name"])
            return result

        return []

    def _parse_memory_reference(self, name: str) -> Optional[tuple]:
        """Parse memory cell reference like 'mem[0]' or 'mem[0][1]'.

        Returns (memref_name, indices_tuple) or None if not a memory reference.
        """
        # Pattern: identifier followed by [number] repeated 1 or more times
        pattern = r"^([a-zA-Z_][a-zA-Z0-9_]*)((?:\[\d+\])+)$"
        match = re.match(pattern, name)
        if not match:
            return None

        memref_name = match.group(1)
        indices_str = match.group(2)

        # Extract numbers from [number] patterns
        index_pattern = r"\[(\d+)\]"
        indices = [int(idx) for idx in re.findall(index_pattern, indices_str)]

        return (memref_name, tuple(indices))

    def _replace_memory_references(self, expression: str, variables: Dict[str, Any]) -> tuple:
        """Replace memory references in expression with placeholders.

        Returns (transformed_expression, placeholder_values_dict)
        """
        # Find all memory references in expression
        # Pattern: identifier[number][number]...
        pattern = r"([a-zA-Z_][a-zA-Z0-9_]*)((?:\[\d+\])+)"

        placeholder_values = {}
        transformed = expression

        # Find all matches
        for match in re.finditer(pattern, expression):
            full_match = match.group(0)  # e.g., "mem[0][1]"
            memref_name = match.group(1)  # e.g., "mem"
            indices_str = match.group(2)  # e.g., "[0][1]"

            # Check if this is a valid memory cell in variables
            # Memory cells are stored with names like "mem[0][1]"
            if full_match in variables:
                info = variables[full_match]
                if info.get("_memory_cell", False):
                    # Get concrete value
                    concrete_val = None
                    if "concrete_value" in info:
                        concrete_val = info["concrete_value"]
                    elif "value" in info:
                        val_str = str(info["value"])
                        try:
                            if val_str.lower() == "true":
                                concrete_val = True
                            elif val_str.lower() == "false":
                                concrete_val = False
                            else:
                                concrete_val = int(val_str)
                        except (ValueError, TypeError):
                            concrete_val = val_str

                    if concrete_val is not None:
                        # Create a valid Python identifier placeholder
                        # Replace [ and ] with _
                        placeholder = full_match.replace("[", "_").replace("]", "_")
                        # Ensure it starts with letter
                        if not placeholder[0].isalpha():
                            placeholder = "mem_" + placeholder

                        # Replace in expression (but need to be careful with overlapping replacements)
                        # We'll collect replacements and apply later
                        placeholder_values[full_match] = (placeholder, concrete_val)

        # Apply replacements (from longest to shortest to avoid partial replacements)
        sorted_replacements = sorted(
            placeholder_values.items(), key=lambda x: len(x[0]), reverse=True
        )
        for full_match, (placeholder, value) in sorted_replacements:
            transformed = transformed.replace(full_match, placeholder)

        # Build dict for eval
        eval_dict = {}
        for full_match, (placeholder, value) in placeholder_values.items():
            eval_dict[placeholder] = value

        return transformed, eval_dict

    def evaluate_expression(self, expression: str) -> Dict[str, Any]:
        """Evaluate an expression in current context.

        Supports simple arithmetic with current variable values.
        """
        if not self.stepper:
            return {"result": "?", "type": "error", "variablesReference": 0}

        # Get current variables and their concrete values
        variables = self.stepper.get_variables()

        # Build mapping of regular variable names to concrete values
        var_values = {}
        # Also build mapping for all memory cells (transformed names)
        memory_values_all = {}

        for name, info in variables.items():
            # Skip internal variables
            if name.startswith("_") or info.get("_skip_dap", False):
                continue

            # Handle memory cells separately
            if info.get("_memory_cell", False):
                # Get concrete value for memory cell
                concrete_val = None
                if "concrete_value" in info:
                    concrete_val = info["concrete_value"]
                elif "value" in info:
                    val_str = str(info["value"])
                    try:
                        if val_str.lower() == "true":
                            concrete_val = True
                        elif val_str.lower() == "false":
                            concrete_val = False
                        else:
                            concrete_val = int(val_str)
                    except (ValueError, TypeError):
                        concrete_val = val_str

                if concrete_val is not None:
                    # Create transformed name (valid Python identifier)
                    transformed_name = name.replace("[", "_").replace("]", "_")
                    # Ensure it starts with letter
                    if not transformed_name[0].isalpha():
                        transformed_name = "mem_" + transformed_name
                    memory_values_all[transformed_name] = concrete_val
                continue

            # Get concrete value if available for regular variables
            if "concrete_value" in info:
                var_values[name] = info["concrete_value"]
            elif "value" in info:
                # Try to parse value string
                val_str = str(info["value"])
                try:
                    if val_str.lower() == "true":
                        var_values[name] = True
                    elif val_str.lower() == "false":
                        var_values[name] = False
                    else:
                        var_values[name] = int(val_str)
                except (ValueError, TypeError):
                    # Keep as string
                    var_values[name] = val_str

        # Handle memory references in expression (transform bracket notation)
        transformed_expr, memory_values_expr = self._replace_memory_references(
            expression, variables
        )
        # Merge memory values from expression with all memory values
        memory_values = {**memory_values_all, **memory_values_expr}

        # Simple expression evaluation
        try:
            # Security: Only allow safe operations
            # Build a safe environment
            safe_dict = {
                "abs": abs,
                "min": min,
                "max": max,
                "sum": sum,
            }
            # Add regular variable values
            safe_dict.update(var_values)
            # Add memory cell values (as placeholders)
            safe_dict.update(memory_values)

            # Evaluate transformed expression
            # Note: Using eval is generally unsafe, but we control the environment
            # For production, use a proper expression parser
            result = eval(transformed_expr, {"__builtins__": {}}, safe_dict)

            return {
                "result": str(result),
                "type": type(result).__name__,
                "variablesReference": 0,
            }
        except Exception as e:
            return {
                "result": f"Error: {e}",
                "type": "error",
                "variablesReference": 0,
            }


class DAPServer:
    """DAP server implementation."""

    def __init__(self):
        self.session = MLIRDebugSession()
        self.seq_counter = 0
        self.running = True

    def next_seq(self) -> int:
        self.seq_counter += 1
        return self.seq_counter

    def read_message(self) -> Optional[Dict[str, Any]]:
        """Read a JSON-RPC message from stdin."""
        # DAP uses Content-Length header format
        line = sys.stdin.readline()
        if not line:
            return None

        if line.startswith("Content-Length:"):
            length = int(line.split(":")[1].strip())
            # Read blank line
            sys.stdin.readline()
            # Read JSON content
            content = sys.stdin.read(length)
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return None
        else:
            # Try to parse as raw JSON (for testing)
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                logger.error(f"Invalid message format: {line}")
                return None

    def write_message(self, message: Dict[str, Any]) -> None:
        """Write a JSON-RPC message to stdout."""
        content = json.dumps(message)
        sys.stdout.write(f"Content-Length: {len(content)}\r\n\r\n{content}")
        sys.stdout.flush()

    def send_response(
        self,
        request: DAPRequest,
        body: Optional[Dict[str, Any]] = None,
        success: bool = True,
        message: Optional[str] = None,
    ) -> None:
        """Send a response to a request."""
        response = {
            "seq": self.next_seq(),
            "type": "response",
            "request_seq": request.seq,
            "success": success,
            "command": request.command,
            "body": body,
        }
        if message and not success:
            response["message"] = message

        self.write_message(response)

    def send_event(self, event_name: str, body: Optional[Dict[str, Any]] = None) -> None:
        """Send an event."""
        event = {
            "seq": self.next_seq(),
            "type": "event",
            "event": event_name,
            "body": body or {},
        }
        self.write_message(event)

    def send_output(self, output: str, category: str = "console") -> None:
        """Send an output event to the debug console."""
        # Ensure output ends with newline for proper display
        if not output.endswith("\n"):
            output += "\n"
        self.send_event("output", {"category": category, "output": output})

    def handle_request(self, request_data: Dict[str, Any]) -> None:
        """Handle a DAP request."""
        request = None  # Initialize in case of early exception
        try:
            seq = request_data.get("seq", 0)
            command = request_data.get("command", "")
            arguments = request_data.get("arguments", {})

            request = DAPRequest(seq=seq, command=command, arguments=arguments)
            logger.info(f"Received request: {command}")

            # Handle different commands
            if command == "initialize":
                self.send_response(
                    request,
                    {
                        "supportsConfigurationDoneRequest": True,
                        "supportsFunctionBreakpoints": False,
                        "supportsConditionalBreakpoints": False,
                        "supportsHitConditionalBreakpoints": False,
                        "supportsEvaluateForHovers": True,
                        "exceptionBreakpointFilters": [],
                        "supportsStepBack": False,
                        "supportsSetVariable": False,
                        "supportsRestartFrame": False,
                        "supportsGotoTargetsRequest": False,
                        "supportsStepInTargetsRequest": False,
                        "supportsCompletionsRequest": False,
                        "supportsModulesRequest": False,
                        "additionalModuleColumns": [],
                        "supportedChecksumAlgorithms": [],
                        "supportsRestartRequest": False,
                        "supportsExceptionOptions": False,
                        "supportsValueFormattingOptions": False,
                        "supportsExceptionInfoRequest": False,
                        "supportTerminateDebuggee": False,
                        "supportsDelayedStackTraceLoading": False,
                        "supportsLoadedSourcesRequest": False,
                        "supportsLogPoints": False,
                        "supportsTerminateThreadsRequest": False,
                        "supportsSetExpression": False,
                        "supportsTerminateRequest": False,
                        "supportsDataBreakpoints": False,
                        "supportsReadMemoryRequest": False,
                        "supportsWriteMemoryRequest": False,
                        "supportsDisassembleRequest": False,
                        "supportsCancelRequest": False,
                        "supportsBreakpointLocationsRequest": False,
                        "supportsClipboardContext": False,
                        "supportsSteppingGranularity": False,
                        "supportsInstructionBreakpoints": False,
                        "supportsExceptionFilterOptions": False,
                        "supportsSingleThreadExecutionRequests": False,
                    },
                )
                self.send_event("initialized")
                self.send_output(
                    f"DAP server started (Python script: {os.path.abspath(sys.argv[0])})"
                )
                self.send_output(f"Python interpreter: {sys.executable}")
                self.send_output(f"Working directory: {os.getcwd()}")

            elif command == "launch":
                # Launch configuration
                program = arguments.get("program", "")
                args = arguments.get("args", [])
                logger.info(f"Launching program: {program} with args: {args}")
                abs_program = os.path.abspath(program)
                self.send_output(f"Debugging MLIR file: {abs_program}")
                self.send_output(f"Arguments: {args}")

                try:
                    self.session.launch(program, args)
                    self.send_response(request, {})
                    # Send stopped event at entry point
                    location = self.session.stepper.get_current_location()
                    body = {
                        "reason": "entry",
                        "threadId": 1,
                        "allThreadsStopped": True,
                    }
                    if location["line"] > 0:
                        body["line"] = location["line"]
                        body["column"] = 1
                        body["source"] = {
                            "path": location["file"],
                            "name": (
                                os.path.basename(location["file"])
                                if location["file"]
                                else "unknown"
                            ),
                        }
                    self.send_event("stopped", body)
                except Exception as e:
                    logger.error(f"Launch failed: {e}")
                    self.send_output(f"ERROR: Launch failed: {e}", category="stderr")
                    self.send_response(request, {}, success=False, message=f"Launch failed: {e}")

            elif command == "setBreakpoints":
                source = arguments.get("source", {})
                uri = source.get("path", "")
                if not uri.startswith("file://"):
                    uri = f"file://{uri}"
                lines = [bp.get("line", 0) for bp in arguments.get("breakpoints", [])]
                breakpoints = self.session.set_breakpoints(uri, lines)
                self.send_response(request, {"breakpoints": breakpoints})

            elif command == "configurationDone":
                self.send_response(request, {})

            elif command == "threads":
                threads = self.session.get_threads()
                self.send_response(request, {"threads": threads})

            elif command == "stackTrace":
                thread_id = arguments.get("threadId", 1)
                stack_frames = self.session.get_stack_trace(thread_id)
                self.send_response(request, {"stackFrames": stack_frames})

            elif command == "scopes":
                frame_id = arguments.get("frameId", 0)
                scopes = self.session.get_scopes(frame_id)
                self.send_response(request, {"scopes": scopes})

            elif command == "variables":
                variables_reference = arguments.get("variablesReference", 0)
                if variables_reference == 0 or variables_reference == 1:
                    # Top-level variables (reference 1 from scopes, 0 for backward compatibility)
                    variables = self.session.get_variables(variables_reference)
                else:
                    # Child variables for a reference
                    variables = self.session.get_variable_children(variables_reference)
                self.send_response(request, {"variables": variables})

            elif command == "evaluate":
                expression = arguments.get("expression", "")
                frame_id = arguments.get("frameId", 0)
                context = arguments.get("context", "hover")

                result = self.session.evaluate_expression(expression)
                self.send_response(request, result)

            elif command == "continue":
                stopped_at_breakpoint = self.session.continue_execution()
                self.send_response(request, {"allThreadsContinued": True})
                if stopped_at_breakpoint:
                    # Send stopped event for breakpoint
                    location = self.session.stepper.get_current_location()
                    body = {
                        "reason": "breakpoint",
                        "threadId": 1,
                        "allThreadsStopped": True,
                    }
                    if location["line"] > 0:
                        body["line"] = location["line"]
                        body["column"] = 1
                        body["source"] = {
                            "path": location["file"],
                            "name": (
                                os.path.basename(location["file"])
                                if location["file"]
                                else "unknown"
                            ),
                        }
                    self.send_event("stopped", body)
                else:
                    # Execution terminated
                    self.send_event("terminated", {})
                    self.send_event("exited", {"exitCode": 0})

            elif command == "next":
                still_running = self.session.step_next()
                self.send_response(request, {})
                if still_running:
                    # Send stopped event for step
                    location = self.session.stepper.get_current_location()
                    body = {
                        "reason": "step",
                        "threadId": 1,
                        "allThreadsStopped": True,
                    }
                    if location["line"] > 0:
                        body["line"] = location["line"]
                        body["column"] = 1
                        body["source"] = {
                            "path": location["file"],
                            "name": (
                                os.path.basename(location["file"])
                                if location["file"]
                                else "unknown"
                            ),
                        }
                    self.send_event("stopped", body)
                else:
                    # Execution terminated
                    self.send_event("terminated", {})
                    self.send_event("exited", {"exitCode": 0})

            elif command == "disconnect":
                self.send_response(request, {})
                self.running = False

            else:
                logger.warning(f"Unsupported command: {command}")
                self.send_response(
                    request,
                    {},
                    success=False,
                    message=f"Unsupported command: {command}",
                )

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            traceback.print_exc()
            if request is not None:
                self.send_response(request, {}, success=False, message=str(e))
            else:
                # Create a minimal request object for error response
                error_request = DAPRequest(seq=0, command="unknown", arguments={})
                self.send_response(error_request, {}, success=False, message=str(e))

    def run(self) -> None:
        """Main server loop."""
        logger.info("DAP server starting...")

        while self.running:
            try:
                message = self.read_message()
                if message is None:
                    break

                msg_type = message.get("type", "")

                if msg_type == "request":
                    self.handle_request(message)
                elif msg_type == "response":
                    logger.debug(f"Received response: {message}")
                elif msg_type == "event":
                    logger.debug(f"Received event: {message}")
                else:
                    logger.warning(f"Unknown message type: {msg_type}")

            except KeyboardInterrupt:
                logger.info("Server interrupted")
                break
            except Exception as e:
                logger.error(f"Error in server loop: {e}")
                traceback.print_exc()
                break

        logger.info("DAP server stopped")


def main():
    """Main entry point."""
    server = DAPServer()
    server.run()


if __name__ == "__main__":
    main()
