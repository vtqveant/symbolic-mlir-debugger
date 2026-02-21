#!/usr/bin/env python3
"""
Logging utilities for DAP trace library.

Consistent logging configuration across all library modules.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime


class LoggingUtils:
    """Utility class for logging configuration."""
    
    # Default logging format
    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Default date format
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    @staticmethod
    def setup_logging(
        level: int = logging.INFO,
        format_string: str = None,
        date_format: str = None,
        log_file: Optional[Path] = None,
        console: bool = True
    ) -> None:
        """Setup logging configuration.
        
        Args:
            level: Logging level
            format_string: Log message format
            date_format: Date format in logs
            log_file: Optional file to log to
            console: Whether to log to console
        """
        if format_string is None:
            format_string = LoggingUtils.DEFAULT_FORMAT
        
        if date_format is None:
            date_format = LoggingUtils.DEFAULT_DATE_FORMAT
        
        # Clear existing handlers
        logging.getLogger().handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(format_string, date_format)
        
        # Setup console handler
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(level)
            logging.getLogger().addHandler(console_handler)
        
        # Setup file handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            logging.getLogger().addHandler(file_handler)
        
        # Set root logger level
        logging.getLogger().setLevel(level)
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get logger with standardized configuration.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Configured logger
        """
        return logging.getLogger(name)
    
    @staticmethod
    def setup_module_logging(module_name: str, 
                           level: int = logging.INFO) -> logging.Logger:
        """Setup logging for a specific module.
        
        Args:
            module_name: Module name
            level: Logging level
            
        Returns:
            Configured logger
        """
        logger = logging.getLogger(module_name)
        logger.setLevel(level)
        
        # Don't propagate to root logger to avoid duplicate logs
        logger.propagate = False
        
        # Add console handler if not already present
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(LoggingUtils.DEFAULT_FORMAT, 
                                        LoggingUtils.DEFAULT_DATE_FORMAT)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @staticmethod
    def create_structured_logger(name: str, 
                               log_file: Optional[Path] = None) -> logging.Logger:
        """Create logger that outputs structured JSON logs.
        
        Args:
            name: Logger name
            log_file: Optional file for JSON logs
            
        Returns:
            Structured logger
        """
        logger = logging.getLogger(f"{name}.structured")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create JSON formatter
        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Add extra fields if present
                if hasattr(record, "extra"):
                    log_data.update(record.extra)
                
                return json.dumps(log_data)
        
        # Add console handler for structured logging
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        
        return logger
    
    @staticmethod
    def log_with_context(logger: logging.Logger, 
                        level: int,
                        message: str,
                        context: Dict[str, Any] = None,
                        **kwargs) -> None:
        """Log message with additional context.
        
        Args:
            logger: Logger instance
            level: Logging level
            message: Log message
            context: Additional context dictionary
            **kwargs: Additional context as keyword arguments
        """
        if context is None:
            context = {}
        
        # Merge context and kwargs
        full_context = {**context, **kwargs}
        
        # Create log record with extra context
        extra = {"extra": full_context}
        
        if level == logging.DEBUG:
            logger.debug(message, extra=extra)
        elif level == logging.INFO:
            logger.info(message, extra=extra)
        elif level == logging.WARNING:
            logger.warning(message, extra=extra)
        elif level == logging.ERROR:
            logger.error(message, extra=extra)
        elif level == logging.CRITICAL:
            logger.critical(message, extra=extra)
    
    @staticmethod
    def log_performance(logger: logging.Logger,
                       operation: str,
                       duration_seconds: float,
                       details: Dict[str, Any] = None) -> None:
        """Log performance metrics.
        
        Args:
            logger: Logger instance
            operation: Operation name
            duration_seconds: Duration in seconds
            details: Additional details
        """
        if details is None:
            details = {}
        
        context = {
            "operation": operation,
            "duration_seconds": duration_seconds,
            "performance": True,
            **details
        }
        
        LoggingUtils.log_with_context(
            logger, logging.INFO,
            f"Performance: {operation} took {duration_seconds:.3f}s",
            context
        )
    
    @staticmethod
    def log_error_with_traceback(logger: logging.Logger,
                                error: Exception,
                                context: Dict[str, Any] = None) -> None:
        """Log error with traceback.
        
        Args:
            logger: Logger instance
            error: Exception to log
            context: Additional context
        """
        import traceback
        
        if context is None:
            context = {}
        
        error_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            **context
        }
        
        LoggingUtils.log_with_context(
            logger, logging.ERROR,
            f"Error: {type(error).__name__}: {str(error)}",
            error_context
        )
    
    @staticmethod
    def create_rotating_file_logger(name: str,
                                  log_dir: Path,
                                  max_bytes: int = 10 * 1024 * 1024,  # 10 MB
                                  backup_count: int = 5) -> logging.Logger:
        """Create logger with rotating file handler.
        
        Args:
            name: Logger name
            log_dir: Directory for log files
            max_bytes: Maximum file size before rotation
            backup_count: Number of backup files to keep
            
        Returns:
            Configured logger
        """
        from logging.handlers import RotatingFileHandler
        
        logger = logging.getLogger(f"{name}.rotating")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Ensure log directory exists
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        log_file = log_dir / f"{name}.log"
        handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        
        # Create formatter
        formatter = logging.Formatter(LoggingUtils.DEFAULT_FORMAT, 
                                    LoggingUtils.DEFAULT_DATE_FORMAT)
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
        return logger
    
    @staticmethod
    def setup_library_logging(log_dir: Optional[Path] = None) -> Dict[str, logging.Logger]:
        """Setup logging for all library modules.
        
        Args:
            log_dir: Optional directory for log files
            
        Returns:
            Dictionary of configured loggers
        """
        loggers = {}
        
        # Module names
        modules = [
            "dap_trace_library.config",
            "dap_trace_library.generation",
            "dap_trace_library.validation",
            "dap_trace_library.execution",
            "dap_trace_library.reporting",
            "dap_trace_library.utils"
        ]
        
        # Setup each module
        for module in modules:
            if log_dir:
                log_file = log_dir / f"{module.replace('.', '_')}.log"
                logger = LoggingUtils.create_rotating_file_logger(
                    module, log_dir
                )
            else:
                logger = LoggingUtils.setup_module_logging(module)
            
            loggers[module] = logger
        
        return loggers
    
    @staticmethod
    def capture_logs_to_list(logger_name: str = "dap_trace_library") -> logging.Handler:
        """Create handler that captures logs to a list.
        
        Args:
            logger_name: Logger name to capture
            
        Returns:
            Handler that stores logs in a list
        """
        class ListHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.logs = []
            
            def emit(self, record):
                self.logs.append({
                    "level": record.levelname,
                    "message": self.format(record),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
        
        handler = ListHandler()
        handler.setFormatter(logging.Formatter(LoggingUtils.DEFAULT_FORMAT))
        
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        return handler
    
    @staticmethod
    def log_configuration(logger: logging.Logger,
                         config: Dict[str, Any],
                         config_name: str = "configuration") -> None:
        """Log configuration details.
        
        Args:
            logger: Logger instance
            config: Configuration dictionary
            config_name: Configuration name for logging
        """
        import yaml
        
        # Convert to YAML for readability
        config_yaml = yaml.dump(config, default_flow_style=False)
        
        LoggingUtils.log_with_context(
            logger, logging.INFO,
            f"Loaded {config_name}",
            {"config_name": config_name, "config_size": len(str(config))}
        )
        
        # Log summary
        if "dialects" in config:
            dialects = config["dialects"]
            enabled_dialects = [d for d in dialects if d.get("enabled", True)]
            enabled_operations = sum(
                len([op for op in d.get("operations", []) 
                    if op.get("enabled", True)])
                for d in enabled_dialects
            )
            
            logger.info(
                f"Configuration summary: {len(enabled_dialects)} enabled dialects, "
                f"{enabled_operations} enabled operations"
            )
    
    @staticmethod
    def create_audit_logger(log_file: Path) -> logging.Logger:
        """Create audit logger for important operations.
        
        Args:
            log_file: Audit log file path
            
        Returns:
            Audit logger
        """
        logger = logging.getLogger("dap_trace_library.audit")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create file handler
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file)
        
        # Create audit formatter
        class AuditFormatter(logging.Formatter):
            def format(self, record):
                return (f"{datetime.utcnow().isoformat()}Z | "
                       f"{record.levelname} | "
                       f"{record.module}.{record.funcName} | "
                       f"{record.getMessage()}")
        
        handler.setFormatter(AuditFormatter())
        logger.addHandler(handler)
        
        return logger