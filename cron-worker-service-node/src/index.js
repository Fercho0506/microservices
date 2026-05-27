const express = require('express');
const cron = require('node-cron');
const { Pool } = require('pg');
const axios = require('axios');

const app = express();
app.use(express.json());

// ─── DB (PostgreSQL) ──────────────────────────────────────
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'finops_db',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  ssl: {
    rejectUnauthorized: false
  }
});

const INTEGRATION_URL = process.env.INTEGRATION_SERVICE_URL || 'http://localhost:8081';

// ─── Init DB ──────────────────────────────────────────────
async function initDB() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS sync_jobs (
      id SERIAL PRIMARY KEY,
      provider VARCHAR(50) NOT NULL,
      start_date DATE NOT NULL,
      end_date DATE NOT NULL,
      status VARCHAR(20) DEFAULT 'pending',
      records_synced INT DEFAULT 0,
      error_message TEXT,
      started_at TIMESTAMPTZ DEFAULT NOW(),
      completed_at TIMESTAMPTZ
    )
  `);
  console.log('[DB] sync_jobs table ready');
}

// ─── Sync logic ───────────────────────────────────────────
async function runSync(provider = 'aws', daysBack = 1) {
  const endDate = new Date().toISOString().split('T')[0];
  const startDate = new Date(Date.now() - daysBack * 86400000).toISOString().split('T')[0];

  const { rows } = await pool.query(
    `INSERT INTO sync_jobs (provider, start_date, end_date, status)
     VALUES ($1, $2, $3, 'running') RETURNING id`,
    [provider, startDate, endDate]
  );
  const jobId = rows[0].id;

  try {
    const resp = await axios.post(
      `${INTEGRATION_URL}/integration/sync/?provider=${provider}&start_date=${startDate}&end_date=${endDate}`,
      {},
      { timeout: 60000 }
    );
    const recordsSaved = resp.data.records_saved || 0;

    await pool.query(
      `UPDATE sync_jobs SET status='success', records_synced=$1, completed_at=NOW() WHERE id=$2`,
      [recordsSaved, jobId]
    );
    console.log(`[CRON] Sync OK — provider=${provider} records=${recordsSaved}`);
    return { jobId, status: 'success', recordsSaved };
  } catch (err) {
    await pool.query(
      `UPDATE sync_jobs SET status='failed', error_message=$1, completed_at=NOW() WHERE id=$2`,
      [err.message, jobId]
    );
    console.error(`[CRON] Sync FAILED — ${err.message}`);
    return { jobId, status: 'failed', error: err.message };
  }
}

// ─── Cron schedule: runs every hour ──────────────────────
cron.schedule('0 * * * *', () => {
  console.log('[CRON] Scheduled sync triggered');
  runSync('aws', 1);
});

// ─── REST endpoints ───────────────────────────────────────
app.get('/worker/health', (req, res) => {
  res.json({ status: 'ok', service: 'cron-worker-node' });
});

app.post('/worker/sync/trigger', async (req, res) => {
  const provider = req.query.provider || 'aws';
  const daysBack = parseInt(req.query.days_back || '1', 10);
  const result = await runSync(provider, daysBack);
  res.status(result.status === 'success' ? 200 : 500).json(result);
});

app.get('/worker/sync/history', async (req, res) => {
  const { rows } = await pool.query(
    'SELECT * FROM sync_jobs ORDER BY started_at DESC LIMIT 20'
  );
  res.json({ jobs: rows });
});

// ─── Start ────────────────────────────────────────────────
const PORT = process.env.PORT || 8082;
initDB().then(() => {
  app.listen(PORT, () => console.log(`[CRON Worker] Listening on :${PORT}`));
});
