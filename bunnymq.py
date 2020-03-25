"""Simple transparent wrapper for a small portion of Pika. It has a nice interface."""

__version__ = '0.0.1'

import pickle
from hashlib import md5

import pika


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
        if not hasattr(self, 'connection'):
            return
        
        try:
            self.connection.close()
        except Exception as e:
            print(e)

    def _declare_queue(self):
        return self.channel.queue_declare(self.queue, durable=True, arguments={'x-max-priority': self.max_priority})

    def setup(self):
        self.disconnect()
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(credentials=self.credentials, **self.conn_params))                                                
        self.channel = self.connection.channel()
        self.stream = self.channel.consume(self.queue)
        self._declare_queue()
        self.channel.basic_qos(prefetch_count=1)
        
    def _put(self, msg, priority):
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue,
            body=self.serializer.dumps(msg),
            properties=pika.BasicProperties(
                delivery_mode=2,
                priority=priority,
            )
        )
        
    def put(self, msg, priority=5):
        assert 0 < int(priority) <  self.max_priority
        
        try:
            return self._put(msg, priority)
        except Exception:
            pass
        
        self.setup()
        self._put(msg, priority)

    def handler(self, func):
        self._handler = func
        return func
    
    def error_handler(self, *errors, requeue=True):
        def wrapped(func):
            self._error_handlers.append((errors, requeue, func))
            return func
        return wrapped   
                
    def handle_error(self, e, msg):
        for errors, requeue, handler in self._error_handlers:
            
            if not isinstance(e, errors):
                continue
                
            handler(msg, e)
            
            if requeue:
                self.requeue()
            else:
                self.task_done()
            
            return
                
        self.requeue()
        raise e
            
    def requeue(self):
        try:
            self.channel.basic_reject(delivery_tag=self._method.delivery_tag, requeue=True)
        except Exception as e:
            print(e)
            self.setup()

        self._processing = False
        self._requeued = True

    def task_done(self):
        try:
            self.channel.basic_ack(delivery_tag=self._method.delivery_tag)
        except Exception as e:
            print(e)
            self.setup()

        self._processing = False
        self._requeued = False

    def _move_ahead(self):
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
            
    def consume(self):
        for msg in self:
            try:
                self.handler(msg)
            except Exception as e:
                self.handle_error(e, msg)
            else:
                self.task_done()
