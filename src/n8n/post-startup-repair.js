/**
 * post-startup-repair.js
 *
 * Runs AFTER n8n has fully started and activated all workflows.
 * Ensures workflow_published_version.publishedVersionId is always in sync
 * with workflow_entity.versionId for every workflow.
 *
 * This catches drift that occurs when:
 * 1. n8n updates versionId during its own startup activation phase
 * 2. Users save workflows via the n8n UI (which updates versionId but not publishedVersionId)
 *
 * Safe to run at any time — all queries use ON CONFLICT DO UPDATE.
 */

const pgPath = require.resolve('pg', { paths: ['/usr/local/lib/node_modules/n8n'] });
const { Client } = require(pgPath);

const client = new Client({
  host: process.env.DB_POSTGRESDB_HOST || 'db',
  port: parseInt(process.env.DB_POSTGRESDB_PORT || '5432', 10),
  database: process.env.DB_POSTGRESDB_DATABASE || 'n8n',
  user: process.env.DB_POSTGRESDB_USER || 'jager',
  password: process.env.DB_POSTGRESDB_PASSWORD || 'jager',
});

async function repairVersions() {
  await client.connect();

  // Guard: only run if the versioning tables exist (n8n 2.x+)
  const tableCheck = await client.query(`
    SELECT EXISTS (
      SELECT FROM information_schema.tables
      WHERE table_schema = 'public'
      AND table_name = 'workflow_published_version'
    )
  `);
  if (!tableCheck.rows[0].exists) {
    console.log('[post-startup-repair] workflow_published_version table not found. Skipping.');
    await client.end();
    return;
  }

  const workflows = await client.query(`
    SELECT id, name, "versionId", active, nodes, connections, settings, description, "nodeGroups"
    FROM workflow_entity
  `);

  if (workflows.rows.length === 0) {
    await client.end();
    return;
  }

  console.log(`[post-startup-repair] Syncing version tables for ${workflows.rows.length} workflow(s)...`);

  const now = new Date().toISOString();
  let repaired = 0;

  for (const r of workflows.rows) {
    const workflowId = r.id;
    const versionId = r.versionId;

    // 1. Ensure workflow_history has an entry for this versionId
    await client.query(
      `INSERT INTO workflow_history (
         "versionId", "workflowId", "authors", "createdAt", "updatedAt",
         "nodes", "connections", "name", "autosaved", "description", "nodeGroups"
       ) VALUES (
         $1, $2, '[]', $3, $3,
         $4, $5, $6, false, $7, $8
       ) ON CONFLICT ("versionId") DO NOTHING`,
      [
        versionId,
        workflowId,
        now,
        JSON.stringify(r.nodes || []),
        JSON.stringify(r.connections || {}),
        r.name,
        r.description || null,
        JSON.stringify(r.nodeGroups || []),
      ]
    );

    // 2. Check current published version
    const existing = await client.query(
      `SELECT "publishedVersionId" FROM workflow_published_version WHERE "workflowId" = $1`,
      [workflowId]
    );

    const publishedVersionId = existing.rows[0]?.publishedVersionId;

    if (publishedVersionId !== versionId) {
      // Upsert workflow_published_version to point to current versionId
      await client.query(
        `INSERT INTO workflow_published_version ("workflowId", "publishedVersionId", "createdAt", "updatedAt")
         VALUES ($1, $2, $3, $3)
         ON CONFLICT ("workflowId")
         DO UPDATE SET "publishedVersionId" = EXCLUDED."publishedVersionId", "updatedAt" = EXCLUDED."updatedAt"`,
        [workflowId, versionId, now]
      );
      console.log(`[post-startup-repair] Fixed: "${r.name}" (${workflowId}) — ${publishedVersionId ?? 'missing'} → ${versionId}`);
      repaired++;
    }

    // 3. Sync activeVersionId for active workflows
    if (r.active) {
      await client.query(
        `UPDATE workflow_entity
         SET "activeVersionId" = $1
         WHERE id = $2 AND active = true AND "activeVersionId" != $1`,
        [versionId, workflowId]
      );
    }
  }

  if (repaired > 0) {
    console.log(`[post-startup-repair] Repaired ${repaired} workflow(s).`);
  } else {
    console.log('[post-startup-repair] All workflows already in sync. No repairs needed.');
  }

  await client.end();
}

repairVersions().catch(err => {
  console.error('[post-startup-repair] Error:', err.message);
  process.exit(1);
});
