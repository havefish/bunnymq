'''Simple messaging with RabbitMQ and Python.'''

__version__ = '0.0.7'

import logging
import pickle
import time
from hashlib import md5

import pika

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

Errors = (
    pika.exceptions.ConnectionClosed,
    pika.exceptions.ChannelClosed,
    pika.exceptions.ChannelWrongStateError,
)


class Queue:
    max_priority = 10
    
    def __init__(self, name, host='localhost', port=5672, vhost='/', username='guest', password='guest', max_retries=100, retry_interval=5):
        name = str(name).strip()
        assert len(name) < 200, f'Queue name too long: {name!r}'

        self.queue = f'bunnymq.{name}'

        self.host = host
        self.port = port
        self.vhost = vhost
        self.credentials = pika.PlainCredentials(username, password)

        self.max_retries = int(max_retries)
        assert self.max_retries > 0, f'max retries should be > 0, given {self.max_retries!r} times'

        self.retry_interval = int(retry_interval)
        assert self.retry_interval > 0, f'retry interval should be > 0, given {self.retry_interval!r} sec'
        
        self.setup()
        
        # registered worker callable
        self._worker = None

        # flags
        self._processing = False
        self._last_msg_hash = None
        self._requeued = False
        
    def disconnect(self):
        try:
            self.connection.close()
        except Exception as e:
            log.debug(e)

    def _declare_queue(self):
        return self.channel.queue_declare(self.queue, durable=True, arguments={'x-max-priority': self.max_priority})

    def _setup(self):
        self.disconnect()

        parameters = pika.ConnectionParameters(credentials=self.credentials, host=self.host, port=self.port, virtual_host=self.vhost)
        self.connection = pika.BlockingConnection(parameters=parameters)                                                
        self.channel = self.connection.channel()

        self._declare_queue()
        self.channel.basic_qos(prefetch_count=1)
        self.channel.confirm_delivery()

        self.stream = self.channel.consume(self.queue)

    def setup(self):
        for _ in range(self.max_retries):
            try:
                return self._setup()
            except Errors as e:
                log.error(f'{e}, retrying in 2 secs.')
                time.sleep(self.retry_interval)

        raise Exception('Max retries exceeded.')
        
    def _put(self, msg, priority):
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue,
            body=pickle.dumps(msg),
            properties=pika.BasicProperties(delivery_mode=2, priority=priority),
            mandatory=True,
        )
        
    def put(self, msg, priority=5):
        assert 0 < int(priority) <  self.max_priority

        try:
            return self._put(msg, priority=priority)
        except Errors as e:
            log.debug(e)
        
        self.setup()
        self._put(msg, priority=priority)

    def requeue(self):
        try:
            self.channel.basic_reject(delivery_tag=self._method.delivery_tag, requeue=True)
        except Errors as e:
            log.debug(e)
            self.setup()

        self._processing = False
        self._requeued = True

    def task_done(self):
        try:
            self.channel.basic_ack(delivery_tag=self._method.delivery_tag)
        except Errors as e:
            log.debug(e)
            self.setup()

        self._processing = False
        self._requeued = False

    def _move_ahead(self):
        log.debug('Moving ahead')

        if self._processing:
            raise Exception('The previous message was neither marked done nor requeued.')

        try:
            r = next(self.stream)
        except StopIteration:
            self.setup()
            r = next(self.stream)

        self._method, _, self._body = r

    @property
    def _msg_hash(self):
        return md5(self._body).hexdigest()

    @property
    def _got_old_msg(self):
        return all([
            self._method.redelivered,
            self._msg_hash == self._last_msg_hash,
            not self._requeued,  # an explicitly requeued message is considered new
        ])

    def __next__(self):
        self._move_ahead()

        if self._got_old_msg:
            log.debug('Got old message')
            self.task_done()
            self._move_ahead()

        self._processing = True
        self._last_msg_hash = self._msg_hash
        return pickle.loads(self._body)

    def __len__(self):
        return self._declare_queue().method.message_count

    def get(self):
        return next(self)
    
    def __iter__(self):
        while True:
            yield next(self)

    def worker(self, func):
        self._worker = func
        return func
            
    def consume(self):
        if self._worker is None:
            raise Exception('register a worker function')

        for msg in self:
            self._worker(msg)

    def clear(self):
        try:
            self.channel.queue_purge(queue=self.queue)
        except Errors as e:
            log.debug(e)
            self.setup()
            self.channel.queue_purge(queue=self.queue)

    def delete(self):
        try:
            self.channel.queue_delete(queue=self.queue)
        except Errors as e:
            log.debug(e)
            self.setup()
            self.channel.queue_delete(queue=self.queue)

        self.disconnect()
