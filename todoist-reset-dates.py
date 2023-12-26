import datetime
from datetime import date, timedelta
import os
import re

from todoist.api import TodoistAPI


class MissingApiKeyError(Exception):
    pass


def get_api_key() -> str:
    env_api_key = os.environ.get('API_KEY')
    if env_api_key is not None:
        return env_api_key
    else:
        raise MissingApiKeyError("API_KEY not found in environment")


api_key = get_api_key()
api = TodoistAPI(api_key)

# It is necessary to get all of the tasks and check all their due dates,
# otherwise the logic may overload a day with too many tasks
due_dates = {}


def get_date_from_item(item):
    due = item['due']
    if due is None:
        return None

    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', due['date'])
    return datetime.date(
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)))


def get_overdue_tasks():
    tasks = []
    today = date.today()
    for item in api.state['items']:
        due = get_date_from_item(item)
        if due is not None:
            if due < today:
                tasks.append(item)
    return tasks


def analyze_due_dates():
    for item in api.state['items']:
        due_without_time = get_date_from_item(item)
        if due_without_time is None:
            continue
        if due_without_time not in due_dates:
            due_dates[due_without_time] = []
        due_dates[due_without_time].append(item)


def reset_due_dates(tasks):
    number = 1
    next_due_date = date.today()
    day_limit = len(due_dates.get(next_due_date, []))

    for task in tasks:
        print(f"Task {number}:  {task.data['content']}")
        while True:
            if day_limit >= 5:
                next_due_date += timedelta(days=+1)
                day_limit = len(due_dates.get(next_due_date, []))
            else:
                break
        print(f"   sending to {next_due_date}")
        due = task.data['due']
        due['date'] = next_due_date
        task.update(due=due)
        number += 1
        day_limit += 1


def main():
    api.sync()
    tasks = get_overdue_tasks()
    analyze_due_dates()

    reset_due_dates(tasks)
    api.commit()


if __name__ == '__main__':
    main()
