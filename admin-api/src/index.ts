import express from 'express';
import cors from 'cors';
import { authRouter }     from './routes/auth';
import { eventsRouter }   from './routes/events';
import { sessionsRouter } from './routes/sessions';
import { overviewRouter } from './routes/overview';

const app  = express();
const PORT = Number(process.env.PORT_ADMIN) || 3002;

app.use(cors({ origin: true, credentials: true }));
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'admin-api' });
});

app.use('/auth',     authRouter);
app.use('/events',   eventsRouter);
app.use('/sessions', sessionsRouter);
app.use('/overview', overviewRouter);

app.listen(PORT, () => {
  console.log(`[admin-api] listening on port ${PORT}`);
});
