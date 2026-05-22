import express from 'express';
import cors from 'cors';
import { collectRouter } from './routes/collect';
import { originCheck } from './middleware/originCheck';

const app = express();
const PORT = Number(process.env.PORT_COLLECTOR) || 3001;
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || '')
  .split(',')
  .map((o) => o.trim())
  .filter(Boolean);

app.use(
  cors({
    origin: (origin, callback) => {
      // Allow requests with no origin (e.g. server-to-server, curl in dev)
      if (!origin) return callback(null, true);
      if (ALLOWED_ORIGINS.length === 0 || ALLOWED_ORIGINS.includes(origin)) {
        return callback(null, true);
      }
      callback(new Error('Not allowed by CORS'));
    },
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
