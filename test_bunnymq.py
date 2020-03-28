import unittest

from bunnymq import Queue


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.queue = Queue('unittest')

    def tearDown(self):
        self.queue.delete()

    def test_queue_name(self):
        self.assertEqual(self.queue.queue, 'bunnymq.unittest')

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

    def test_auto_setup(self):
        self.queue.disconnect()
        self.queue.put(1)

    def test_iterable(self):
        self.queue.put(1)
        it = iter(self.queue)
        self.assertEqual(next(it), 1)

    def test_handle_ack_failure(self):
        self.queue.put(1)
        self.queue.put(2)

        item = self.queue.get()
        self.assertEqual(item, 1)

        self.queue.disconnect()  # simulates a connection loss

        self.queue.task_done()

        item = self.queue.get()
        self.assertEqual(item, 2)  # 1 will be silently skipped

    def test_handle_requeue_failure(self):
        self.queue.put(1)
        self.queue.put(2)

        item = self.queue.get()
        self.assertEqual(item, 1)

        self.queue.disconnect()  # simulates a connection loss

        self.queue.requeue()

        item = self.queue.get()
        self.assertEqual(item, 1)

    def test_clear(self):
        self.queue.put(1)
        self.assertEqual(len(self.queue), 1)

        self.queue.clear()
        self.assertEqual(len(self.queue), 0)
