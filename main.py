import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from todoist_api_python.api import TodoistAPI

import config
import scheduler

logging.basicConfig(level=logging.DEBUG)


def main():
    """Main function to run the Todoist scheduler."""
    api = TodoistAPI(config.TODOIST_API_KEY)
    today = datetime.now(ZoneInfo(config.USER_TZ)).date()

    logging.info("Getting overdue tasks...")
    overdue_tasks = api.get_tasks(
        filter=f"overdue & ! p1 & ! @{config.IGNORE_TASK_TAG}"
    )

    today_str = today.strftime("%Y-%m-%d")
    # filter out tasks that are due today because Todoist has a weird idea
    # about what overdue means
    overdue_tasks = [
        t for t in overdue_tasks if t.due and t.due.date != today_str
    ]

    scheduler.schedule_and_push_down(
        api, overdue_tasks, today, config.TASKS_PER_DAY, config.IGNORE_TASK_TAG
    )

    logging.info("Scheduling complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)