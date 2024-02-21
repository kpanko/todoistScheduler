import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from todoist_api_python.api import TodoistAPI

TASKS_PER_DAY = 5

USER_TZ = os.environ.get('USER_TZ', 'America/New_York')
api_key = os.environ['TODOIST_API_KEY']
api = TodoistAPI(api_key)


def get_number_tasks_for(next_day):
  tasks = api.get_tasks(filter='due on ' + next_day.strftime('%m/%d/%Y'))
  return len(tasks)
  

# TODO: refactor to not be globals?
next_day = datetime.now(ZoneInfo(USER_TZ)).date()
tasks_on_next_day = get_number_tasks_for(next_day)


def reschedule_to(task, date):
  due_date = task.due.string

  due_date = re.sub(r'\bstarting on\b.*', '', due_date)
  
  if task.due.is_recurring:
    due_string = f"{due_date}starting on " + date.strftime('%m/%d/%Y')
  else:
    due_string = date.strftime('%m/%d/%Y')
    
  is_success = api.update_task(task_id=task.id, due_string=due_string)

  if not is_success:
    raise Exception("Failed to reschedule task")
  

def reschedule_to_next_free_day(task):
  global next_day, tasks_on_next_day

  # check if the next day has too many tasks
  while tasks_on_next_day >= TASKS_PER_DAY:
    next_day += timedelta(days=+1)
    tasks_on_next_day = get_number_tasks_for(next_day)

  reschedule_to(task, next_day)
  tasks_on_next_day = get_number_tasks_for(next_day)


# Get all overdue tasks

try:
  tasks = api.get_tasks(filter='overdue')

  for task in tasks:
    reschedule_to_next_free_day(task)

except Exception as e:
  print(e)
