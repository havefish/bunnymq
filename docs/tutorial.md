# Bunnymq Tutorial

## Connecting to RabbitMQ

Creating a queue is simple.

```python
>>> from bunnymq import Queue
>>> queue = Queue('test', host='localhost', port=5672, username='guest', password='guest')
```

This will create a queue named `bunnymq.test` on the RabbitMQ server running at `localhost:5672`.
The `username`, `password`, `host`, `port` arguments are optional; if none are given the defaults will be used.


## Putting Items onto the Queue

You can have one (or many) Python programs pushing to the queue using `Queue.put`

```python
>>> queue.put(1)
>>> queue.put('hello')
>>> queue.put({'a': 1})
```

You can push more than one item onto the queue at once:

```python
>>> queue.put(1, 2, None)
```

You can push any python object that can be [pickled](http://docs.python.org/library/pickle.html). For example:

```python
>>> import datetime
>>> queue.put(datetime.now())
```

## Getting Items off the Queue
You can have one (or many) Python programs pulling items off the queue using `Queue.get`

```python
>>> queue.get()
1
```

If you try again,

```python
>>> q.get()
```
This will raise an exception:
```python
Exception: The previous message was neither marked done nor requeued.
```
The server needs to know what happened with the message you just pulled. This brings us to the topic of [consumer acknowledement](https://www.rabbitmq.com/confirms.html).
