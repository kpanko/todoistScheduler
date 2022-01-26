from datetime import datetime, date, timedelta
from todoist.api import TodoistAPI

api = TodoistAPI("")


def get_overdue_tasks() -> object:
    tasks = []
    for item in api.state['items']:
        due = item['due']
        if due is not None:
            # remove the Z from the end because Python is stupid
            due_date = datetime.fromisoformat(due['date'].removesuffix('Z'))
            if due_date < datetime.now():
                tasks.append(item)
    return tasks


def reset_due_dates(tasks):
    day_limit = 0
    number = 1
    next_duedate = date.today()
    for task in tasks:
        print(f"Task {number}:  {task.data['content']}")
        number += 1
        day_limit += 1
        if day_limit >= 5:
            next_duedate += timedelta(days=+1)
            day_limit = 0
        print(f"   sending to {next_duedate}")
        due = task.data['due']
        due['date'] = next_duedate
        task.update(due=due)


def main():
    api.sync()
    tasks = get_overdue_tasks()

    reset_due_dates(tasks)
    api.commit()


if __name__ == '__main__':
    main()
