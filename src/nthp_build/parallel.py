import logging
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process

log = logging.getLogger(__name__)


def run_tasks_in_series(tasks):
    log.info("Running %d tasks in series", len(tasks))
    for task in tasks:
        task()


def run_cpu_tasks_in_parallel(tasks, state=None):
    log.info("Running %d CPU tasks in parallel", len(tasks))
    running_tasks = [Process(target=task) for task in tasks]
    for running_task in running_tasks:
        running_task.start()
    for running_task in running_tasks:
        running_task.join()


def run_io_tasks_in_parallel(tasks):
    log.info("Running %d IO tasks in parallel", len(tasks))
    with ThreadPoolExecutor() as executor:
        running_tasks = [executor.submit(task) for task in tasks]
        for running_task in running_tasks:
            running_task.result()
