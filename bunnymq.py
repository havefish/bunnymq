__version__ = '0.0.1'

import pickle

import pika


class Queue:
    max_priority = 10
    
    def __init__(self, queue, serializer=pickle, username='guest', password='guest', **conn_params):
        self.queue = queue
        self.serializer = serializer
        
        self.credentials = pika.PlainCredentials(username, password)
        self.conn_params = conn_params
        
        self.setup()
        
        self._processing = False
        self._handler = None
        self._error_handlers = []
        self._last_acked = True
        
    def disconnect(self):
        if not hasattr(self, 'connection'):
            return
        
        try:
            self.connection.close()
        except Exception as e:
            print(e)
            
    def setup(self):
        self.disconnect()
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(credentials=self.credentials, **self.conn_params))                                                
        self.channel = self.connection.channel()
        self.stream = self.channel.consume(self.queue)
        self.channel.queue_declare(self.queue, durable=True, arguments={'x-max-priority': self.max_priority})
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
            self.channel.basic_reject(delivery_tag=self._delivery_tag, requeue=True)
        except Exception as e:
            print(e)
            self.setup()

        self._processing = False

    def task_done(self):
        try:
            self.channel.basic_ack(delivery_tag=self._delivery_tag)
        except Exception as e:
            print(e)
            self.setup()

        self._processing = False

    def __next__(self):
        if self._processing:
            raise Exception('The previous message was neither marked done nor requeued.')

        try:
            r = next(self.stream)
        except StopIteration:
            self.setup()
            r = next(self.stream)

        method, _, body = r
        
        self._delivery_tag = method.delivery_tag
        self._processing = True

        return self.serializer.loads(body)

    def __len__(self):
        res = self.channel.queue_declare(self.queue, durable=True, arguments={'x-max-priority': self.max_priority})
        return res.method.message_count

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
