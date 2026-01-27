import express from "express";
import { publishOrderCreated } from "./queues/publisher";

const app = express();
app.use(express.json());

app.post("/orders", async (req, res) => {
  const orderId = req.body?.id ?? "order-1";
  await publishOrderCreated({ orderId });
  res.json({ ok: true, orderId });
});

app.listen(3000, () => {
  console.log("Node service listening on 3000");
});
