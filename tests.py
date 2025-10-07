import unittest
from unittest.mock import MagicMock, call
from datetime import date, timedelta

from todoist_api_python.models import Task, Due

# Import from the new modules
from scheduler import (
    slice_list,
    sort_tasks,
    schedule_and_push_down,
)

# A sentinel object to detect if a keyword argument was provided
_SENTINEL = object()

# A more flexible task creator
def create_task(id, content, priority=1, due_date_str=None, is_recurring=False, due=_SENTINEL):
    if due is _SENTINEL:
        if due_date_str:
            due = Due(
                string=f"every day starting {due_date_str}" if is_recurring else due_date_str,
                date=due_date_str,
                is_recurring=is_recurring,
                timezone=None
            )
        else:
            due = None

    return Task(
        id=id,
        content=content,
        priority=priority,
        due=due,
        assignee_id=None,
        assigner_id=None,
        comment_count=0,
        is_completed=False,
        created_at='2024-01-01T12:00:00Z',
        creator_id='1',
        description='',
        labels=[],
        order=0,
        parent_id=None,
        project_id='1',
        section_id=None,
        url='',
        sync_id=None,
    )


class TestTaskSort(unittest.TestCase):

    def test_sort_emptylist(self):
        lst = []
        sort_tasks(lst)
        self.assertEqual(lst, [], "Somehow couldn't sort nothing")

    def test_sort_by_priority(self):
        urgent_task = create_task('urgent', 'urgent', priority=4)
        low_task = create_task('low', 'low', priority=1)
        lst = [low_task, urgent_task]
        sort_tasks(lst)
        self.assertEqual([t.id for t in lst], ['urgent', 'low'], "Could not sort by priority")

    def test_sort_by_due_date(self):
        old_task = create_task('old', 'old', due_date_str='2024-02-29')
        new_task = create_task('new', 'new', due_date_str='2024-03-14')
        lst = [new_task, old_task]
        sort_tasks(lst)
        self.assertEqual([t.id for t in lst], ['old', 'new'], "Could not sort by due date")

    def test_sort_by_priority_then_due_date(self):
        urgent_old_task = create_task('uo', 'uo', priority=4, due_date_str='2024-02-29')
        urgent_new_task = create_task('un', 'un', priority=4, due_date_str='2024-03-14')
        low_old_task = create_task('lo', 'lo', priority=1, due_date_str='1980-01-01')
        low_new_task = create_task('ln', 'ln', priority=1, due_date_str='2024-03-20')
        lst = [low_old_task, low_new_task, urgent_new_task, urgent_old_task]
        sort_tasks(lst)
        expected_ids = ['uo', 'un', 'lo', 'ln']
        self.assertEqual([t.id for t in lst], expected_ids, "Could not sort by priority and due date")

    def test_sort_due_is_none(self):
        task_with_due = create_task('with_due', 'with_due', due_date_str='2024-01-01')
        task_without_due = create_task('without_due', 'without_due', due=None)
        task_without_due.priority = 4
        lst = [task_with_due, task_without_due]
        sort_tasks(lst)
        self.assertEqual([t.id for t in lst], ['without_due', 'with_due'])


class TestFunctions(unittest.TestCase):

    def test_slice_normally(self):
        lst = [1, 2, 5, 10]
        result1, result2 = slice_list(lst, 3)
        self.assertEqual(result1, [1, 2, 5])
        self.assertEqual(result2, [10])

    def test_slice_with_negative_amount(self):
        lst = [1, 2, 5]
        result1, result2 = slice_list(lst, -1)
        self.assertEqual(result1, [])
        self.assertEqual(result2, lst)


class TestScheduling(unittest.TestCase):
    def setUp(self):
        self.api = MagicMock()
        self.api.update_task.return_value = True
        self.today = date(2024, 1, 1)
        self.tomorrow = self.today + timedelta(days=1)
        self.day_after = self.tomorrow + timedelta(days=1)
        self.tasks_per_day = 2
        self.ignore_tag = 'no_reschedule'

    def test_schedule_no_tasks(self):
        schedule_and_push_down(
            self.api, [], self.today, self.tasks_per_day, self.ignore_tag
        )
        self.api.get_tasks.assert_not_called()
        self.api.update_task.assert_not_called()

    def test_schedule_fit_in_one_day(self):
        tasks_to_add = [
            create_task('1', 'Task 1', priority=4, due_date_str='2023-12-31'),
            create_task('2', 'Task 2', priority=1, due_date_str='2023-12-30')
        ]
        self.api.get_tasks.return_value = []

        schedule_and_push_down(
            self.api, tasks_to_add, self.today, self.tasks_per_day, self.ignore_tag
        )

        self.api.get_tasks.assert_called_once_with(
            filter=f'! p1 & ! @{self.ignore_tag} & due on ' + self.today.strftime('%Y-%m-%d')
        )
        expected_calls = [
            call(task_id='1', due_string=self.today.strftime('%Y-%m-%d')),
            call(task_id='2', due_string=self.today.strftime('%Y-%m-%d'))
        ]
        self.api.update_task.assert_has_calls(expected_calls, any_order=True)

    def test_push_to_next_day(self):
        tasks_to_add = [
            create_task('1', 'Task 1 P4', priority=4, due_date_str='2023-12-31'),
            create_task('2', 'Task 2 P4', priority=4, due_date_str='2023-12-30'),
            create_task('3', 'Task 3 P1', priority=1, due_date_str='2023-12-29')
        ]
        self.api.get_tasks.side_effect = [[], []]

        schedule_and_push_down(
            self.api, tasks_to_add, self.today, self.tasks_per_day, self.ignore_tag
        )
        
        update_task_calls = [
            call(task_id='2', due_string=self.today.strftime('%Y-%m-%d')),
            call(task_id='1', due_string=self.today.strftime('%Y-%m-%d')),
            call(task_id='3', due_string=self.tomorrow.strftime('%Y-%m-%d'))
        ]
        self.api.update_task.assert_has_calls(update_task_calls, any_order=True)
        self.assertEqual(self.api.update_task.call_count, 3)

    def test_with_existing_tasks(self):
        existing_task = create_task('existing', 'Existing Task', priority=4, due_date_str=self.today.strftime('%Y-%m-%d'))
        tasks_to_add = [
            create_task('1', 'New Task 1 P4', priority=4, due_date_str='2023-12-31'),
            create_task('2', 'New Task 2 P1', priority=1, due_date_str='2023-12-30')
        ]
        self.api.get_tasks.side_effect = [[existing_task], [], []]
        
        schedule_and_push_down(
            self.api, tasks_to_add, self.today, self.tasks_per_day, self.ignore_tag
        )

        # The highest priority new task ('1') takes the remaining spot for today.
        # The existing task is pushed to tomorrow.
        # The lowest priority new task ('2') is also pushed to tomorrow.
        update_task_calls = [
            call(task_id='1', due_string=self.today.strftime('%Y-%m-%d')),
            call(task_id='existing', due_string=self.tomorrow.strftime('%Y-%m-%d')),
            call(task_id='2', due_string=self.tomorrow.strftime('%Y-%m-%d')),
        ]
        self.api.update_task.assert_has_calls(update_task_calls, any_order=True)
        self.assertEqual(self.api.update_task.call_count, 3)

if __name__ == '__main__':
    unittest.main()