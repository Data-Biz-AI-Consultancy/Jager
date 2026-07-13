#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Table configurations to sync
const TABLES = [
    { schema: "s_buffer", table: "channels", pk: "id", incremental_col: "updated_at" },
    { schema: "s_buffer", table: "posts",    pk: "id", incremental_col: "updated_at" }
];

function loadEnvFile() {
    if (fs.existsSync(".env")) {
        const envContent = fs.readFileSync(".env", "utf8");
        envContent.split("\n").forEach(line => {
            line = line.trim();
            if (!line || line.startsWith("#")) return;
            if (line.includes("=")) {
                const parts = line.split("=");
                const key = parts[0].trim();
                let val = parts.slice(1).join("=").trim();
                // strip quotes
                if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
                    val = val.slice(1, -1);
                }
                process.env[key] = val;
            }
        });
    }
}

function runDuckQuery(dbName, token, query) {
    // Escape double quotes for shell execution
    const escapedQuery = query.replace(/"/g, '\\"').replace(/\n/g, ' ');
    const cmd = `duckdb -c "ATTACH 'md:${dbName}?motherduck_token=${token}' AS md; ${escapedQuery}"`;
    try {
        const output = execSync(cmd, { stdio: ['pipe', 'pipe', 'pipe'] }).toString().trim();
        return output;
    } catch (err) {
        console.error(`DuckDB execution error: ${err.message}`);
        if (err.stderr) {
            console.error(`Details: ${err.stderr.toString()}`);
        }
        throw err;
    }
}

function main() {
    const args = process.argv.slice(2);
    const isDryRun = args.includes("--dry-run");

    loadEnvFile();

    let motherduck_token = process.env.MOTHERDUCK_TOKEN;
    if (!motherduck_token || motherduck_token === "<MOTHERDUCK_TOKEN>") {
        motherduck_token = process.env.MOTHERDUCK_TOKEN_PROD;
    }
    const motherduck_db = process.env.MOTHERDUCK_DATABASE || "staging";
    
    let pg_olap_url = process.env.POSTGRES_OLAP_URL || process.env.OLAP_DATABASE_URL || "postgresql://jager:jager@db:5432/jager_olap";

    if (!motherduck_token || motherduck_token === "<MOTHERDUCK_TOKEN>") {
        console.error("Error: MOTHERDUCK_TOKEN is not set or is invalid.");
        process.exit(1);
    }

    console.log(`Connecting to MotherDuck database: ${motherduck_db}...`);

    let hasErrors = false;
    for (const t of TABLES) {
        const { schema, table, pk, incremental_col } = t;
        const fqn = `${schema}.${table}`;

        console.log(`\n--- Syncing ${fqn} ---`);

        if (isDryRun) {
            console.log(`[DRY-RUN] Would sync ${fqn} (pk: ${pk}, incremental column: ${incremental_col})`);
            continue;
        }

        try {
            // Setup steps query: install/load postgres, attach postgres database
            const setupSql = `
                INSTALL postgres; 
                LOAD postgres; 
                ATTACH '${pg_olap_url}' AS pg (TYPE POSTGRES, READ_ONLY);
                CREATE SCHEMA IF NOT EXISTS md.${schema};
            `;

            // Check if table exists in MotherDuck, otherwise create it empty
            const checkTableSql = `${setupSql} SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '${schema}' AND table_name = '${table}';`;
            const tableExistsCount = parseInt(runDuckQuery(motherduck_db, motherduck_token, checkTableSql).split('\n').pop().trim()) || 0;

            if (tableExistsCount === 0) {
                console.log(`Table md.${fqn} does not exist in MotherDuck. Creating empty table from Postgres template...`);
                const createTableSql = `${setupSql} CREATE TABLE md.${fqn} AS SELECT * FROM pg.${fqn} LIMIT 0;`;
                runDuckQuery(motherduck_db, motherduck_token, createTableSql);
            }

            // Get high water mark
            const getHwmSql = `${setupSql} SELECT MAX(${incremental_col}) FROM md.${fqn};`;
            const hwmOut = runDuckQuery(motherduck_db, motherduck_token, getHwmSql).split('\n').pop().trim();
            const hwm = (hwmOut && hwmOut !== "NULL") ? hwmOut : null;

            let selectQuery = "";
            if (hwm) {
                console.log(`Incremental sync: High-water mark is ${hwm}`);
                selectQuery = `SELECT * FROM pg.${fqn} WHERE ${incremental_col} > '${hwm}'`;
            } else {
                console.log("Full sync: No high-water mark found.");
                selectQuery = `SELECT * FROM pg.${fqn}`;
            }

            // Sync query doing delete-then-insert via a temporary view
            const syncSql = `
                ${setupSql}
                CREATE OR REPLACE TEMPORARY VIEW updates_temp AS ${selectQuery};
                
                -- Check update count
                SELECT COUNT(*) FROM updates_temp;
            `;

            const rowsOut = runDuckQuery(motherduck_db, motherduck_token, syncSql).split('\n').pop().trim();
            const updateCount = parseInt(rowsOut) || 0;
            console.log(`Found ${updateCount} new/updated records to sync.`);

            if (updateCount > 0) {
                const mergeSql = `
                    ${setupSql}
                    CREATE OR REPLACE TEMPORARY VIEW updates_temp AS ${selectQuery};
                    DELETE FROM md.${fqn} WHERE ${pk} IN (SELECT ${pk} FROM updates_temp);
                    INSERT INTO md.${fqn} SELECT * FROM updates_temp;
                `;
                runDuckQuery(motherduck_db, motherduck_token, mergeSql);
                console.log(`Sync complete for ${fqn}!`);
            } else {
                console.log(`No updates found for ${fqn}.`);
            }

        } catch (e) {
            console.error(`Error syncing ${fqn}: ${e.message}`);
            hasErrors = true;
        }
    }

    if (hasErrors) {
        console.error("\nSync completed with errors!");
        process.exit(1);
    } else {
        console.log("\nSync completed successfully!");
    }
}

main();
