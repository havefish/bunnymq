# BunnyMQ

[![Build Status](https://travis-ci.com/havefish/bunnymq.svg?branch=master)](https://travis-ci.com/havefish/bunnymq)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/bunnymq.svg)](https://pypi.python.org/pypi/bunnymq/)
[![PyPI version fury.io](https://badge.fury.io/py/bunnymq.svg)](https://pypi.python.org/pypi/bunnymq/)

Simple messaging with RabbitMQ and Python.

Head over to the [tutorial](http://havefish.github.io/bunnymq/) to get started.

This is a small library inspired by the Python standard library [queue](https://docs.python.org/3/library/queue.html) module and the [hotqueue](https://github.com/richardhenry/hotqueue) library. Primarily geared towards programmer happiness :slightly_smiling_face:

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

## Features

* Simple usage
* Automatic serialization and deserialization of Python objects
* Automatic retry while publishing
* Automatic handling of connection failures while consuming
* Automatic handling of message redeliveries because of failure to send acknowledgement at the end of processing. This is a frequent scenario for long running consumer tasks. If you have encountered this problem, do read the [details](http://havefish.github.io/bunnymq/details.html).
* Easy parallelization by starting multiple workers to share the load.


## Install

```
pip install bunnymq
```

## Requirements
* Python 3.6+
* [RabbitMQ server](https://www.rabbitmq.com/)
* [Pika](https://pika.readthedocs.io/en/stable/)
