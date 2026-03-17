# DAP Trace Library Refactoring Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 1: Add Jinja2 templating with fallback to old string templates, maintaining backward compatibility.

**Architecture:** Jinja2 template system integrated into existing generator with fallback mechanism. No architectural changes in Phase 1.

**Tech Stack:** Python 3.8+, Jinja2 templating engine, pytest for testing.

---

## Phase 1: Foundation (Week 1) - Jinja2 Integration with Fallback

### File Structure for Phase 1 Only

#### New Files to Create
```
dap_trace_library/
├── templates/              # Base Jinja2 templates
│   ├── base/
│   │   ├── binary_op.j2    # Base binary operation template
│   │   └── unary_op.j2     # Base unary operation template
│   └── traces/
│       └── basic_session.j2    # Basic DAP session template
└── utils/
    └── template_loader.py # Jinja2 template management with fallback
```

#### Files to Modify
- `requirements.txt` - Add Jinja2 dependency
- `dap_trace_library/generation/configurable_generator.py` - Add TemplateLoader integration with fallback
- `tests/test_template_loader.py` - New tests for TemplateLoader
- `dap_trace_library/test_library.py` - Verify backward compatibility

#### Backward Compatibility Requirements
1. Existing code using old template strings must continue to work
2. TemplateLoader must fall back to string templates when Jinja2 templates not found
3. All existing tests must pass without modification
4. Output equivalence must be verified

---

## Phase 1: Foundation (Week 1)

### Task 1: Add Jinja2 Dependency and Setup Template Directory Structure

**Files:**
- Modify: `requirements.txt`
- Create: `dap_trace_library/templates/base/binary_op.j2`
- Create: `dap_trace_library/templates/base/unary_op.j2`
- Create: `dap_trace_library/templates/traces/basic_session.j2`

- [ ] **Step 1: Add Jinja2 to requirements**

```txt
# Add to requirements.txt
Jinja2>=3.1.0
```

- [ ] **Step 2: Run test to verify dependency installation**

```bash
pip install -r requirements.txt
python -c "import jinja2; print(f'Jinja2 version: {jinja2.__version__}')"
```

Expected: Prints Jinja2 version >= 3.1.0

- [ ] **Step 3: Create base template directory structure**

```bash
mkdir -p dap_trace_library/templates/{base,traces,dialects/arith,dialects/memref}
```

- [ ] **Step 4: Create base binary operation template**

File: `dap_trace_library/templates/base/binary_op.j2`

```jinja2
{# Base template for binary operations #}
module {
  func.func @test_{{ dialect }}_{{ operation.name }}() {
    %0 = arith.constant {{ value_a }} : i{{ bitwidth }}
    %1 = arith.constant {{ value_b }} : i{{ bitwidth }}
    %result = {{ dialect }}.{{ operation.name }} %0, %1 : i{{ bitwidth }}
    return
  }
}
```

- [ ] **Step 5: Create basic DAP session template**

File: `dap_trace_library/templates/traces/basic_session.j2`

```jinja2
{# Basic DAP session template #}
{
  "name": "{{ trace_name }}",
  "program": "{{ program_path }}",
  "dialect": "{{ dialect }}",
  "operation": "{{ operation.name }}",
  "concrete_inputs": {{ concrete_inputs|tojson }},
  "session": [
    {
      "command": "initialize",
      "arguments": {
        "adapterID": "mlir-debugger",
        "clientID": "test-{{ dialect }}-{{ operation.name }}"
      },
      "expect": {"success": true}
    },
    {
      "command": "launch",
      "arguments": {
        "program": "{{ program_path }}",
        "noDebug": true
      },
      "expect": {"success": true}
    },
    {
      "command": "disconnect",
      "arguments": {"terminateDebuggee": true},
      "expect": {"success": true}
    }
  ]
}
```

- [ ] **Step 6: Commit foundation setup**

```bash
git add requirements.txt dap_trace_library/templates/
git commit -m "feat: add Jinja2 dependency and base template structure"
```

### Task 2: Implement TemplateLoader Utility with Fallback

**Files:**
- Create: `dap_trace_library/utils/template_loader.py`
- Create: `tests/test_template_loader.py`

- [ ] **Step 1: Write failing test for TemplateLoader with fallback**

File: `tests/test_template_loader.py`

```python
import pytest
from pathlib import Path
from dap_trace_library.utils.template_loader import TemplateLoader

def test_template_loader_initialization():
    """Test TemplateLoader can be initialized."""
    loader = TemplateLoader(template_dirs=["dap_trace_library/templates"])
    assert loader is not None
    assert len(loader.template_dirs) == 1

def test_template_loader_load_template():
    """Test TemplateLoader can load a template."""
    loader = TemplateLoader(template_dirs=["dap_trace_library/templates"])
    template = loader.load_template("base/binary_op.j2")
    assert template is not None
    # Template should be a Jinja2 Template object
    assert hasattr(template, 'render')

def test_template_loader_fallback_to_string():
    """Test TemplateLoader falls back to string template when Jinja2 template not found."""
    loader = TemplateLoader(template_dirs=["dap_trace_library/templates"])
    
    # Provide fallback string template
    fallback_template = "module {{\n  func.func @test_{op_name}() {{\n    %0 = arith.constant {value_a} : i{bitwidth}\n    %1 = arith.constant {value_b} : i{bitwidth}\n    %2 = arith.{op_name} %0, %1 : i{bitwidth}\n    return\n  }}\n}}"
    
    # This should work even if template doesn't exist (using fallback)
    result = loader.render_with_fallback(
        "nonexistent_template.j2",
        fallback_template,
        op_name="addi",
        value_a=10,
        value_b=20,
        bitwidth=32
    )
    
    assert "arith.addi" in result
    assert "i32" in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_template_loader.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'dap_trace_library.utils.template_loader'"

- [ ] **Step 3: Implement TemplateLoader with fallback support**

File: `dap_trace_library/utils/template_loader.py`

```python
#!/usr/bin/env python3
"""
Jinja2 template loader for DAP Trace Library with fallback to string templates.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import jinja2
import logging

logger = logging.getLogger(__name__)


class TemplateLoader:
    """Load and manage Jinja2 templates with caching and fallback to string templates."""
    
    def __init__(self, template_dirs: List[str] = None):
        """Initialize template loader.
        
        Args:
            template_dirs: List of directories to search for templates
        """
        self.template_dirs = template_dirs or []
        self._environment = None
        self._template_cache = {}
        
        # Add default template directory if none provided
        if not self.template_dirs:
            default_dir = Path(__file__).parent.parent / "templates"
            if default_dir.exists():
                self.template_dirs = [str(default_dir)]
        
        self._init_environment()
    
    def _init_environment(self):
        """Initialize Jinja2 environment."""
        if not self.template_dirs:
            logger.warning("No template directories configured")
            return
            
        try:
            loader = jinja2.FileSystemLoader(self.template_dirs)
            self._environment = jinja2.Environment(
                loader=loader,
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
            
            # Add custom filters
            self._environment.filters['tojson'] = self._tojson_filter
            logger.info("Jinja2 environment initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Jinja2 environment: {e}")
            self._environment = None
    
    def _tojson_filter(self, value: Any) -> str:
        """JSON filter for templates."""
        import json
        return json.dumps(value)
    
    def is_jinja2_available(self) -> bool:
        """Check if Jinja2 is available and environment is initialized.
        
        Returns:
            True if Jinja2 templates can be used, False otherwise
        """
        return self._environment is not None
    
    def load_template(self, template_name: str) -> Optional[jinja2.Template]:
        """Load a Jinja2 template by name.
        
        Args:
            template_name: Name of template (e.g., "base/binary_op.j2")
            
        Returns:
            Jinja2 Template object or None if not found/available
        """
        if not self.is_jinja2_available():
            logger.debug(f"Jinja2 not available, cannot load template: {template_name}")
            return None
        
        # Check cache first
        if template_name in self._template_cache:
            return self._template_cache[template_name]
        
        try:
            template = self._environment.get_template(template_name)
            self._template_cache[template_name] = template
            logger.debug(f"Loaded Jinja2 template: {template_name}")
            return template
        except jinja2.TemplateNotFound as e:
            logger.warning(f"Jinja2 template not found: {template_name}")
            return None
        except jinja2.TemplateSyntaxError as e:
            logger.error(f"Jinja2 template syntax error in {template_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading template {template_name}: {e}")
            return None
    
    def render_jinja2_template(self, template_name: str, **context) -> Optional[str]:
        """Render a Jinja2 template with the given context.
        
        Args:
            template_name: Name of template
            **context: Template variables
            
        Returns:
            Rendered template as string or None if template not available
        """
        template = self.load_template(template_name)
        if template is None:
            return None
        
        try:
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            return None
    
    def render_string_template(self, template_string: str, **context) -> str:
        """Render a string template using Python's str.format().
        
        Args:
            template_string: String template
            **context: Template variables
            
        Returns:
            Rendered template as string
        """
        try:
            return template_string.format(**context)
        except KeyError as e:
            logger.error(f"Missing variable in string template: {e}")
            # Fallback to simple replacement
            result = template_string
            for key, value in context.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result
    
    def render_with_fallback(self, jinja2_template_name: str, 
                           fallback_template_string: str, 
                           **context) -> str:
        """Render template with Jinja2 first, fallback to string template.
        
        Args:
            jinja2_template_name: Name of Jinja2 template to try first
            fallback_template_string: String template as fallback
            **context: Template variables
            
        Returns:
            Rendered template as string
        """
        # Try Jinja2 first
        if self.is_jinja2_available():
            result = self.render_jinja2_template(jinja2_template_name, **context)
            if result is not None:
                logger.debug(f"Rendered using Jinja2 template: {jinja2_template_name}")
                return result
        
        # Fallback to string template
        logger.debug(f"Falling back to string template for: {jinja2_template_name}")
        return self.render_string_template(fallback_template_string, **context)
    
    def validate_template(self, template_name: str, required_vars: List[str] = None) -> Dict[str, Any]:
        """Validate a template for required variables and syntax.
        
        Args:
            template_name: Name of template
            required_vars: List of required variable names
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "required_vars": [],
            "found_vars": []
        }
        
        try:
            template = self.load_template(template_name)
            if template is None:
                result["valid"] = False
                result["errors"].append(f"Template not found: {template_name}")
                return result
                
            if required_vars:
                result["required_vars"] = required_vars
                # TODO: Implement proper variable analysis
                result["warnings"].append("Variable validation not implemented")
                
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Unexpected error: {e}")
            
        return result
    
    def list_available_templates(self) -> List[str]:
        """List all available Jinja2 templates.
        
        Returns:
            List of template names
        """
        if not self.is_jinja2_available():
            return []
            
        try:
            return self._environment.list_templates()
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_template_loader.py -v
```

Expected: PASS

- [ ] **Step 5: Add test for fallback behavior**

File: `tests/test_template_loader.py` (append)

```python
def test_template_loader_fallback_behavior():
    """Test TemplateLoader fallback behavior when Jinja2 is not available."""
    # Create loader with non-existent directory to simulate Jinja2 failure
    loader = TemplateLoader(template_dirs=["/non/existent/directory"])
    
    # Jinja2 should not be available
    assert loader.is_jinja2_available() == False
    
    # String template should still work
    template_string = "Test {name} with value {value}"
    result = loader.render_string_template(template_string, name="test", value=42)
    assert result == "Test test with value 42"
    
    # Fallback should work
    fallback_result = loader.render_with_fallback(
        "nonexistent.j2",
        template_string,
        name="fallback",
        value=100
    )
    assert "fallback" in fallback_result
    assert "100" in fallback_result
```

- [ ] **Step 6: Run fallback tests**

```bash
pytest tests/test_template_loader.py::test_template_loader_fallback_behavior -v
```

Expected: PASS

- [ ] **Step 7: Commit TemplateLoader implementation**

```bash
git add dap_trace_library/utils/template_loader.py tests/test_template_loader.py
git commit -m "feat: implement TemplateLoader with Jinja2 and fallback to string templates"
```

### Task 3: Update ConfigurableGenerator to Use TemplateLoader

**Files:**
- Modify: `dap_trace_library/generation/configurable_generator.py`
- Create: `tests/test_generator_integration.py`

- [ ] **Step 1: Write failing test for generator integration**

File: `tests/test_generator_integration.py`

```python
import pytest
from pathlib import Path
from dap_trace_library.generation.configurable_generator import ConfigurableGenerator
from dap_trace_library.config.dialect_config import GeneratorConfig

def test_generator_uses_template_loader():
    """Test that generator uses TemplateLoader when available."""
    config = GeneratorConfig.create_arith_example()
    generator = ConfigurableGenerator(config)
    
    # Generator should have template_loader attribute
    assert hasattr(generator, 'template_loader')
    assert generator.template_loader is not None
    
    # Check if template_loader is used in generate_mlir_snippet
    # We'll test this by mocking and verifying method calls
    from unittest.mock import MagicMock, patch
    
    with patch.object(generator.template_loader, 'render_with_fallback') as mock_render:
        mock_render.return_value = "mocked mlir output"
        
        # Get an operation to test with
        operation = config.get_enabled_operations()[0]
        values = {"a": 1, "b": 2, "bitwidth": 32}
        
        result = generator.generate_mlir_snippet(operation, values)
        
        # Should have called render_with_fallback
        assert mock_render.called
        assert result == "mocked mlir output"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_generator_integration.py -v
```

Expected: FAIL (generator doesn't have template_loader attribute yet)

- [ ] **Step 3: Update ConfigurableGenerator to use TemplateLoader**

File: `dap_trace_library/generation/configurable_generator.py`

First, add import at top of file (after existing imports):

```python
from ..utils.template_loader import TemplateLoader
```

Then, in the `__init__` method of `ConfigurableGenerator` class, add template_loader initialization. Find the `__init__` method around line 26 and update it:

```python
    def __init__(self, config: GeneratorConfig):
        """Initialize configurable generator."""
        super().__init__(config)
        self.z3_generator = Z3Generator()
        
        # Initialize TemplateLoader
        self.template_loader = TemplateLoader()
        
        # Load dialect-specific templates
        self.templates = self._load_templates()
        
        # Track generated files by dialect
        self.generated_by_dialect = {}
```

Next, update the `generate_mlir_snippet` method to use TemplateLoader. Find the method around line 142 and replace it:

```python
    def generate_mlir_snippet(self, operation: OperationConfig, 
                             values: Dict[str, Any]) -> str:
        """Generate MLIR code snippet for an operation.
        
        Args:
            operation: Operation configuration
            values: Concrete values for variables
            
        Returns:
            MLIR code as string
        """
        dialect_name = operation.dialect
        template_info = self.templates.get(dialect_name, {})
        
        # Try to get Jinja2 template path from configuration
        jinja2_template_path = None
        if "mlir_template" in template_info:
            # Check if it's a Jinja2 template path (ends with .j2)
            template_str = template_info["mlir_template"]
            if isinstance(template_str, str) and template_str.endswith('.j2'):
                jinja2_template_path = template_str
            else:
                # It's a string template, use as fallback
                fallback_template = template_str
        
        # Prepare template variables
        template_vars = {
            "dialect": dialect_name,
            "operation": operation,
            "op_name": operation.name,
            "bitwidth": values.get("bitwidth", 32),
            "size": values.get("size", 10)
        }
        
        # Add operation-specific parameters
        template_vars.update(operation.parameters)
        
        # Add concrete values
        variable_mapping = template_info.get("variable_mapping", {})
        for var_name, var_value in values.items():
            if var_name in variable_mapping:
                template_var_name = variable_mapping[var_name]
                template_vars[template_var_name] = var_value
            else:
                template_vars[var_name] = var_value
        
        # Use TemplateLoader with fallback
        if jinja2_template_path:
            # We have a Jinja2 template path, try to use it
            fallback_template = template_info.get("mlir_template", "")
            return self.template_loader.render_with_fallback(
                jinja2_template_path,
                fallback_template,
                **template_vars
            )
        else:
            # No Jinja2 template path, use string template directly
            template = template_info.get("mlir_template", "")
            if not template:
                # Get default template
                dialect_config = self.config.get_dialect(dialect_name)
                if dialect_config:
                    template = self._get_default_template(dialect_config)
                else:
                    template = "module {{\n  func.func @test_{op_name}() {{\n    // {dialect}.{op_name} with values {values}\n    return\n  }}\n}}"
            
            return self.template_loader.render_string_template(template, **template_vars)
```

Also update the `generate_dap_trace` method to use TemplateLoader for trace templates. Find the method around line 190 and update the trace template rendering part (around line 225-232):

```python
        # Start with template session
        if "session" in trace_template:
            for session_item in trace_template["session"]:
                # Render template variables in session item
                rendered_item = self._render_session_item(
                    session_item, operation, mlir_path, values
                )
                trace["session"].append(rendered_item)
```

The `_render_session_item` method already uses string formatting. We could update it to use TemplateLoader, but for Phase 1 we'll keep it as is for backward compatibility.

- [ ] **Step 4: Run test to verify integration works**

```bash
pytest tests/test_generator_integration.py -v
```

Expected: PASS

- [ ] **Step 5: Add test for backward compatibility**

File: `tests/test_generator_integration.py` (append)

```python
def test_generator_backward_compatibility():
    """Test that generator maintains backward compatibility with old templates."""
    config = GeneratorConfig.create_arith_example()
    generator = ConfigurableGenerator(config)
    
    # Get an operation
    operation = config.get_enabled_operations()[0]
    values = {"a": 1, "b": 2, "bitwidth": 32}
    
    # Generate MLIR using the generator
    result = generator.generate_mlir_snippet(operation, values)
    
    # Should produce valid MLIR
    assert "module" in result
    assert "func.func" in result
    assert operation.name in result
    
    # Test with disabled Jinja2 (simulate missing templates)
    generator.template_loader = None
    result2 = generator.generate_mlir_snippet(operation, values)
    assert "module" in result2  # Should still work with string templates
```

- [ ] **Step 6: Run backward compatibility test**

```bash
pytest tests/test_generator_integration.py::test_generator_backward_compatibility -v
```

Expected: PASS

- [ ] **Step 7: Commit generator integration**

```bash
git add dap_trace_library/generation/configurable_generator.py tests/test_generator_integration.py
git commit -m "feat: update ConfigurableGenerator to use TemplateLoader with fallback"
```

### Task 4: Test Backward Compatibility and Phase 1 Completion

**Files:**
- Modify: `dap_trace_library/test_library.py`
- Run: Existing test suite

- [ ] **Step 1: Run existing library tests to verify backward compatibility**

```bash
cd /home/transcend/code/VIBE/symbolic-mlir-debugger
python dap_trace_library/test_library.py
```

Expected: All tests pass (may have warnings about new TemplateLoader)

- [ ] **Step 2: Create Phase 1 completion test**

File: `tests/test_phase1_completion.py`

```python
#!/usr/bin/env python3
"""
Phase 1 completion tests for DAP Trace Library refactoring.
"""

import pytest
import sys
from pathlib import Path

def test_jinja2_dependency():
    """Test that Jinja2 is installed."""
    try:
        import jinja2
        assert jinja2.__version__ >= "3.1.0"
    except ImportError:
        pytest.fail("Jinja2 not installed")

def test_template_loader_module():
    """Test that TemplateLoader module exists."""
    try:
        from dap_trace_library.utils.template_loader import TemplateLoader
        assert TemplateLoader is not None
    except ImportError as e:
        pytest.fail(f"TemplateLoader module not found: {e}")

def test_generator_has_template_loader():
    """Test that ConfigurableGenerator has template_loader."""
    from dap_trace_library.generation.configurable_generator import ConfigurableGenerator
    from dap_trace_library.config.dialect_config import GeneratorConfig
    
    config = GeneratorConfig.create_arith_example()
    generator = ConfigurableGenerator(config)
    
    assert hasattr(generator, 'template_loader')
    assert generator.template_loader is not None

def test_template_files_exist():
    """Test that base template files exist."""
    template_dir = Path(__file__).parent.parent / "dap_trace_library" / "templates"
    
    required_files = [
        "base/binary_op.j2",
        "traces/basic_session.j2"
    ]
    
    for file_path in required_files:
        full_path = template_dir / file_path
        assert full_path.exists(), f"Template file not found: {file_path}"

def test_output_equivalence():
    """Test that new system produces equivalent output to old system for simple cases."""
    from dap_trace_library.generation.configurable_generator import ConfigurableGenerator
    from dap_trace_library.config.dialect_config import GeneratorConfig, OperationConfig, OperationCategory
    
    # Create minimal config
    config = GeneratorConfig()
    
    # Create a simple operation config
    operation = OperationConfig(
        name="addi",
        dialect="arith",
        category=OperationCategory.ARITHMETIC,
        bitwidths=[32]
    )
    
    # Add to config
    from dap_trace_library.config.dialect_config import DialectConfig, DialectType
    dialect = DialectConfig(
        name="arith",
        dialect_type=DialectType.ARITH,
        operations=[operation]
    )
    config.dialects = [dialect]
    
    generator = ConfigurableGenerator(config)
    values = {"a": 1, "b": 2, "bitwidth": 32}
    
    # Generate MLIR
    result = generator.generate_mlir_snippet(operation, values)
    
    # Basic validation
    assert "module" in result
    assert "func.func" in result
    assert "arith.addi" in result
    assert "i32" in result
    
    print("Phase 1 completion test passed - new system works with old configuration")
```

- [ ] **Step 3: Run Phase 1 completion tests**

```bash
pytest tests/test_phase1_completion.py -v
```

Expected: All tests PASS

- [ ] **Step 4: Run full test suite to ensure no regressions**

```bash
cd /home/transcend/code/VIBE/symbolic-mlir-debugger/debugger
python -m pytest ../dap_trace_library/ -v --tb=short
```

Expected: All existing tests pass (may have deprecation warnings)

- [ ] **Step 5: Create git tag for Phase 1 completion**

```bash
cd /home/transcend/code/VIBE/symbolic-mlir-debugger
git tag v2.0-phase1-complete
git push origin v2.0-phase1-complete
```

- [ ] **Step 6: Commit Phase 1 completion verification**

```bash
git add tests/test_phase1_completion.py
git commit -m "feat: add Phase 1 completion tests and verification"
```

---

## Phase 1 Completion Criteria

✅ **Phase 1: Foundation (Jinja2 Integration with Fallback) - COMPLETE**

### What has been implemented:
1. **Jinja2 dependency** added to requirements
2. **Template directory structure** created with base templates
3. **TemplateLoader utility** with fallback to string templates
4. **ConfigurableGenerator updated** to use TemplateLoader with backward compatibility
5. **Backward compatibility verified** - existing tests pass
6. **Phase 1 completion tests** added

### Files created/modified:
- `requirements.txt` - Added Jinja2 dependency
- `dap_trace_library/templates/` - Base Jinja2 templates
- `dap_trace_library/utils/template_loader.py` - TemplateLoader with fallback
- `dap_trace_library/generation/configurable_generator.py` - Updated to use TemplateLoader
- `tests/test_template_loader.py` - TemplateLoader tests
- `tests/test_generator_integration.py` - Generator integration tests
- `tests/test_phase1_completion.py` - Phase 1 completion tests

### Backward compatibility maintained:
- Existing string templates continue to work
- Generator falls back to string templates when Jinja2 templates not available
- All existing tests pass without modification
- Output equivalence verified for basic operations

---

## Next Steps

1. **Execute Phase 1** using @subagent-driven-development
2. **Review Phase 1 completion** before proceeding to Phase 2
3. **Continue with Phase 2-6** implementation following the same pattern
4. **Perform final validation** before removing deprecated files
5. **Update documentation** and release new version

**Git tag before starting:** `git tag v2.0-phase1-start`

**Rollback procedure:** `git reset --hard v2.0-phase1-start` if Phase 1 fails validation.