import re
from datetime import date, timedelta
import logging
from typing import List, Optional

from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task

def sort_tasks(list: List[Task]):
    """Sorts tasks by priority (desc) and then due date (asc)."""
    list.sort(key=lambda t: (
      -t.priority,
      t.due.date if t.due else None
      ))


def get_tasks_for(api: TodoistAPI, day: date, ignore_tag: str) -> List[Task]:
  """Gets all tasks for a given day, ignoring tasks with a specific tag."""
  return api.get_tasks(
    filter=f'! p1 & ! @{ignore_tag} & due on ' + day.strftime('%Y-%m-%d'))


def reschedule_to(api: TodoistAPI, task: Task, day: date):
  """Reschedules a task to a new date."""
  if task.due is None:
    # This logic only deals with overdue tasks but Pylance does not know this
    return

  if task.due.date == day.strftime('%Y-%m-%d'):
    return

  logging.info(f"Sending the task {task.content} to {day}")

  due_date = task.due.string
  due_date = re.sub(r'\s*starting on.*', '', due_date)

  if task.due.is_recurring:
    due_string = f"{due_date} starting on " + day.strftime('%Y-%m-%d')
  else:
    due_string = day.strftime('%Y-%m-%d')

  logging.debug("updating task_id %s with: %s", task.id, due_string)

  is_success = api.update_task(task_id=task.id, due_string=due_string)

  if not is_success:
    raise Exception("Failed to reschedule task")


def slice_list(lst, num_items):
    """Slices a list into two parts at a given index."""
    if num_items >= 0:
      return lst[:num_items], lst[num_items:]
    else:
      return [], lst

def schedule_and_push_down(
  api: TodoistAPI,
  tasks_to_add: List[Task],
  today: date,
  tasks_per_day: int,
  ignore_tag: str,
  day: Optional[date] = None,
  depth: int = 0):
  """Schedules tasks, pushing them to later days if the current day is full."""

  logging.debug("Called schedule_and_push_down with depth %d", depth)
  logging.debug("Tasks to add (%d):", len(tasks_to_add))
  for task in tasks_to_add:
    logging.debug(task)

  if not tasks_to_add:
    return

  if day is None:
    day = today

  logging.debug("Getting tasks for %s", day)
  tasks = get_tasks_for(api, day, ignore_tag)

  num_this_day = len(tasks)

  logging.debug("Found %d tasks", len(tasks))
  for task in tasks:
    logging.debug(task)

  existing_task_ids = {task.id for task in tasks}

  tasks.extend([t for t in tasks_to_add if t.id not in existing_task_ids])

  sort_tasks(tasks)

  tasks_for_this_day, tasks_for_later = slice_list(
    tasks, tasks_per_day - num_this_day)

  logging.debug("%d tasks to reschedule to %s", len(tasks_for_this_day), day)

  for task in tasks_for_this_day:
    reschedule_to(api, task, day)

  if tasks_for_later:
    schedule_and_push_down(
        api, tasks_for_later, today, tasks_per_day, ignore_tag, day + timedelta(days=+1), depth+1
    )