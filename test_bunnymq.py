import unittest

from bunnymq import Queue


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.queue = Queue('unittest')

    def tearDown(self):
        self.queue.delete()

    def test_len_of_new_queue(self):
        self.assertEqual(len(self.queue), 0)

    def test_get(self):
        self.queue.put(1)
        item = self.queue.get()
        self.assertEqual(item, 1)
