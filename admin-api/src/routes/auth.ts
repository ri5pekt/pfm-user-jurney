import { Router } from 'express';
import jwt from 'jsonwebtoken';

export const authRouter = Router();

authRouter.post('/login', (req, res): void => {
  const { email, password } = req.body as { email?: string; password?: string };

  const validEmail    = process.env.ADMIN_EMAIL    || 'admin@admin.com';
  const validPassword = process.env.ADMIN_PASSWORD || 'admin';

  if (!email || !password || email !== validEmail || password !== validPassword) {
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
