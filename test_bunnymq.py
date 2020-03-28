import unittest

from bunnymq import Queue


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.queue = Queue('unittest')

    def tearDown(self):
        del self.queue

    def test_len_of_new_queue(self):
        self.assertEqual(len(self.queue), 0)
