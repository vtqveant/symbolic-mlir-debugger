#!/usr/bin/env python3
"""
State manager for symbolic execution.

Manages the lifecycle of execution states, including forking, worklist scheduling,
and completed state tracking.

Responsibilities:
1. State lifecycle: maintain worklist of active states, track completed states
2. State forking: create copies of states for symbolic branching (via state.fork())
3. Scheduling: determine which state to execute next (FIFO by default)
4. Termination: mark states as completed when they terminate (pc is None)

State forking responsibilities:
- The StateManager provides fork_state() method that delegates to state.fork()
- Control flow operations (cf.cond_br) should fork states via StateManager
- The interpreter executes operations and may request state forking via StateManager
- Path conditions are added by the control flow executor, not by StateManager
- Concrete values and memory model are forked by SymbolicState.fork()

Memory model integration:
- SymbolicState includes a memory_model instance (MemrefMemoryModel by default)
- State forking automatically forks the memory model via memory_model.fork()
- Memory operations use the memory model for symbolic/concrete storage

Worklist scheduling:
- Default FIFO (breadth-first) for symbolic execution
- Can be switched to LIFO or priority modes for concolic execution
- Priority methods: prioritize_by_path_length(), prioritize_by_recently_forked()
"""

from typing import List, Optional, Dict, Any
from .models import SymbolicState


class StateManager:
    """Manages symbolic execution states.

    Responsibilities:
    - Maintain worklist of active states
    - Fork states for symbolic branching
    - Track completed states
    - Schedule state execution (FIFO by default)
    """

    def __init__(self, initial_state: Optional[SymbolicState] = None):
        """Initialize state manager.

        Args:
            initial_state: Optional initial state to start with
        """
        self.worklist: List[SymbolicState] = []
        self.completed_states: List[SymbolicState] = []

        if initial_state is not None:
            self.add_state(initial_state)

    def add_state(self, state: SymbolicState) -> None:
        """Add a state to the worklist for execution."""
        if state.pc is not None:  # Only add states that can continue execution
            self.worklist.append(state)
        else:
            # State is already terminated, add to completed
            self.completed_states.append(state)

    def add_states(self, states: List[SymbolicState]) -> None:
        """Add multiple states to the worklist."""
        for state in states:
            self.add_state(state)

    def get_next_state(self) -> Optional[SymbolicState]:
        """Get the next state from the worklist (FIFO).

        Returns:
            Next state to execute, or None if worklist is empty
        """
        if not self.worklist:
            return None
        return self.worklist.pop(0)  # FIFO (breadth-first)

    def fork_state(self, state: SymbolicState) -> SymbolicState:
        """Create a copy of a state for symbolic branching.

        Args:
            state: State to fork

        Returns:
            Deep copy of the state
        """
        return state.fork()

    def fork_states(self, state: SymbolicState, count: int) -> List[SymbolicState]:
        """Create multiple copies of a state.

        Args:
            state: State to fork
            count: Number of copies to create

        Returns:
            List of forked states
        """
        return [state.fork() for _ in range(count)]

    def complete_state(self, state: SymbolicState) -> None:
        """Mark a state as completed (terminated).

        Args:
            state: State that has terminated (pc is None)
        """
        # Remove from worklist if present
        if state in self.worklist:
            self.worklist.remove(state)
        # Add to completed if not already there
        if state not in self.completed_states:
            self.completed_states.append(state)

    def has_states(self) -> bool:
        """Check if there are states remaining in the worklist."""
        return len(self.worklist) > 0

    def is_empty(self) -> bool:
        """Check if worklist is empty."""
        return len(self.worklist) == 0

    def get_worklist_size(self) -> int:
        """Get number of states in worklist."""
        return len(self.worklist)

    def get_completed_count(self) -> int:
        """Get number of completed states."""
        return len(self.completed_states)

    def get_all_completed(self) -> List[SymbolicState]:
        """Get all completed states."""
        return list(self.completed_states)

    def clear(self) -> None:
        """Clear all states (worklist and completed)."""
        self.worklist.clear()
        self.completed_states.clear()

    def prioritize_by_path_length(self) -> None:
        """Prioritize states with shorter path conditions (for concolic execution).

        This implements depth-first search by preferring states with fewer
        branch decisions (shorter path conditions).
        """
        self.worklist.sort(key=lambda s: len(s.path_condition))

    def prioritize_by_recently_forked(self) -> None:
        """Prioritize recently forked states (LIFO).

        This implements depth-first search by preferring states that were
        most recently added to the worklist.
        """
        # Reverse the worklist to make it LIFO
        self.worklist.reverse()
