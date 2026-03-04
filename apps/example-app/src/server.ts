import app from "./index";
import { serve } from "bun";

const PORT = Number(process.env.PORT || 3000);

serve({
  fetch: app.fetch,
  port: PORT,
});

console.log(`example-app is running on http://localhost:${PORT}`);
