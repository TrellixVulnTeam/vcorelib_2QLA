"""
Test the 'task.manager' module.
"""

# third-party
from pytest import raises

# module under test
from vcorelib.task import FailTask, Task, TaskFailed
from vcorelib.task.manager import TaskManager
from vcorelib.task.time.sleep import SleepTask


def test_task_manager_basic():
    """Test basic interactions with a task manager."""

    manager = TaskManager()
    manager.register(SleepTask("a", 0.1))
    manager.register(SleepTask("b", 0.1))
    manager.register(SleepTask("c", 0.1))
    manager.register(SleepTask("test", 0.1), ["a", "b", "c"])
    manager.execute(["test"])
    manager.execute(["test"])

    manager.register_to("a", ["b", "c"])
    manager.register_to("b", ["c"])
    manager.execute(["test"])

    manager.finalized = False
    manager.execute(["test"], init_only=True)


def test_task_manager_dry_run():
    """Test that tasks behave correctly during 'init_only'."""

    manager = TaskManager()
    manager.register(Task("a"))
    manager.register(Task("b"))
    manager.register(Task("c"))
    manager.register(Task("test"), ["a", "b", "c"])
    manager.execute(["test"], init_only=True)
    assert manager.tasks["test"].resolved("test") is False


def test_task_manager_dynamic():
    """Test that we can run dynamically resolved tasks."""

    manager = TaskManager()
    manager.register(SleepTask("a", 0.1))
    manager.register(SleepTask("b", 0.1))
    manager.register(SleepTask("c", 0.1))
    manager.register(SleepTask("a:{a}", 0.1), ["a", "b", "c"])
    manager.execute(["a:1", "a:2", "a:3"])
    manager.execute(["a:1"])
    manager.execute(["a:2"])
    manager.execute(["a:3"])
    assert "d:5" in manager.execute(["a:4", "d:5"])

    # Verify that we can depend on tasks that aren't resolved yet.
    manager.register(Task("test"), ["a:5", "a:6", "a:7"])
    manager.execute(["test"])


def test_task_manager_failure():
    """Test the behavior of the task manager when tasks fail."""

    manager = TaskManager()

    manager.register(SleepTask("a", 2.0))
    manager.register(SleepTask("b", 2.0))
    manager.register(SleepTask("c", 2.0))
    manager.register(FailTask("test"))

    # Ensure this fails.
    with raises(TaskFailed):
        manager.execute(["a", "b", "c", "test"])
