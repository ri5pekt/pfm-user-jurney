import express from 'express';

const app = express();
const PORT = Number(process.env.PORT_ADMIN) || 3002;

app.use(express.json());

// ─── Health ───────────────────────────────────────────────────────────────────
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'admin-api' });
});

// ─── Auth & dashboard routes added in Phase 2 ─────────────────────────────────
// POST /auth/login
// GET  /journeys
// GET  /journeys/graph
// GET  /funnels
// GET  /traffic-sources

app.listen(PORT, () => {
  console.log(`[admin-api] listening on port ${PORT}`);
});
