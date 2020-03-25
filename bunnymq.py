"""Simple transparent wrapper for a small portion of Pika. It has a nice interface."""

__version__ = '0.0.2'

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
)


class Queue:
    max_priority = 10
    
    def __init__(self, queue, serializer=pickle, username='guest', password='guest', **conn_params):
        self.queue = queue
        self.serializer = serializer
        
        self.credentials = pika.PlainCredentials(username, password)
        self.conn_params = conn_params
        
        self.setup()
        
        # registered callables
        self._handler = None
        self._error_handlers = []

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

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(credentials=self.credentials, **self.conn_params))                                                
        self.channel = self.connection.channel()

        self._declare_queue()
        self.channel.basic_qos(prefetch_count=1)

        self.stream = self.channel.consume(self.queue)

    def setup(self):
        while True:
            try:
                return self._setup()
            except Errors as e:
                log.error(f'{e}, retrying in 2 secs.')
                time.sleep(2)
        
    def _put(self, msg, **kwargs):
        body = self.serializer.dumps(msg)
        properties = pika.BasicProperties(delivery_mode=2, **kwargs)
        self.channel.basic_publish(exchange='', routing_key=self.queue, body=body, properties=properties)
        
    def put(self, msg, priority=5, **kwargs):
        assert 0 < int(priority) <  self.max_priority

        func = lambda: self._put(msg, priority=priority, **kwargs)
        
        try:
            return func()
        except Errors as e:
            log.debug(e)
        
        self.setup()
        func()

    def on(self, event, *errors, requeue=True):
        e = event.strip().lower()

        if e == 'message':
            return self._h

        if e == 'error':
            return self._errh(errors, requeue)

        raise Exception(f"event must be one of {'message', 'error'}, given {e!r}")

    def _h(self, func):
        self._handler = func
        return func
    
    def _errh(self, errors, requeue):
        def wrapped(func):
            self._error_handlers.append((errors, requeue, func))
            return func
        return wrapped   
                
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
        return self.serializer.loads(self._body)

    def __len__(self):
        return self._declare_queue().method.message_count

    def get(self):
        return next(self)
    
    def __iter__(self):
        while True:
            yield next(self)

    def _handle_error(self, e, msg):
        for errors, requeue, handler in self._error_handlers:
            
            if not isinstance(e, errors):
                continue

            log.debug(f'Error {e!r} is of type {errors!r}')
                
            handler(msg, e)
            
            if requeue:
                self.requeue()
            else:
                self.task_done()
            
            return
                
        self.requeue()
        raise e
            
    def consume(self):
        if self._handler is None:
            raise Exception('consume needs a message handler')

        for msg in self:
            try:
                self._handler(msg)
            except Exception as e:
                log.debug(e)
                self._handle_error(e, msg)
            else:
                self.task_done()
