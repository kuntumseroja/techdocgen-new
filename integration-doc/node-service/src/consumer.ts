import amqplib from "amqplib";

export async function startConsumer() {
  const connection = await amqplib.connect("amqp://localhost");
  const channel = await connection.createChannel();

  const queue = "order-created";
  await channel.assertQueue(queue, { durable: true });
  await channel.consume(queue, (msg) => {
    if (!msg) {
      return;
    }
    const body = msg.content.toString("utf-8");
    console.log("order-created:", body);
    channel.ack(msg);
  });
}
