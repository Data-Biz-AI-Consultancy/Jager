const fs = require('fs');
const path = require('path');

const dockerfilePath = path.join(__dirname, '../src/n8n/Dockerfile');

function runTest() {
  console.log(`Parsing Dockerfile at: ${dockerfilePath}`);
  if (!fs.existsSync(dockerfilePath)) {
    console.error('Dockerfile not found!');
    process.exit(1);
  }

  const content = fs.readFileSync(dockerfilePath, 'utf8');
  const lines = content.split('\n');
  let errors = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('COPY ')) {
      // COPY source destination
      // Handle potential multiple spaces or tabs
      const parts = line.split(/\s+/).slice(1);
      if (parts.length < 2) {
        console.error(`Line ${i + 1}: Invalid COPY command format: "${line}"`);
        errors++;
        continue;
      }
      
      const source = parts[0];
      // Resolve path relative to project root (one level up from tests/)
      const fullSourcePath = path.resolve(__dirname, '..', source);
      
      if (!fs.existsSync(fullSourcePath)) {
        console.error(`Line ${i + 1}: COPY source path "${source}" does not exist at "${fullSourcePath}"`);
        errors++;
      } else {
        console.log(`Line ${i + 1}: Verified COPY source path "${source}" exists.`);
      }
    }
  }

  if (errors > 0) {
    console.error(`Test failed: Found ${errors} missing files/directories referenced in Dockerfile.`);
    process.exit(1);
  }

  console.log('All Dockerfile COPY source paths verified successfully!');
}

runTest();
