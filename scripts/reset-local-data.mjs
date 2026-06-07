import fs from 'fs/promises';
import path from 'path';

const root = path.resolve(new URL('..', import.meta.url).pathname);
const backend = path.join(root, 'backend');

await fs.rm(path.join(backend, 'data'), { recursive: true, force: true });
await fs.rm(path.join(backend, 'uploads'), { recursive: true, force: true });
console.log('Lokale Entwicklungsdaten wurden entfernt. Fuehre danach npm run setup oder npm run dev aus.');
