'''Simple messaging with RabbitMQ and Python.'''

__version__ = '0.0.14'

import logging
import pickle
import time

import pika

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

logging.getLogger('pika').setLevel(logging.CRITICAL)



class BunnyError(Exception):
    pass


class StatusUnknown(BunnyError):
    pass


class DumpError(BunnyError):
    pass


class LoadError(BunnyError):
    pass


class Queue:
    max_priority = 10
    heartbeat_interval = 600  # 10 min, default 1 min is too low
    
    def __init__(self, name, serializer=pickle, host='localhost', port=5672, vhost='/', username='guest', password='guest', max_retries=100):
        name = str(name).strip()
        assert len(name) < 200, f'Queue name too long: {name!r}'
        self.queue = f'bunnymq.{name}'

        self.serializer = serializer

        self.host = host
        self.port = port
        self.vhost = vhost
        self.credentials = pika.PlainCredentials(username, password)

        self.max_retries = int(max_retries)
        assert self.max_retries > 0, f'max retries should be > 0, given {self.max_retries!r} times'

        self.setup()
        
        # registered worker callable
        self._worker = None

        # flags
        self._processing = False

    def __repr__(self):
        return f'Queue({self.queue!r}, host={self.host!r}, port={self.port!r}, vhost={self.vhost!r})'

    def disconnect(self):
        try:
            self.connection.close()
        except Exception as e:
            log.debug(e)

    def _declare_queue(self):
        return self.channel.queue_declare(self.queue, durable=True, arguments={'x-max-priority': self.max_priority})

    def _setup(self):
        log.info(f'Setting up {self!r}')
        self.disconnect()

        parameters = pika.ConnectionParameters(
            credentials=self.credentials,
            host=self.host, port=self.port,
            virtual_host=self.vhost,
            heartbeat=self.heartbeat_interval,
        )
        self.connection = pika.BlockingConnection(parameters=parameters)                                                
        self.channel = self.connection.channel()

        self._declare_queue()
        self.channel.basic_qos(prefetch_count=1)
        self.channel.confirm_delivery()

        self.stream = self.channel.consume(self.queue)

    def _dump(self, msg):
        if not self.serializer:
            return msg

        try:
            return self.serializer.dumps(msg)
        except Exception as e:
            raise DumpError(e)

    def _load(self, body):
        if not self.serializer:
            return body

        try:
            return self.serializer.loads(body)
        except Exception as e:
            raise LoadError(e)

    def setup(self):
        self._retry(self._setup)
        
    def _put(self, msg, priority):
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue,
            body=self._dump(msg),
            properties=pika.BasicProperties(delivery_mode=2, priority=priority),
            mandatory=True,
        )
        
    def put(self, msg, priority=5):
        assert 0 < int(priority) <  self.max_priority
        self._setup_retry(self._put, msg, priority=priority)

    def requeue(self, priority=5):
        self.task_done()
        self.put(self._msg, priority=priority)

        self._processing = False

    def task_done(self):
        try:
            self.channel.basic_ack(delivery_tag=self._method.delivery_tag)
        except pika.exceptions.AMQPError as e:
            log.error(e)
            self.setup()

        self._processing = False

    def __next__(self):
        if self._processing:
            raise StatusUnknown('The previous message was neither marked done nor requeued.')

        self._method, _, body = self._setup_retry(next, self.stream)
        self._processing = True
        self._msg = self._load(body)

        return self._msg

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
        self._setup_retry(self.channel.queue_purge, queue=self.queue)

    def delete(self):
        self._setup_retry(self.channel.queue_delete, queue=self.queue)
        self.disconnect()

    def _retry(self, func, *args, _onerr=None, **kwargs):
        for _ in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except BunnyError as e:
                raise
            except Exception as e:
                log.error(f'{e}, retrying')
                _e = e
                _onerr and _onerr()

        raise Exception(f'Max retries exceeded.\n{_e}')

    def _setup_retry(self, func, *args, **kwargs):
        return self._retry(func, *args, _onerr=self.setup, **kwargs)
