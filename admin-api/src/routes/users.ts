import { Router, Request, Response } from 'express';
import bcrypt from 'bcrypt';
import { pgPool } from '../lib/postgres';

export const usersRouter = Router();

// GET /users — list all admin users
usersRouter.get('/', async (_req: Request, res: Response): Promise<void> => {
  const { rows } = await pgPool.query(
    `SELECT id, email, name, role, created_at FROM admin_users ORDER BY created_at ASC`,
  );
  res.json({ users: rows });
});

// POST /users — create a new admin user
usersRouter.post('/', async (req: Request, res: Response): Promise<void> => {
  const { email, name, password, role } = req.body as {
    email?: string; name?: string; password?: string; role?: string;
  };

  if (!email || !password) {
    res.status(400).json({ error: 'email and password are required' });
    return;
  }

  const passwordHash = await bcrypt.hash(password, 10);

  try {
    const { rows } = await pgPool.query(
      `INSERT INTO admin_users (email, name, password_hash, role)
       VALUES ($1, $2, $3, $4)
       RETURNING id, email, name, role, created_at`,
      [email.toLowerCase().trim(), name || '', passwordHash, role || 'admin'],
    );
    res.status(201).json({ user: rows[0] });
  } catch (err: any) {
    if (err.code === '23505') {
      res.status(409).json({ error: 'A user with that email already exists' });
    } else {
      res.status(500).json({ error: 'Failed to create user' });
    }
  }
});

// DELETE /users/:id — remove a user
usersRouter.delete('/:id', async (req: Request, res: Response): Promise<void> => {
  const id = parseInt(req.params.id);

  // Prevent deleting the last user
  const { rows: countRows } = await pgPool.query(`SELECT COUNT(*) FROM admin_users`);
  if (parseInt(countRows[0].count) <= 1) {
    res.status(400).json({ error: 'Cannot delete the last user' });
    return;
  }

  await pgPool.query(`DELETE FROM admin_users WHERE id = $1`, [id]);
  res.json({ ok: true });
});
