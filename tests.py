import unittest

from typing import List

from todoist_api_python.models import Task, Due

# TODO: consider making a module or class or whatever
from main import sort_tasks

def create_blank_task():
    
    due = Due('',
		 False,
		 '',
		 None,
		 None)
    task = Task(
        'assignedto',
        'assignedby',
		 0,
		 False,
		 'a test task',
		 'created on',
		 'created by',
		 'describe this task',
		 due,
		 'the id',
		 [],
		 0,
		 None,
		 0,
		 '',
		 None,
		 '',
		 None)

    return task


class TestTaskSort(unittest.TestCase):
    
    def test_sort_emptylist(self):

        list = []
        sort_tasks(list)
        
        self.assertEqual(list, [], "Somehow couldn't sort nothing")

    def test_sort_by_priority(self):

        urgent_task = create_blank_task()
        urgent_task.priority = 4
        
        low_task = create_blank_task()
        low_task.priority = 1

        list = [low_task, urgent_task]

        sort_tasks(list)

        expected = [urgent_task, low_task]
        
        self.assertEqual(list, expected,
                         "Could not sort by priority")

    def test_sort_by_due_date(self):
        
        old_task = create_blank_task()
        old_task.due.date = '2024-02-29'

        new_task = create_blank_task()
        new_task.due.date = '2024-03-14'

        list = [new_task, old_task]

        sort_tasks(list)

        expected = [old_task, new_task]

        self.assertEqual(list, expected,
                         "Could not sort by priority")

    def test_sort_by_priority_then_due_date(self):

        urgent_old_task = create_blank_task()
        urgent_old_task.priority = 4
        urgent_old_task.due.date = '2024-02-29'

        urgent_new_task = create_blank_task()
        urgent_new_task.priority = 4
        urgent_new_task.due.date = '2024-03-14'
        
        low_old_task = create_blank_task()
        low_old_task.priority = 1
        low_old_task.due.date = '1980-01-01'

        low_new_task = create_blank_task()
        low_new_task.priority = 1
        low_new_task.due.date = '2024-03-20'

        list = [low_old_task, low_new_task, urgent_new_task, urgent_old_task]

        sort_tasks(list)

        expected = [urgent_old_task, urgent_new_task, low_old_task, low_new_task]
        
        self.assertEqual(list, expected,
                         "Could not sort by priority and due date")

    def test_sort_due_is_none(self):
        
        task = create_blank_task()
        task.due = None
        
        list = [task]
        
        sort_tasks(list)

        expected = [task]
        
        self.assertEqual(list, expected,
                         "Could not sort task with None due date")

    def test_sort_bang_goes_last(self):
        
        daily_task = create_blank_task()
        daily_task.due.string = 'every day'

        repeating_task = create_blank_task()
        repeating_task.due.string = 'every! three weeks'
        
        list = [repeating_task, daily_task]
        
        sort_tasks(list)
        
        expected = [daily_task, repeating_task]
        
        self.assertEqual(list, expected,
                         "Could not sort tasks without ! to front")


if __name__ == '__main__':
    unittest.main()