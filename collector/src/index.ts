import express from 'express';
import cors from 'cors';
import { collectRouter } from './routes/collect';
import { originCheck } from './middleware/originCheck';

const app  = express();
const PORT = Number(process.env.PORT_COLLECTOR) || 3001;

app.use(
  cors({
    // Allow all origins at the CORS header level — the originCheck middleware
    // handles domain validation and silently drops requests from unknown origins.
    // This prevents 500s from CORS callbacks and allows proper preflight responses.
    origin: true,
    methods: ['POST', 'OPTIONS'],
  }),
);

app.use(express.json({ limit: '10kb' }));
app.use(originCheck);

app.use('/p', collectRouter);

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'collector' });
});

app.listen(PORT, () => {
  console.log(`[collector] listening on port ${PORT}`);
});
