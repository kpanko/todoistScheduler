import os
import re
from datetime import date, datetime, timedelta
import logging
from typing import List
from zoneinfo import ZoneInfo

from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task

TASKS_PER_DAY = 5

USER_TZ = os.environ.get('USER_TZ', 'America/New_York')
api_key = os.environ.get('TODOIST_API_KEY', '')
api = TodoistAPI(api_key)


# TODO: I think the ! is going missing and todoist isn't preserving it;
# instead of this, use a tag like @not_reschedule for daily repeating tasks
def sort_tasks(list: List[Task]):
    list.sort(key=lambda t: (
      '!' in t.due.string if t.due else True,
      -t.priority,
      t.due.date if t.due else None
      ))


def get_tasks_for(day: date) -> List[Task]:
  return api.get_tasks(filter='due on ' + day.strftime('%m/%d/%Y'))


def reschedule_to(task: Task, date: date):

  if task.due.date == date.strftime('%Y-%m-%d'):
    return

  logging.info(f"Sending the task {task.content} to {date}")
  
  due_date = task.due.string

  due_date = re.sub(r'\s*starting on.*', '', due_date)
  
  if task.due.is_recurring:
    due_string = f"{due_date} starting on " + date.strftime('%m/%d/%Y')
  else:
    due_string = date.strftime('%m/%d/%Y')
    
  logging.debug("updating task_id %s with: %s", task.id, due_string)

  is_success = api.update_task(task_id=task.id, due_string=due_string)

  if not is_success:
    raise Exception("Failed to reschedule task")
  

def slice_list(lst, num_items):
    if num_items >= 0:
      return lst[:num_items], lst[num_items:]
    else:
      return [], lst
  
def schedule_and_push_down(
  tasks_to_add: List[Task],
  day: date = None,
  depth: int = 0):

  logging.debug("Called schedule_and_push_down with depth %d", depth)
  logging.debug("Tasks to add (%d):", len(tasks_to_add))
  for task in tasks_to_add:
    logging.debug(task)

  if not tasks_to_add:
    return

  if day is None:
    day = datetime.now(ZoneInfo(USER_TZ)).date() # Today

  # query all the tasks for this day

  logging.debug("Getting tasks for %s", day)
  tasks = get_tasks_for(day)

  num_this_day = len(tasks)

  logging.debug("Found %d tasks", len(tasks))
  for task in tasks:
    logging.debug(task)

  # filter tasks to have only repeating tasks with the '!'
  tasks = [t for t in tasks if t.due.is_recurring and '!' in t.due.string]

  num_this_day = num_this_day - len(tasks)

  logging.debug("After filter there are now %d tasks", len(tasks))
  
  tasks.extend(tasks_to_add)

  # Sort tasks by priority and by days late
  sort_tasks(tasks)

  tasks_for_this_day, tasks_for_later = slice_list(tasks, TASKS_PER_DAY-num_this_day)

  # assign tasks to this day

  logging.debug("%d tasks to reschedule to %s", len(tasks_for_this_day), day)

  for task in tasks_for_this_day:
    reschedule_to(task, day)

  # recursively call self with rest of the tasks

  schedule_and_push_down(tasks_for_later, day + timedelta(days=+1), depth+1)
  

logging.basicConfig(level=logging.DEBUG)

try:
  # Get all overdue tasks
  logging.info("Getting overdue tasks")
  overdue_tasks = api.get_tasks(filter='overdue & ! p1')

  schedule_and_push_down(overdue_tasks)

except Exception as e:
  print(e)
