"""DAP Protocol Constants"""

# Protocol commands
COMMAND_INITIALIZE = "initialize"
COMMAND_LAUNCH = "launch"
COMMAND_DISCONNECT = "disconnect"
COMMAND_SET_BREAKPOINTS = "setBreakpoints"
COMMAND_CONFIGURATION_DONE = "configurationDone"
COMMAND_CONTINUE = "continue"
COMMAND_NEXT = "next"
COMMAND_STEP_IN = "stepIn"
COMMAND_STEP_OUT = "stepOut"
COMMAND_STEPPED = "stepped"

# Symbolic debugging commands
COMMAND_SYMBOLIC_SET_MODE = "symbolic/setMode"
COMMAND_SYMBOLIC_EVALUATE = "symbolic/evaluate"
COMMAND_SYMBOLIC_EXPLORE_PATHS = "symbolic/explorePaths"
COMMAND_SYMBOLIC_GET_CONSTRAINTS = "symbolic/getConstraints"

# Protocol events
EVENT_INITIALIZED = "initialized"
EVENT_TERMINATED = "terminated"
EVENT_EXECEPTION = "exception"
EVENT_BREAKPOINT = "breakpoint"
EVENT_OUTPUT = "output"
EVENT_MODULE = "module"
EVENT_THREAD = "thread"
EVENT_PROCESS = "process"

# Protocol responses
RESPONSE_SUCCESS = 1
RESPONSE_ERROR = 2

# Sequence type
SEQUENCE_TYPE_REQUEST = 0
SEQUENCE_TYPE_RESPONSE = 1
SEQUENCE_TYPE_EVENT = 2

# Protocol error codes
ERROR_CODE_OK = 0
ERROR_CODE_CANCELED = 128
ERROR_CODE_NOT_SUPPORTED = 261
ERROR_CODE_FAILED = 262

# Capabilities
SUPPORTS_STEP_INTO_TARGETS = "supportsStepIntoTargets"
SUPPORTS_TERMINATE_DEBUGGEE = "supportsTerminateDebuggee"

# Request types
REQUEST_START = "start"
REQUEST_CONFIGURATION_DONE = "configurationDone"
REQUEST_COMPILED_SOURCE = "compiledSource"
REQUEST_SET_VARIABLE = "setVariable"
REQUEST_SET_EXCEPTION_BREAKPOINTS = "setExceptionBreakpoints"
REQUEST_SET_FUNCTION_BREAKPOINTS = "setFunctionBreakpoints"
REQUEST_DATA_BREAKPOINTS = "setDataBreakpoints"
REQUEST_SOURCE = "source"
REQUEST_THREADS = "threads"
REQUEST_STACKTRACE = "stackTrace"
REQUEST_SCOPES = "scopes"
REQUEST_VARIABLES = "variables"
REQUEST_EVALUATE = "evaluate"
REQUEST_STEP_INTO = "stepInto"
REQUEST_STEP_OVER = "stepOver"
REQUEST_STEP_OUT = "stepOut"
REQUEST_CONTINUE = "continue"
REQUEST_GOTO = "goto"
REQUEST_GOTO_TARGETS = "gotoTargets"
REQUEST_SET_FUNCTION_BREAKPOINTS = "setFunctionBreakpoints"
REQUEST_SET_EXCEPTION_BREAKPOINTS = "setExceptionBreakpoints"
REQUEST_COMPILED_SOURCE = "compiledSource"

# Response types
RESPONSE_CONTINUE = "continue"
RESPONSE_CONTINUE = "continue"
RESPONSE_GOTO = "goto"

# Path segment types
PATH_SEGMENT_MODULE = "module"
PATH_SEGMENT_SOURCE = "source"

# Stack frame types
FRAME_TYPE_UNKNOWN = 0
FRAME_TYPE_CALL = 1
FRAME_TYPE_RETURN = 2

# Stack frame arguments
FRAME_ID_PREFIX = "frame."

# Variable types
VAR_TYPE_UNKNOWN = 0
VAR_TYPE_VALUE = 1
VAR_TYPE_CONSTRAINT = 2

# Variable presentation hints
PRESENTATION_HINT_NORMAL = "normal"
PRESENTATION_HINT_HIGHLIGHT = "highlight"
PRESENTATION_HINT_SUBTLE = "subtle"

# View containers
VIEW_CONTAINER_NORMAL = "normal"
VIEW_CONTAINER_ARROW = "arrow"
VIEW_CONTAINER_TREE = "tree"
VIEW_CONTAINER_ARRAY = "array"
VIEW_CONTAINER_STRING = "string"

# Status types
STATUS_IDLE = 0
STATUS_RUNNING = 1
STATUS_PAUSED = 2
STATUS_TERMINATED = 3

# Memory reference types
MEMORY_READ = 0
MEMORY_WRITE = 1

# Source types
SOURCE_DEFAULT = 0
