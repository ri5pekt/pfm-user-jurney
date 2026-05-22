import { Request, Response, NextFunction } from 'express';

const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || '')
  .split(',')
  .map((o) => o.trim())
  .filter(Boolean);

export function originCheck(req: Request, res: Response, next: NextFunction): void {
  // Only enforce on the tracking endpoint
  if (req.path !== '/' || req.method !== 'POST') {
    return next();
  }

  // Skip in dev if no origins configured
  if (ALLOWED_ORIGINS.length === 0) {
    return next();
  }

  const origin = req.headers.origin || '';
  if (ALLOWED_ORIGINS.includes(origin)) {
    return next();
  }

  // Reject silently — don't reveal enforcement to scrapers
  res.status(204).end();
}
