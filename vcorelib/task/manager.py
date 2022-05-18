"""
A simple task management interface.
"""

# built-in
from asyncio import gather
from asyncio import get_event_loop as _get_event_loop
from collections import defaultdict
from typing import Any as _Any
from typing import Callable as _Callable
from typing import Coroutine as _Coroutine
from typing import Dict as _Dict
from typing import Iterable as _Iterable
from typing import List as _List
from typing import Set as _Set
from typing import Tuple as _Tuple
from typing import cast

# internal
from vcorelib.script import ScriptableMixin
from vcorelib.target import TargetMatch
from vcorelib.target.resolver import TargetResolver
from vcorelib.task import Task

BasicCoroutine = _Callable[[], _Coroutine[_Any, _Any, None]]


class TaskManager(ScriptableMixin):
    """
    A class for managing concurrent execution of tasks and also interfacing
    them via names.
    """

    def __init__(self, resolver: TargetResolver = None) -> None:
        """Initialize this task manager."""

        super().__init__()
        self.tasks: _Dict[str, Task] = {}
        self.dependencies: _Dict[str, _Set[str]] = defaultdict(set)
        self.finalized: bool = False
        if resolver is None:
            resolver = TargetResolver()
        self.resolver = resolver
        self.eloop = _get_event_loop()

    def register(
        self,
        task: Task,
        dependencies: _Iterable[str] = None,
        target: str = None,
    ) -> bool:
        """Register a new task and apply any requested dependencies."""

        new_task = False

        # Register this target so that it will return the provided task if
        # matched.
        if target is None:
            target = task.name

        # Don't take any action if we didn't actually register the task.
        if self.resolver.register(target, task):
            self.tasks[task.name] = task
            new_task = True

        # If we're adding more dependencies, make sure it's for the same task.
        else:
            assert self.tasks[task.name] == task

        if dependencies is None:
            dependencies = []
        self.dependencies[task.name].update(dependencies)

        self.finalized = False
        return new_task

    def register_to(self, target: str, dependencies: _Iterable[str]) -> bool:
        """Register dependencies to a task by name."""
        return self.register(self.tasks[target], dependencies)

    def finalize(self, **kwargs) -> None:
        """Register task dependencies while the event loop is running."""

        if not self.finalized:
            for task, deps in self.dependencies.items():
                self.tasks[task].depend_on_all(
                    (self.tasks[x] for x in deps), **kwargs
                )
            self.finalized = True

    def evaluate(
        self, tasks: _Iterable[str], **kwargs
    ) -> _Tuple[_List[_Tuple[Task, TargetMatch]], _Set[str]]:
        """
        Iterate over task strings and provide a list of tasks that can be
        executed (plus relevant data from matching the target) as well as
        the set of tasks that can't be resolved.
        """

        # Ensure task dependencies are added.
        self.finalize(**kwargs)

        unresolved: _Set[str] = set()
        task_objs: _List[_Tuple[Task, TargetMatch]] = []
        for resolved in self.resolver.evaluate_all(tasks):
            if isinstance(resolved, str):
                unresolved.add(resolved)
                continue
            task_objs.append((cast(Task, resolved.data), resolved.result))

        return task_objs, unresolved

    def prepare_execute(
        self, tasks: _Iterable[str], **kwargs
    ) -> _Tuple[_Set[str], BasicCoroutine]:
        """
        Gather tasks that can and can't be executed to prepare a function that
        can execute tasks and also return the task strings that wouldn't be
        resolved.
        """

        task_objs, unresolved = self.evaluate(tasks, **kwargs)

        async def executor() -> None:
            """Wait for all of the configured tasks to complete."""

            # Run all tasks together in the event loop.
            await gather(
                *[
                    x[0].dispatch(substitutions=x[1].substitutions, **kwargs)
                    for x in task_objs
                ]
            )

        return unresolved, executor

    def execute(self, tasks: _Iterable[str], **kwargs) -> _Set[str]:
        """
        Execute some set of provided tasks. Return the tasks that don't get
        resolved.
        """

        unresolved, executor = self.prepare_execute(tasks, **kwargs)
        self.eloop.run_until_complete(executor())
        return unresolved
