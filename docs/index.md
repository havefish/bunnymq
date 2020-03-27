# BunnyMQ

Simple messaging with RabbitMQ and Python.

Basic Usage:

```python
>>> queue = Queue('test')

>>> queue.put(1)
>>> queue.put('hello', priority=8)
>>> queue.put({'a': 1})

>>> queue.get()
'hello'
>>> queue.task_done()

>>> queue.get()
1
>>> queue.requeue()
```

Iterating over a queue indefinitely, waiting if nothing is available:

```python
>>> for item in queue:
...     print(item)
...     queue.task_done()
```

Go through the [tutorial](tutorial.md) for detailed usage.

## Installation
```
pip install bunnymq
```

## Requirements
* Python 3.6+
* [RabbitMQ server](https://www.rabbitmq.com/)
* [Pika](https://pika.readthedocs.io/en/stable/)
