import { Hono } from "hono";

const app = new Hono();

app.get("/", (c) => {
  return c.json({
    message:
      "halo dari example-app! (tes deployment pipeline gitlab itb (tes workflow rule))",
  });
});

export default app;
