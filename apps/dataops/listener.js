import WebSocket from "ws";
import { Kafka } from "kafkajs";

console.log("Tes Demo CI/CD");

const producer = new Kafka({
  clientId: "listener",
  brokers: process.env.KAFKA_HOST.split(","),
}).producer();
await producer.connect();

const ws = new WebSocket(process.env.COINBASE_WS);
ws.on("error", console.error);
ws.on("open", function open() {
  const data = {
    type: "subscribe",
    product_ids: ["BTC-USD"],
    channels: ["matches"],
  };
  ws.send(JSON.stringify(data));
});
ws.on("message", async (data) => {
  // console.log(JSON.parse(data))
  await producer.send({
    topic: "btc_usd",
    messages: [{ value: data }],
  });
});
