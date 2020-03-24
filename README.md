# Bunnymq

Simple transparent wrapper for a small subset of Pika.

# Install

```
pip install bunnymq
```

If `pika` works, this will also work.

## Usage

Wheather you want a producer or a consumer, you create the following object

```python
>>> from bunnymq import Queue
>>> queue = Queue('test') 
```

This creates a queue named `test` assuming default values for other parameters listed below.

1. `username` defaults to `'guest'`
2. `password` defaults to `'guest'`
3. `serializer` defaults to `pickle` module. This can be any object that implements the interface `dumps` and `loads`. Hence `json` module will also work out of the box.
3. Any keyword arguments that `pika.ConnectionParameters` takes _except_ the parameter `credentials`.


### Basic Interface
#### Put

```python
>>> queue.put({'a': 1})
```
The message is automatically serialized.
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

This sends a `basic_ack`.

> The semantics of this method is somewhat different from the one in `queue.Queue` in the standard library, in that there is no `queue.join` in our case that is waiting for invocation of `task_done`.

#### Requeue
```python
>>> queue.requeue()
```

This sends a `basic_reject` with `requeue=True`

#### Queue size
```python
>>> len(queue)
2
```

### Iterable Interface

```python
for msg in queue:
    try:
        # handle the message
    except NonRetirableError:
        # do some logging, alerting ...
        queue.task_done()
    except RetirableError:
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
@queue.handler
def process(msg):
    pass


@queue.error_handler(E1, E2, requeue=False)
def non_retirable_error_1(msg, e):
    pass


@queue.error_handler(E3, E4, requeue=False)
def non_retirable_error_2(msg, e):
    pass


@queue.error_handler(E5, E6, ...)
def retirable_error(msg, e):
    pass

```

> Any number of error handlers can be registered. In the _Iterable interface_ this would make the try/except block extremely ugly.

#### Workflow
The `queue` object has two methods that are registration decorators:

1. `queue.handler`: bound to a single callable, that processes the message
2. `queue.error_handler`: bound to a list of callables, that handle the errors 
    
Once a message is consumed, `queue.handler` callable is invoked passing the message

1. if there are no exceptions the message is marked done.
2. If there are errors, the appropriate handler is invoked, depending on the type of the raised exception. The message is marked done or requeued depending on the `requeue` argument. By default it is `True`.
3. If none of the handlers match, the message is requeued and the exception is raised.
