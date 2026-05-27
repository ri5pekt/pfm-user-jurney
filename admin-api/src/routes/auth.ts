import { Router } from 'express';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcrypt';
import { pgPool } from '../lib/postgres';

export const authRouter = Router();

authRouter.post('/login', async (req, res): Promise<void> => {
  const { email, password } = req.body as { email?: string; password?: string };

  if (!email || !password) {
    res.status(401).json({ error: 'Invalid credentials' });
    return;
  }

  // ── 1. Check DB users first ───────────────────────────────────────
  try {
    const { rows } = await pgPool.query(
      `SELECT id, email, password_hash FROM admin_users WHERE email = $1 LIMIT 1`,
      [email.toLowerCase().trim()],
    );

    if (rows.length > 0) {
      const match = await bcrypt.compare(password, rows[0].password_hash);
      if (!match) {
        res.status(401).json({ error: 'Invalid credentials' });
        return;
      }
      const token = jwt.sign(
        { sub: rows[0].email, id: rows[0].id },
        process.env.JWT_SECRET || 'dev_secret',
        { expiresIn: '24h' },
      );
      res.json({ token });
      return;
    }
  } catch {
    // DB not ready yet or table missing — fall through to env var check
  }

  // ── 2. Fallback: env var credentials (used before any DB users exist) ──
  const validEmail    = process.env.ADMIN_EMAIL    || 'admin@admin.com';
  const validPassword = process.env.ADMIN_PASSWORD || 'admin';

  if (email !== validEmail || password !== validPassword) {
    res.status(401).json({ error: 'Invalid credentials' });
    return;
  }

  const token = jwt.sign(
    { sub: email },
    process.env.JWT_SECRET || 'dev_secret',
    { expiresIn: '24h' },
  );
  res.json({ token });
});
