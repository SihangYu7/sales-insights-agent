"""
LangChain Callback Handlers
===========================
Custom callbacks for logging, metrics tracking, and user context management.

These handlers integrate with LangChain's callback system to provide:
- Detailed logging of LLM and tool events
- Performance metrics and cost tracking
- User context for personalization and auditing
"""

import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langchain_middleware")


class LoggingCallbackHandler(BaseCallbackHandler):
    """
    Tracks all LLM and tool events with detailed logging.

    Events logged:
    - LLM start/end with prompts and responses
    - Tool invocations with inputs and outputs
    - Errors with full context
    - Chain execution flow
    """

    def __init__(self, user_id: Optional[int] = None, log_level: str = "INFO"):
        self.user_id = user_id
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.start_times: Dict[str, float] = {}

    def _log(self, level: int, message: str, **kwargs):
        """Helper to log with user context."""
        extra = {"user_id": self.user_id, **kwargs}
        logger.log(level, f"[User:{self.user_id}] {message}", extra=extra)

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts processing."""
        self.start_times[str(run_id)] = time.time()
        model_name = serialized.get("name", "unknown")
        prompt_preview = prompts[0][:100] + "..." if prompts and len(prompts[0]) > 100 else prompts[0] if prompts else ""

        self._log(
            logging.INFO,
            f"LLM Start | Model: {model_name} | Prompt: {prompt_preview}",
            run_id=str(run_id),
            event="llm_start"
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM finishes processing."""
        elapsed = time.time() - self.start_times.pop(str(run_id), time.time())

        # Extract token usage if available
        token_usage = {}
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})

        self._log(
            logging.INFO,
            f"LLM End | Duration: {elapsed:.2f}s | Tokens: {token_usage}",
            run_id=str(run_id),
            event="llm_end",
            duration=elapsed,
            tokens=token_usage
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM encounters an error."""
        self._log(
            logging.ERROR,
            f"LLM Error | {type(error).__name__}: {str(error)}",
            run_id=str(run_id),
            event="llm_error",
            error_type=type(error).__name__
        )

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts execution."""
        self.start_times[str(run_id)] = time.time()
        tool_name = serialized.get("name", "unknown")
        input_preview = input_str[:100] + "..." if len(input_str) > 100 else input_str

        self._log(
            logging.INFO,
            f"Tool Start | {tool_name} | Input: {input_preview}",
            run_id=str(run_id),
            event="tool_start",
            tool_name=tool_name
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool finishes execution."""
        elapsed = time.time() - self.start_times.pop(str(run_id), time.time())
        output_preview = str(output)[:100] + "..." if len(str(output)) > 100 else str(output)

        self._log(
            logging.INFO,
            f"Tool End | Duration: {elapsed:.2f}s | Output: {output_preview}",
            run_id=str(run_id),
            event="tool_end",
            duration=elapsed
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool encounters an error."""
        self._log(
            logging.ERROR,
            f"Tool Error | {type(error).__name__}: {str(error)}",
            run_id=str(run_id),
            event="tool_error",
            error_type=type(error).__name__
        )

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain starts."""
        self.start_times[str(run_id)] = time.time()
        chain_name = serialized.get("name", "unknown")

        self._log(
            logging.DEBUG,
            f"Chain Start | {chain_name}",
            run_id=str(run_id),
            event="chain_start"
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain finishes."""
        elapsed = time.time() - self.start_times.pop(str(run_id), time.time())

        self._log(
            logging.DEBUG,
            f"Chain End | Duration: {elapsed:.2f}s",
            run_id=str(run_id),
            event="chain_end",
            duration=elapsed
        )


class MetricsCallbackHandler(BaseCallbackHandler):
    """
    Collects performance metrics for monitoring and cost tracking.

    Metrics tracked:
    - Response times per operation
    - Token usage (input/output)
    - Tool call frequency
    - Cost estimates based on token usage
    """

    # Approximate costs per 1K tokens (GPT-3.5-Turbo)
    COST_PER_1K_INPUT = 0.0005
    COST_PER_1K_OUTPUT = 0.0015

    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
        self.metrics = {
            "user_id": user_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "llm_calls": 0,
            "tool_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_duration_seconds": 0.0,
            "estimated_cost_usd": 0.0,
            "tools_used": [],
            "errors": []
        }
        self.start_times: Dict[str, float] = {}

    def get_metrics(self) -> Dict[str, Any]:
        """Return collected metrics."""
        self.metrics["completed_at"] = datetime.now(timezone.utc).isoformat()
        return self.metrics.copy()

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Track LLM call start."""
        self.start_times[str(run_id)] = time.time()
        self.metrics["llm_calls"] += 1

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Track LLM call completion and token usage."""
        elapsed = time.time() - self.start_times.pop(str(run_id), time.time())
        self.metrics["total_duration_seconds"] += elapsed

        # Extract token usage
        if response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            self.metrics["total_input_tokens"] += input_tokens
            self.metrics["total_output_tokens"] += output_tokens

            # Calculate cost
            input_cost = (input_tokens / 1000) * self.COST_PER_1K_INPUT
            output_cost = (output_tokens / 1000) * self.COST_PER_1K_OUTPUT
            self.metrics["estimated_cost_usd"] += input_cost + output_cost

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Track LLM errors."""
        self.metrics["errors"].append({
            "type": "llm_error",
            "error": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Track tool call start."""
        self.start_times[str(run_id)] = time.time()
        self.metrics["tool_calls"] += 1

        tool_name = serialized.get("name", "unknown")
        if tool_name not in self.metrics["tools_used"]:
            self.metrics["tools_used"].append(tool_name)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Track tool call completion."""
        elapsed = time.time() - self.start_times.pop(str(run_id), time.time())
        self.metrics["total_duration_seconds"] += elapsed

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Track tool errors."""
        self.metrics["errors"].append({
            "type": "tool_error",
            "error": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


class UserContextCallbackHandler(BaseCallbackHandler):
    """
    Manages user context for personalization and auditing.

    Features:
    - Store user_id, email, name with each request
    - Track per-user query history
    - Enable personalized responses
    - Audit trail for compliance
    """

    def __init__(
        self,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None
    ):
        self.user_id = user_id
        self.user_email = user_email
        self.user_name = user_name
        self.query_log: List[Dict[str, Any]] = []

    def get_user_context(self) -> Dict[str, Any]:
        """Return current user context."""
        return {
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_name": self.user_name
        }

    def get_query_log(self) -> List[Dict[str, Any]]:
        """Return query history for this session."""
        return self.query_log.copy()

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Log the start of a query with user context."""
        # Only log top-level chains (no parent)
        if kwargs.get("parent_run_id") is None:
            question = inputs.get("question", inputs.get("input", str(inputs)))
            self.query_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": self.user_id,
                "question": question[:500] if isinstance(question, str) else str(question)[:500],
                "run_id": str(run_id)
            })

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Update query log with results."""
        # Find and update the matching query log entry
        for entry in self.query_log:
            if entry.get("run_id") == str(run_id):
                entry["completed"] = True
                entry["completed_at"] = datetime.now(timezone.utc).isoformat()
                break


def create_callback_handlers(
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None,
    enable_logging: bool = True,
    enable_metrics: bool = True,
    enable_user_context: bool = True
) -> List[BaseCallbackHandler]:
    """
    Factory function to create a list of callback handlers.

    Args:
        user_id: User ID for context
        user_email: User email for context
        user_name: User name for context
        enable_logging: Enable logging handler
        enable_metrics: Enable metrics handler
        enable_user_context: Enable user context handler

    Returns:
        List of configured callback handlers
    """
    handlers = []

    if enable_logging:
        handlers.append(LoggingCallbackHandler(user_id=user_id))

    if enable_metrics:
        handlers.append(MetricsCallbackHandler(user_id=user_id))

    if enable_user_context:
        handlers.append(UserContextCallbackHandler(
            user_id=user_id,
            user_email=user_email,
            user_name=user_name
        ))

    return handlers
