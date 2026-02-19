#!/usr/bin/env node
/**
 * token-burn.ts - Calculate token usage from session JSONL files
 * 
 * TypeScript/Node.js version with feature parity to Python implementation.
 * Streams through JSONL files to handle large files efficiently.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as readline from 'readline';

interface TokenCounts {
  input: number;
  output: number;
  cache_read: number;
  cache_write: number;
  total: number;
}

interface ProcessResult {
  file: string;
  lines_processed: number;
  messages_processed: number;
  tokens_by_model: Record<string, TokenCounts>;
  errors: number;
  total_input: number;
  total_output: number;
  total_cache_read: number;
  total_cache_write: number;
  total_tokens: number;
}

interface ModelInfo {
  provider: string | null;
  model: string | null;
}

/**
 * Stream lines from a JSONL file
 */
async function* streamJsonlLines(filepath: string): AsyncGenerator<string> {
  const fileStream = fs.createReadStream(filepath, { encoding: 'utf8' });
  const rl = readline.createInterface({
    input: fileStream,
    crlfDelay: Infinity
  });
  
  for await (const line of rl) {
    if (line.trim()) {
      yield line.trim();
    }
  }
}

/**
 * Extract model provider and ID from message data
 */
function extractModelInfo(data: any): ModelInfo {
  const msg = data.message || {};
  
  if (msg.model) {
    return { provider: msg.provider || null, model: msg.model };
  }
  
  // Check content for model info
  const content = msg.content || [];
  if (Array.isArray(content)) {
    for (const item of content) {
      if (item && typeof item === 'object' && 'text' in item) {
        const text = item.text;
        if (typeof text === 'string' && text.includes('model:')) {
          const parts = text.split('model:');
          if (parts.length > 1) {
            const modelStr = parts[1].trim().split(/\s/)[0];
            if (modelStr.includes('/')) {
              const [p, m] = modelStr.split('/', 2);
              return { provider: p, model: modelStr };
            }
          }
        }
      }
    }
  }
  
  // Check custom model-snapshot events
  if (data.type === 'custom' && data.customType === 'model-snapshot') {
    const snap = data.data || {};
    const provider = snap.provider;
    const model = snap.modelId;
    if (provider && model) {
      return { provider, model: `${provider}/${model}` };
    }
  }
  
  return { provider: null, model: null };
}

/**
 * Extract token usage from message data including cached tokens
 * Returns: [input, output, cacheRead, cacheWrite, total]
 */
function extractTokenUsage(data: any): [number, number, number, number, number] {
  const msg = data.message || {};
  const usage = msg.usage || {};
  
  if (usage) {
    const inp = usage.input || usage.inputTokens || 0;
    const out = usage.output || usage.outputTokens || 0;
    const cacheRead = usage.cacheRead || 0;
    const cacheWrite = usage.cacheWrite || 0;
    const total = usage.totalTokens || (inp + out + cacheRead + cacheWrite);
    return [inp, out, cacheRead, cacheWrite, total];
  }
  
  return [0, 0, 0, 0, 0];
}

/**
 * Generate canonical model name
 */
function getModelName(provider: string | null, modelId: string | null): string {
  if (provider && modelId) {
    if (modelId.includes('/')) return modelId;
    return `${provider}/${modelId}`;
  }
  if (modelId) return modelId;
  if (provider) return provider;
  return 'unknown';
}

/**
 * Process a single JSONL file
 */
async function processJsonlFile(filepath: string): Promise<ProcessResult> {
  const result: ProcessResult = {
    file: filepath,
    lines_processed: 0,
    messages_processed: 0,
    tokens_by_model: {},
    errors: 0,
    total_input: 0,
    total_output: 0,
    total_cache_read: 0,
    total_cache_write: 0,
    total_tokens: 0
  };
  
  let currentModel: string | null = null;
  
  for await (const line of streamJsonlLines(filepath)) {
    result.lines_processed++;
    
    try {
      const data = JSON.parse(line);
      const msgType = data.type;
      
      // Track model changes
      if (msgType === 'custom' && data.customType === 'model-snapshot') {
        const { provider, model } = extractModelInfo(data);
        if (model) currentModel = getModelName(provider, model);
      }
      
      // Process messages with token usage
      if (msgType === 'message') {
        const { provider, model } = extractModelInfo(data);
        if (model) currentModel = getModelName(provider, model);
        
        const [inp, out, cacheRead, cacheWrite, total] = extractTokenUsage(data);
        
        if (total > 0) {
          result.messages_processed++;
          const model = currentModel || 'unknown';
          
          if (!result.tokens_by_model[model]) {
            result.tokens_by_model[model] = {
              input: 0, output: 0, cache_read: 0, cache_write: 0, total: 0
            };
          }
          
          result.tokens_by_model[model].input += inp;
          result.tokens_by_model[model].output += out;
          result.tokens_by_model[model].cache_read += cacheRead;
          result.tokens_by_model[model].cache_write += cacheWrite;
          result.tokens_by_model[model].total += total;
          
          result.total_input += inp;
          result.total_output += out;
          result.total_cache_read += cacheRead;
          result.total_cache_write += cacheWrite;
          result.total_tokens += total;
        }
      }
    } catch (e) {
      result.errors++;
      if (result.errors <= 3) {
        console.error(`Warning: Error processing line in ${filepath}: ${e}`);
      }
    }
  }
  
  return result;
}

/**
 * Recursively find all JSONL files in a directory
 */
function findSessionFiles(basePath: string): string[] {
  const files: string[] = [];
  
  function recurse(currentPath: string) {
    const entries = fs.readdirSync(currentPath, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(currentPath, entry.name);
      
      if (entry.isDirectory()) {
        recurse(fullPath);
      } else if (entry.isFile() && entry.name.endsWith('.jsonl')) {
        files.push(fullPath);
      }
    }
  }
  
  recurse(basePath);
  return files.sort();
}

/**
 * Format number with commas
 */
function formatNumber(n: number): string {
  return n.toLocaleString();
}

/**
 * Main entry point
 */
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    console.log(`
token-burn.ts - Calculate token usage from session JSONL files

Usage:
  npx ts-node token-burn.ts <path> [options]

Options:
  --json          Output as JSON
  --recursive     Process directories recursively

Examples:
  npx ts-node token-burn.ts ~/.openclaw/agents/main/sessions/session.jsonl
  npx ts-node token-burn.ts ~/.openclaw/agents/main/sessions/ --recursive
  npx ts-node token-burn.ts session.jsonl --json
`);
    process.exit(0);
  }
  
  const targetPath = args[0];
  const outputJson = args.includes('--json');
  const recursive = args.includes('--recursive');
  
  // Collect files
  let files: string[] = [];
  const stat = fs.statSync(targetPath);
  
  if (stat.isFile()) {
    files = [targetPath];
  } else if (stat.isDirectory()) {
    if (recursive) {
      files = findSessionFiles(targetPath);
    } else {
      files = fs.readdirSync(targetPath)
        .filter(f => f.endsWith('.jsonl'))
        .map(f => path.join(targetPath, f));
    }
  }
  
  if (files.length === 0) {
    console.error('No JSONL files found');
    process.exit(1);
  }
  
  // Process files
  const allResults: ProcessResult[] = [];
  const grandTotal: Record<string, TokenCounts> = {};
  let totalLines = 0;
  let totalMessages = 0;
  
  for (const filepath of files) {
    try {
      const result = await processJsonlFile(filepath);
      allResults.push(result);
      
      // Accumulate totals
      for (const [model, counts] of Object.entries(result.tokens_by_model)) {
        if (!grandTotal[model]) {
          grandTotal[model] = { input: 0, output: 0, cache_read: 0, cache_write: 0, total: 0 };
        }
        grandTotal[model].input += counts.input;
        grandTotal[model].output += counts.output;
        grandTotal[model].cache_read += counts.cache_read;
        grandTotal[model].cache_write += counts.cache_write;
        grandTotal[model].total += counts.total;
      }
      
      totalLines += result.lines_processed;
      totalMessages += result.messages_processed;
    } catch (e) {
      console.error(`Error processing ${filepath}: ${e}`);
    }
  }
  
  // Output results
  if (outputJson) {
    const output = {
      files_processed: files.length,
      total_lines: totalLines,
      total_messages: totalMessages,
      tokens_by_model: grandTotal,
      total_input: Object.values(grandTotal).reduce((a, b) => a + b.input, 0),
      total_output: Object.values(grandTotal).reduce((a, b) => a + b.output, 0),
      total_cache_read: Object.values(grandTotal).reduce((a, b) => a + b.cache_read, 0),
      total_cache_write: Object.values(grandTotal).reduce((a, b) => a + b.cache_write, 0),
      total_tokens: Object.values(grandTotal).reduce((a, b) => a + b.total, 0),
    };
    console.log(JSON.stringify(output, null, 2));
  } else {
    console.log('\n' + '='.repeat(70));
    console.log(' '.repeat(20) + 'TOKEN BURN REPORT');
    console.log('='.repeat(70));
    console.log(`\nFiles processed: ${files.length}`);
    console.log(`Total lines: ${formatNumber(totalLines)}`);
    console.log(`Messages with usage: ${formatNumber(totalMessages)}`);
    
    console.log(`\nToken usage by model:`);
    console.log('-'.repeat(70));
    
    const sortedModels = Object.entries(grandTotal)
      .sort((a, b) => b[1].total - a[1].total);
    
    for (const [model, counts] of sortedModels) {
      console.log(`  ${model}`);
      console.log(`    Input:       ${formatNumber(counts.input).padStart(15)} tokens`);
      console.log(`    Output:      ${formatNumber(counts.output).padStart(15)} tokens`);
      console.log(`    Cache Read:  ${formatNumber(counts.cache_read).padStart(15)} tokens`);
      console.log(`    Cache Write: ${formatNumber(counts.cache_write).padStart(15)} tokens`);
      console.log(`    Total:       ${formatNumber(counts.total).padStart(15)} tokens`);
      console.log();
    }
    
    console.log('-'.repeat(70));
    const totalIn = Object.values(grandTotal).reduce((a, b) => a + b.input, 0);
    const totalOut = Object.values(grandTotal).reduce((a, b) => a + b.output, 0);
    const totalCacheR = Object.values(grandTotal).reduce((a, b) => a + b.cache_read, 0);
    const totalCacheW = Object.values(grandTotal).reduce((a, b) => a + b.cache_write, 0);
    const totalAll = Object.values(grandTotal).reduce((a, b) => a + b.total, 0);
    
    console.log(`  TOTAL INPUT        ${formatNumber(totalIn).padStart(15)}`);
    console.log(`  TOTAL OUTPUT       ${formatNumber(totalOut).padStart(15)}`);
    console.log(`  TOTAL CACHE READ   ${formatNumber(totalCacheR).padStart(15)}`);
    console.log(`  TOTAL CACHE WRITE  ${formatNumber(totalCacheW).padStart(15)}`);
    console.log(`  GRAND TOTAL        ${formatNumber(totalAll).padStart(15)}`);
    console.log('\n' + '='.repeat(70));
  }
}

main().catch(console.error);
