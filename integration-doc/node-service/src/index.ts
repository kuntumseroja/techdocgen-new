import express from "express";
import { publishOrderCreated } from "./publisher";
import { startConsumer } from "./consumer";

const app = express();
app.use(express.json());

app.post("/orders", async (req, res) => {
  const orderId = req.body?.id ?? "order-1";
  await publishOrderCreated({ orderId });
  res.json({ ok: true, orderId });
});

startConsumer().catch((err) => console.error(err));

app.listen(3001, () => {
  console.log("Integration demo Node service on 3001");
});
