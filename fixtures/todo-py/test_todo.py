import unittest

from todo import TodoList


class TestTodoList(unittest.TestCase):
    def test_add_assigns_incrementing_ids(self):
        tl = TodoList()
        self.assertEqual(tl.add("a"), 1)
        self.assertEqual(tl.add("b"), 2)

    def test_complete_marks_done(self):
        tl = TodoList()
        i = tl.add("x")
        self.assertTrue(tl.complete(i))
        self.assertTrue(tl.list()[0].done)

    def test_complete_missing_returns_false(self):
        tl = TodoList()
        self.assertFalse(tl.complete(99))


if __name__ == "__main__":
    unittest.main()
