# Misc

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