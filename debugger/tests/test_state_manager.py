#!/usr/bin/env python3
"""
Tests for StateManager.
"""

import pytest
import z3
from interpreter.state_manager import StateManager
from interpreter.models import SymbolicState


def test_state_manager_initialization():
    """Test StateManager initialization with and without initial state."""
    # Empty initialization
    sm = StateManager()
    assert sm.get_worklist_size() == 0
    assert sm.get_completed_count() == 0
    assert not sm.has_states()

    # With initial state
    state = SymbolicState(pc="^entry")
    sm = StateManager(initial_state=state)
    assert sm.get_worklist_size() == 1
    assert sm.get_completed_count() == 0
    assert sm.has_states()


def test_add_state():
    """Test adding states to worklist."""
    sm = StateManager()
    state1 = SymbolicState(pc="^block1")
    state2 = SymbolicState(pc="^block2")
    state3 = SymbolicState(pc=None)  # terminated state

    sm.add_state(state1)
    assert sm.get_worklist_size() == 1
    sm.add_state(state2)
    assert sm.get_worklist_size() == 2

    # Terminated state should go directly to completed
    sm.add_state(state3)
    assert sm.get_worklist_size() == 2
    assert sm.get_completed_count() == 1


def test_add_states():
    """Test adding multiple states at once."""
    sm = StateManager()
    states = [
        SymbolicState(pc="^block1"),
        SymbolicState(pc="^block2"),
        SymbolicState(pc=None),
    ]
    sm.add_states(states)
    assert sm.get_worklist_size() == 2
    assert sm.get_completed_count() == 1


def test_get_next_state_fifo():
    """Test FIFO ordering of get_next_state."""
    sm = StateManager()
    state1 = SymbolicState(pc="^block1")
    state2 = SymbolicState(pc="^block2")
    sm.add_state(state1)
    sm.add_state(state2)

    # First in, first out
    next_state = sm.get_next_state()
    assert next_state is state1
    assert sm.get_worklist_size() == 1

    next_state = sm.get_next_state()
    assert next_state is state2
    assert sm.get_worklist_size() == 0

    # Empty worklist returns None
    assert sm.get_next_state() is None


def test_fork_state():
    """Test forking a state."""
    sm = StateManager()
    original = SymbolicState(pc="^block1")
    original.add_path_condition(z3.Bool("cond"))
    original.set_value("x", z3.Int("x"), "i32")
    original.set_concrete_value("x", 42)

    forked = sm.fork_state(original)
    assert forked is not original
    assert forked.pc == original.pc
    assert len(forked.path_condition) == len(original.path_condition)
    assert forked.get_expr("x") == original.get_expr("x")
    assert forked.get_concrete_value("x") == original.get_concrete_value("x")

    # Modifying forked state should not affect original
    forked.add_path_condition(z3.Bool("new_cond"))
    assert len(forked.path_condition) == 2
    assert len(original.path_condition) == 1


def test_fork_states():
    """Test forking multiple copies."""
    sm = StateManager()
    original = SymbolicState(pc="^block1")
    copies = sm.fork_states(original, 3)
    assert len(copies) == 3
    for copy in copies:
        assert copy.pc == original.pc
        assert copy is not original
    # All copies should be distinct objects
    assert copies[0] is not copies[1]
    assert copies[0] is not copies[2]


def test_complete_state():
    """Test marking state as completed."""
    sm = StateManager()
    state = SymbolicState(pc="^block1")
    sm.add_state(state)
    assert sm.get_worklist_size() == 1
    assert sm.get_completed_count() == 0

    # Complete state (terminate)
    state.pc = None
    sm.complete_state(state)
    # State should be moved from worklist to completed
    assert sm.get_worklist_size() == 0
    assert sm.get_completed_count() == 1

    # Completing same state twice should not duplicate
    sm.complete_state(state)
    assert sm.get_completed_count() == 1


def test_clear():
    """Test clearing all states."""
    sm = StateManager()
    sm.add_state(SymbolicState(pc="^block1"))
    sm.add_state(SymbolicState(pc=None))
    assert sm.get_worklist_size() == 1
    assert sm.get_completed_count() == 1

    sm.clear()
    assert sm.get_worklist_size() == 0
    assert sm.get_completed_count() == 0


def test_prioritize_by_path_length():
    """Test priority scheduling by path length."""
    sm = StateManager()
    state1 = SymbolicState(pc="^block1")
    state1.add_path_condition(z3.Bool("cond1"))
    state1.add_path_condition(z3.Bool("cond2"))  # length 2
    state2 = SymbolicState(pc="^block2")
    state2.add_path_condition(z3.Bool("cond3"))  # length 1
    state3 = SymbolicState(pc="^block3")  # length 0

    sm.add_state(state1)
    sm.add_state(state2)
    sm.add_state(state3)

    sm.prioritize_by_path_length()
    # Should order by increasing path length: state3, state2, state1
    next_state = sm.get_next_state()
    assert next_state is state3
    next_state = sm.get_next_state()
    assert next_state is state2
    next_state = sm.get_next_state()
    assert next_state is state1


def test_prioritize_by_recently_forked():
    """Test LIFO scheduling."""
    sm = StateManager()
    state1 = SymbolicState(pc="^block1")
    state2 = SymbolicState(pc="^block2")
    state3 = SymbolicState(pc="^block3")

    sm.add_state(state1)
    sm.add_state(state2)
    sm.add_state(state3)

    sm.prioritize_by_recently_forked()
    # Should reverse order: state3, state2, state1
    next_state = sm.get_next_state()
    assert next_state is state3
    next_state = sm.get_next_state()
    assert next_state is state2
    next_state = sm.get_next_state()
    assert next_state is state1


def test_memory_model_forking():
    """Test that memory model is properly forked."""
    sm = StateManager()
    original = SymbolicState(pc="^entry")
    # Allocate a memref in memory model
    original.allocate_memory("mem", (10, 20), "i32")
    # Store a concrete value
    original.memory_model.store("mem", [0, 0], z3.IntVal(42), "i32")
    original.memory_model.set_concrete_value("mem", [0, 0], 42)

    forked = sm.fork_state(original)
    # Memory models should be different objects
    assert forked.memory_model is not original.memory_model
    # But should have same content initially
    val = forked.memory_model.load("mem", [0, 0], "i32")
    assert isinstance(val, z3.ExprRef)
    # Concrete value should be preserved
    concrete = forked.memory_model.get_concrete_value("mem", [0, 0])
    assert concrete == 42

    # Modifying forked memory should not affect original
    forked.memory_model.store("mem", [0, 0], z3.IntVal(99), "i32")
    val_original = original.memory_model.load("mem", [0, 0], "i32")
    val_forked = forked.memory_model.load("mem", [0, 0], "i32")
    # Values should differ
    # Use Z3 to check equality
    solver = z3.Solver()
    solver.add(val_original == val_forked)
    assert solver.check() == z3.unsat  # Not equal


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
