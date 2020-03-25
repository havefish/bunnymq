# Bunnymq

Talk to RabbitMQ in Python.

The official Python library to interact with RabbitMQ is [Pika](https://pika.readthedocs.io/en/stable/). However, I have never been a big fan of the interface Pika provides. It is too bloated for simple tasks. This wrapper tries to provide a nicer interface for a _very small albeit useful_ portion of the aforementioned library.

Pull requests that are aimed at

* making the code cleaner, more understandable and pythonic
* better abstraction and interface
* better implemetation
* bug fixes
* better documentation

are most welcome. 

> When in doubt always refer to the [RabbitMQ](https://www.rabbitmq.com/getstarted.html) guides and the [Pika](https://pika.readthedocs.io/en/stable/) docs.

## Features

* Automatic serialization and deserialization of messages. Using a custom serializer is almost [trivial](#custom-serializers).
* Multiple consumer patterns.
* Automatic retry while publishing
* Automatic handling of connection failures while consuming
* Automatic handling of message redeliveries because of failure to send acknowledgement at the end of processing. This is a frequent scenario for long running consumer tasks. If you have encountered this problem, do read the [details](#redelivery-issues).
* Easy parallelization by starting multiple workers to [share the load](#multiple-consumers). No two consumers will ever get the same message.

It is very important that the code be readable. Pull requests that are aimed at making the code cleaner and more understandable are most welcome.

## Install

```
pip install bunnymq
```

## Usage

Wheather you want a producer or a consumer, you create the following object

```python
>>> from bunnymq import Queue
>>> queue = Queue('test') 
```

This creates a queue named `test` assuming default values for other parameters listed below.

1. `username` defaults to `'guest'`
2. `password` defaults to `'guest'`
3. `serializer` defaults to `pickle` module.
3. Any keyword arguments that `pika.ConnectionParameters` takes _except_ the parameter `credentials`.

> This library works with the default exchange

> If a queue exists in the broker with the same name but different properties (created by some other means), an exception will be raised.

There is only one simple way to publish a message to the queue, the `put` method. However, there are multiple patterns available for consumers

* [Basic interface](#basic-interface)
* [Iterable interface](#iterable-interface)
* [Decorator interface](#decorator-interface) (recommended)

These are described below.

### Basic Interface
#### Put

```python
>>> queue.put({'a': 1})
```
The message is automatically serialized.

The queue, by default, is a priority queue with priorities ranging from 1 (low) through 10 (high). By default the value is 5. To put a message a with a custom priority,
```python
>>> queue.put({'b': 1}, priority=8)
```
This message will be consumed before the ones with lower priority.
#### Get

```python
>>> queue.get()
{'a': 1}
```
The message is automatically deserialized.

```python
>>> q.get()
```
This will raise an exception:
```python
Exception: The previous message was neither marked done nor requeued.
```

#### Mark done
```python
>>> queue.task_done()
```

This informs the broker that message has been successfully processed. This may also be used where the message was not sucessfully processed but it is _not_ to be retried.

> The semantics of this method is somewhat different from the one in `queue.Queue` in the standard library, in that there is no `queue.join` in our case that is waiting for invocation of `task_done`.

#### Requeue
```python
>>> queue.requeue()
```

This informs the broker that the message was not sucessfully processed and should be redelivered so that it can be retried.

#### Queue size
```python
>>> len(queue)
2
```

> Python standard library `queue` module has a `Queue.qsize` method and that is the [right] choice. However `len` is convenient. This may change in future.

### Iterable Interface

The `Queue` class implemets iterable protocol, namely the `__iter__` method, which enables the following:

```python
for msg in queue:
    try:
        # handle the message
    except NonRetriableError:
        # do some logging, alerting ...
        queue.task_done()
    except RetriableError:
        # do some logging, alerting ...
        queue.requeue()
    except Exception:
        raise
    else:
        queue.task_done()
```

### Decorator Interface
This one is the __recommended__ usage because it is the cleanest.

```python
@queue.on('message')  # <-- marked done automatically, if there are no errors
def process(msg):
    pass


@queue.on('error', NotFound, NotNeeded, requeue=False)  # <-- marked done automatically
def _(msg, e):
    # log the event
    pass


@queue.on('error', BlockedContent, requeue=False)  # <-- marked done automatically
def _(msg, e):
    # send an alert and log the event
    pass


@queue.on('error', RateLimited)  # <-- requeued automatically
def _(msg, e):
    # log the event
    pass


if __name__ == '__main__':
    queue.consume()

```

> Any number of error handlers can be registered. In the _Iterable interface_ this would make the try/except block extremely ugly.

#### Workflow
The `queue` object has an `on` method with which we can register handlers for two types of events:

1. `'message'`: bound to a single callable, that processes the message
2. `'error'`: bound to a list of callables, that handle the errors. The error handlers allow us to capture and process **domain specific exceptions**.
    
Once a message is consumed, the `'message'` handler is invoked passing the message

1. if there are no exceptions the message is marked done.
2. If there are errors, the appropriate handler is invoked, depending on the type of the raised exception. The message is marked done or requeued depending on the `requeue` argument. By default it is `True`.
3. If none of the handlers match, the message is requeued and the exception is re-raised.

## Custom Serializers
A serializer is any object that implements two methods:
1. `dumps` returns `str`/`bytes`
2. `loads` that takes `bytes`. 

Hence `json` module can be a drop in replacement.

```python
>>> import json
>>> queue = Queue('test', serializer=json)
```

Here is an abstract class.

```python
class MySerializer:
    def dumps(self, msg) -> bytes:
        raise NotImplementedError

    def loads(self, content:bytes):
        raise NotImplementedError
```

## Multiple Consumers
Let `consumer.py` be the module that can be run as a main program.

```
python consumer.py
```
Alternatively, the module exists inside a package `pkg`, then:

```
python -m pkg.consumer
```

This starts a worker. To start another one, open another terminal and invoke this again. Now you have two consumers.

If the application is containeried, the consumers can be run in the background and scaling up and down is trivial with [docker-compose](https://docs.docker.com/compose/).

## Redelivery Issues

Pika [recommends](https://www.rabbitmq.com/reliability.html#consumer-side) the consumers be designed to be idempotent.

> In the event of network failure (or a node failure), messages can be redelivered, and consumers must be prepared to handle deliveries they have seen in the past.

This is important because if the task takes time and the connection has closed by the time it finishes, the acknoledgement cannot be sent. The [reason](https://www.rabbitmq.com/confirms.html#consumer-acks-delivery-tags) being

> Because delivery tags are scoped per channel, deliveries must be acknowledged on the same channel they were received on.

Assuming the consumer is not idempotent, in case of redelivery of such a message, it should be handled before the consumer recieves it again.

Two situations arise:

1. The long running task completes sucessfully and wants to acknoledge. But the connection has closed and the new connection (and a new channel) won't accept the old delivery tag.
2. The long running task encounters error and wants to requeue. But the connection has closed and the new connection (and a new channel) won't accept the old delivery tag.

Unacked messages are redelivered by default, so the 2nd situation should not be a problem. However, if one wants to solve the 1st situation, it has to be kept in mind that the consumer might have explicitly requested a requeue.

**The current implementation addresses both the situations.**
