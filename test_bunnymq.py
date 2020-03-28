import unittest

from bunnymq import Queue


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.queue = Queue('unittest')

    def tearDown(self):
        self.queue.delete()

    def test_len_of_new_queue(self):
        self.assertEqual(len(self.queue), 0)

    def test_put(self):
        self.queue.put(1)
        self.assertEqual(len(self.queue), 1)

    def test_get(self):
        self.queue.put(1)
        item = self.queue.get()
        self.assertEqual(item, 1)

    def test_get_raises(self):
        self.queue.put(1)
        self.queue.get()

        with self.assertRaises(Exception):
            self.queue.get()

    def test_task_done(self):
        self.queue.put(1)
        self.queue.get()
        self.queue.task_done()
        self.assertEqual(len(self.queue), 0)

    def test_requeue(self):
        self.queue.put(1)
        item = self.queue.get()
        self.queue.requeue()
        self.assertEqual(self.queue.get(), item)
