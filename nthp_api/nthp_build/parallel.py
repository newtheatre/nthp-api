import logging
import multiprocessing
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Queue
from multiprocessing.managers import SyncManager
from typing import Any, NamedTuple

log = logging.getLogger(__name__)

# Children must inherit the parent's memory: `nthp build` loads into an in-memory
# database that only forked processes can see. Python 3.14 makes forkserver the
# Linux default, so ask for fork explicitly rather than relying on it.
MP_CONTEXT = multiprocessing.get_context("fork")


class MultiProcessError(Exception):
    pass


def run_tasks_in_series(tasks):
    log.info("Running %d tasks in series", len(tasks))
    for task in tasks:
        task()


def run_cpu_task(task: Callable, error_queue: Queue):
    try:
        task()
    except Exception as e:
        log.exception(f"Error occurred while running task {task}")
        error_queue.put(e)


def run_cpu_tasks_in_parallel(tasks: list[Callable]):
    log.info("Running %d CPU tasks in parallel", len(tasks))
    error_queue: Queue = MP_CONTEXT.Queue()
    running_tasks = [
        MP_CONTEXT.Process(target=run_cpu_task, args=(task, error_queue))
        for task in tasks
    ]
    for running_task in running_tasks:
        running_task.start()
    for running_task in running_tasks:
        running_task.join()

    if not error_queue.empty():
        raise MultiProcessError("Errors occurred while running tasks")


def run_io_tasks_in_parallel(tasks):
    log.info("Running %d IO tasks in parallel", len(tasks))
    with ThreadPoolExecutor() as executor:
        running_tasks = [executor.submit(task) for task in tasks]
        for running_task in running_tasks:
            running_task.result()


class DumperSharedState(NamedTuple):
    search_documents: Any


def make_dumper_state(manager: SyncManager) -> DumperSharedState:
    return DumperSharedState(search_documents=manager.list())
