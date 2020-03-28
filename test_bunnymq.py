import unittest

from bunnymq import Queue


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.queue = Queue('unittest')

    def tearDown(self):
        del self.queue

    def test_nothing(self):
        pass
