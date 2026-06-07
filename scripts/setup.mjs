import fs from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const backend = path.join(root, 'backend');
const frontend = path.join(root, 'frontend');

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function copyIfMissing(source, target) {
  try {
    await fs.access(target);
  } catch {
    await fs.copyFile(source, target);
  }
}

await ensureDir(path.join(backend, 'data'));
await ensureDir(path.join(backend, 'uploads'));
await ensureDir(path.join(backend, 'uploads', 'photos'));
await ensureDir(path.join(backend, 'uploads', 'signatures'));
await ensureDir(path.join(backend, 'uploads', 'protocols'));

await copyIfMissing(path.join(backend, '.env.example'), path.join(backend, '.env'));
await copyIfMissing(path.join(frontend, '.env.example'), path.join(frontend, '.env'));

const secretsPath = path.join(backend, 'data', 'local-secret.txt');

try {
  await fs.access(secretsPath);
} catch {
  await fs.writeFile(secretsPath, crypto.randomBytes(32).toString('hex'), 'utf8');
}

console.log('Lokale Umgebung vorbereitet.');
