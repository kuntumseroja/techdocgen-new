import amqplib from "amqplib";

export async function publishOrderCreated(payload: { orderId: string }) {
  const connection = await amqplib.connect("amqp://localhost");
  const channel = await connection.createChannel();
  const exchange = "orders";
  const routingKey = "order.created";

  await channel.assertExchange(exchange, "topic", { durable: true });
  channel.publish(exchange, routingKey, Buffer.from(JSON.stringify(payload)));

  await channel.close();
  await connection.close();
}
