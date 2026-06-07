import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import multer from 'multer';
import bcrypt from 'bcryptjs';
import crypto from 'crypto';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PORT = Number(process.env.PORT || 3100);
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const UPLOAD_DIR = process.env.UPLOAD_DIR || path.join(__dirname, 'uploads');
const FRONTEND_DIST = process.env.FRONTEND_DIST || path.join(__dirname, '..', 'frontend', 'dist');
const DEFAULT_ADMIN_EMAIL = process.env.ADMIN_EMAIL || 'admin@dkh.immo';
const DEFAULT_ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'Admin123!';

const app = express();
const sessions = new Map();

async function ensureFile(filePath, fallback) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  try { await fs.access(filePath); } catch { await fs.writeFile(filePath, JSON.stringify(fallback, null, 2)); }
}

async function readJson(name, fallback) {
  const filePath = path.join(DATA_DIR, name);
  await ensureFile(filePath, fallback);
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

async function writeJson(name, data) {
  const filePath = path.join(DATA_DIR, name);
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const tmp = `${filePath}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(data, null, 2));
  await fs.rename(tmp, filePath);
}

async function bootstrap() {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.mkdir(UPLOAD_DIR, { recursive: true });
  const usersFile = path.join(DATA_DIR, 'users.json');
  let users = [];
  try {
    users = JSON.parse(await fs.readFile(usersFile, 'utf8'));
  } catch {
    users = [];
  }

  const needsAdmin = users.length === 0 || users.some(user => user.passwordHash === '__WIRD_BEIM_BACKEND_START_ERSETZT__');
  if (needsAdmin) {
    const passwordHash = await bcrypt.hash(DEFAULT_ADMIN_PASSWORD, 10);
    const admin = {
      id: users[0]?.id || crypto.randomUUID(),
      name: users[0]?.name || 'Admin',
      email: DEFAULT_ADMIN_EMAIL,
      role: 'admin',
      passwordHash,
      createdAt: users[0]?.createdAt || new Date().toISOString()
    };
    await writeJson('users.json', [admin, ...users.filter(user => user.email !== admin.email && user.passwordHash !== '__WIRD_BEIM_BACKEND_START_ERSETZT__')]);
  }
  await ensureFile(path.join(DATA_DIR, 'cases.json'), []);
}

function publicUser(user) {
  const { passwordHash, ...safe } = user;
  return safe;
}

function auth(req, res, next) {
  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : '';
  const session = token ? sessions.get(token) : null;
  if (!session) return res.status(401).json({ error: 'Nicht angemeldet' });
  req.user = session.user;
  next();
}

const storage = multer.diskStorage({
  destination: async (_req, _file, cb) => { await fs.mkdir(UPLOAD_DIR, { recursive: true }); cb(null, UPLOAD_DIR); },
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase() || '.jpg';
    cb(null, `${Date.now()}-${crypto.randomUUID()}${ext}`);
  }
});
const upload = multer({ storage, limits: { fileSize: 12 * 1024 * 1024 } });

app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({ origin: true, credentials: true }));
app.use(express.json({ limit: '25mb' }));
app.use(morgan('combined'));
app.use('/uploads', express.static(UPLOAD_DIR));

app.get('/api/health', (_req, res) => res.json({ ok: true, app: 'DKH Abnahme Backend', time: new Date().toISOString() }));

app.post('/api/auth/login', async (req, res) => {
  const { email, password } = req.body || {};
  const users = await readJson('users.json', []);
  const user = users.find(u => u.email?.toLowerCase() === String(email || '').toLowerCase());
  if (!user || !(await bcrypt.compare(String(password || ''), user.passwordHash))) {
    return res.status(401).json({ error: 'E-Mail oder Passwort ist falsch.' });
  }
  const token = crypto.randomBytes(32).toString('hex');
  sessions.set(token, { user: publicUser(user), createdAt: Date.now() });
  res.json({ token, user: publicUser(user) });
});

app.post('/api/auth/logout', auth, (req, res) => {
  const token = req.headers.authorization?.slice(7);
  if (token) sessions.delete(token);
  res.json({ ok: true });
});

app.get('/api/me', auth, (req, res) => res.json({ user: req.user }));

app.get('/api/cases', auth, async (_req, res) => {
  const cases = await readJson('cases.json', []);
  res.json({ cases });
});

app.put('/api/cases', auth, async (req, res) => {
  const cases = Array.isArray(req.body?.cases) ? req.body.cases : [];
  const stamped = cases.map(item => ({ ...item, serverUpdatedAt: new Date().toISOString(), serverUpdatedBy: req.user.email }));
  await writeJson('cases.json', stamped);
  res.json({ ok: true, count: stamped.length });
});

app.post('/api/cases', auth, async (req, res) => {
  const cases = await readJson('cases.json', []);
  const item = { ...req.body, id: req.body.id || crypto.randomUUID(), serverUpdatedAt: new Date().toISOString(), serverUpdatedBy: req.user.email };
  await writeJson('cases.json', [item, ...cases.filter(c => c.id !== item.id)]);
  res.status(201).json({ item });
});

app.put('/api/cases/:id', auth, async (req, res) => {
  const cases = await readJson('cases.json', []);
  const index = cases.findIndex(c => c.id === req.params.id);
  const item = { ...req.body, id: req.params.id, serverUpdatedAt: new Date().toISOString(), serverUpdatedBy: req.user.email };
  if (index >= 0) cases[index] = item; else cases.unshift(item);
  await writeJson('cases.json', cases);
  res.json({ item });
});

app.delete('/api/cases/:id', auth, async (req, res) => {
  const cases = await readJson('cases.json', []);
  await writeJson('cases.json', cases.filter(c => c.id !== req.params.id));
  res.json({ ok: true });
});

app.post('/api/uploads', auth, upload.single('file'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'Keine Datei hochgeladen.' });
  res.json({ url: `/uploads/${req.file.filename}`, filename: req.file.filename, size: req.file.size });
});

app.use(express.static(FRONTEND_DIST));
app.get('*', async (_req, res, next) => {
  try { await fs.access(path.join(FRONTEND_DIST, 'index.html')); res.sendFile(path.join(FRONTEND_DIST, 'index.html')); }
  catch { next(); }
});

bootstrap().then(() => app.listen(PORT, () => {
  console.log(`DKH Abnahme Backend laeuft auf Port ${PORT}`);
  console.log(`Standard-Login: ${DEFAULT_ADMIN_EMAIL} / ${DEFAULT_ADMIN_PASSWORD}`);
})).catch(error => {
  console.error(error);
  process.exit(1);
});
