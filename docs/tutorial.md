# Bunnymq Tutorial

## Connecting to RabbitMQ

Creating a queue is simple.

```python
>>> from bunnymq import Queue
>>> queue = Queue('test', host='localhost', port=5672, username='guest', password='guest')
```

This will create a queue named `bunnymq.test` on the RabbitMQ server running at `localhost:5672`.
The `username`, `password`, `host`, `port` arguments are optional; if none are given the defaults will be used.

