#!/usr/bin/env node

/**
 * SSH MCP Server for Project Builder Remote Codebase Access
 *
 * Provides secure SSH-based file operations and command execution for Project Builder agents.
 * Follows Clean Architecture principles with proper separation of concerns.
 *
 * Features:
 * - Connection pooling for performance
 * - SSH key-based authentication only
 * - Path restrictions for security
 * - Command whitelisting
 * - Comprehensive error handling
 * - Observability (logging, metrics)
 *
 * Usage:
 * 1. Install dependencies: npm install @modelcontextprotocol/sdk ssh2
 * 2. Configure SSH keys: Ensure ~/.ssh/id_rsa or specified key exists
 * 3. Add to Claude Code config or use with Project Builder MCP client
 *
 * Configuration via environment variables:
 * - SSH_MCP_ALLOWED_HOSTS: Comma-separated list of allowed hosts (default: localhost)
 * - SSH_MCP_ALLOWED_PATHS: Comma-separated list of allowed path prefixes (default: /opt,/home,/tmp)
 * - SSH_MCP_SSH_KEY_PATH: Path to SSH private key (default: ~/.ssh/id_rsa)
 * - SSH_MCP_CONNECTION_TIMEOUT: Connection timeout in ms (default: 30000)
 * - SSH_MCP_MAX_CONNECTIONS: Max pooled connections per host (default: 5)
 * - SSH_MCP_LOG_LEVEL: Logging level (default: info)
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { Client as SSHClient } from 'ssh2';
import { readFileSync } from 'fs';
import { homedir } from 'os';
import { join } from 'path';

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
  allowedHosts: (process.env.SSH_MCP_ALLOWED_HOSTS || 'localhost').split(',').map(h => h.trim()),
  allowedPaths: (process.env.SSH_MCP_ALLOWED_PATHS || '/opt,/home,/tmp').split(',').map(p => p.trim()),
  sshKeyPath: process.env.SSH_MCP_SSH_KEY_PATH || join(homedir(), '.ssh', 'id_rsa'),
  connectionTimeout: parseInt(process.env.SSH_MCP_CONNECTION_TIMEOUT || '30000'),
  maxConnectionsPerHost: parseInt(process.env.SSH_MCP_MAX_CONNECTIONS || '5'),
  logLevel: process.env.SSH_MCP_LOG_LEVEL || 'info',

  // Command whitelist (empty = allow all, populated = only these commands)
  commandWhitelist: (process.env.SSH_MCP_COMMAND_WHITELIST || '').split(',').filter(c => c.trim()),

  // Command blacklist (always checked)
  commandBlacklist: (process.env.SSH_MCP_COMMAND_BLACKLIST || 'rm -rf /,mkfs,dd if=/dev/zero').split(',').map(c => c.trim()),
};

// ============================================================================
// Logging
// ============================================================================

const LOG_LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };
const currentLogLevel = LOG_LEVELS[CONFIG.logLevel] || LOG_LEVELS.info;

function log(level, message, metadata = {}) {
  if (LOG_LEVELS[level] >= currentLogLevel) {
    const timestamp = new Date().toISOString();
    const metaStr = Object.keys(metadata).length > 0 ? ` ${JSON.stringify(metadata)}` : '';
    console.error(`[${timestamp}] [${level.toUpperCase()}] ${message}${metaStr}`);
  }
}

// ============================================================================
// Metrics Collection
// ============================================================================

const metrics = {
  connections: { total: 0, active: 0, failed: 0 },
  operations: { total: 0, successful: 0, failed: 0 },
  latency: { sum: 0, count: 0, min: Infinity, max: 0 },
};

function recordMetric(operation, success, latencyMs) {
  metrics.operations.total++;
  if (success) {
    metrics.operations.successful++;
  } else {
    metrics.operations.failed++;
  }

  if (latencyMs !== undefined) {
    metrics.latency.sum += latencyMs;
    metrics.latency.count++;
    metrics.latency.min = Math.min(metrics.latency.min, latencyMs);
    metrics.latency.max = Math.max(metrics.latency.max, latencyMs);
  }
}

function getMetrics() {
  const avgLatency = metrics.latency.count > 0
    ? (metrics.latency.sum / metrics.latency.count).toFixed(2)
    : 0;

  return {
    ...metrics,
    latency: {
      ...metrics.latency,
      average: parseFloat(avgLatency),
    },
  };
}

// ============================================================================
// Connection Pool
// ============================================================================

class SSHConnectionPool {
  constructor() {
    this.pools = new Map(); // host -> connection[]
    this.activeConnections = new Map(); // connectionId -> { host, conn, inUse }
    this.nextConnectionId = 0;
  }

  async getConnection(host, username = 'root', port = 22) {
    const poolKey = `${username}@${host}:${port}`;

    // Check for available connection in pool
    if (this.pools.has(poolKey)) {
      const pool = this.pools.get(poolKey);
      const available = pool.find(connId => !this.activeConnections.get(connId).inUse);

      if (available) {
        const connInfo = this.activeConnections.get(available);
        connInfo.inUse = true;
        log('debug', 'Reusing pooled connection', { host, connectionId: available });
        return { connectionId: available, connection: connInfo.conn };
      }
    }

    // Create new connection if under limit
    const currentPoolSize = this.pools.get(poolKey)?.length || 0;
    if (currentPoolSize >= CONFIG.maxConnectionsPerHost) {
      throw new Error(`Connection pool exhausted for ${poolKey} (max: ${CONFIG.maxConnectionsPerHost})`);
    }

    log('info', 'Creating new SSH connection', { host, username, port });
    metrics.connections.total++;
    metrics.connections.active++;

    const conn = new SSHClient();
    const connectionId = this.nextConnectionId++;

    try {
      // Load SSH private key
      const privateKey = readFileSync(CONFIG.sshKeyPath);

      // Connect with promise wrapper
      await new Promise((resolve, reject) => {
        conn.on('ready', () => {
          log('info', 'SSH connection established', { host, connectionId });
          resolve();
        });

        conn.on('error', (err) => {
          log('error', 'SSH connection error', { host, error: err.message });
          metrics.connections.failed++;
          metrics.connections.active--;
          reject(err);
        });

        conn.on('close', () => {
          log('debug', 'SSH connection closed', { host, connectionId });
          metrics.connections.active--;
          this._removeConnection(connectionId);
        });

        conn.connect({
          host,
          port,
          username,
          privateKey,
          readyTimeout: CONFIG.connectionTimeout,
        });
      });

      // Store in pool
      if (!this.pools.has(poolKey)) {
        this.pools.set(poolKey, []);
      }
      this.pools.get(poolKey).push(connectionId);
      this.activeConnections.set(connectionId, { host: poolKey, conn, inUse: true });

      return { connectionId, connection: conn };
    } catch (error) {
      conn.end();
      throw error;
    }
  }

  releaseConnection(connectionId) {
    const connInfo = this.activeConnections.get(connectionId);
    if (connInfo) {
      connInfo.inUse = false;
      log('debug', 'Released connection back to pool', { connectionId });
    }
  }

  _removeConnection(connectionId) {
    const connInfo = this.activeConnections.get(connectionId);
    if (connInfo) {
      const pool = this.pools.get(connInfo.host);
      if (pool) {
        const index = pool.indexOf(connectionId);
        if (index > -1) {
          pool.splice(index, 1);
        }
        if (pool.length === 0) {
          this.pools.delete(connInfo.host);
        }
      }
      this.activeConnections.delete(connectionId);
    }
  }

  async closeAll() {
    log('info', 'Closing all SSH connections');
    for (const [connectionId, connInfo] of this.activeConnections.entries()) {
      connInfo.conn.end();
    }
    this.pools.clear();
    this.activeConnections.clear();
  }
}

const connectionPool = new SSHConnectionPool();

// ============================================================================
// Security Validation
// ============================================================================

function validateHost(host) {
  // Extract hostname from user@host format
  const hostname = host.includes('@') ? host.split('@')[1] : host;

  if (!CONFIG.allowedHosts.includes(hostname) && !CONFIG.allowedHosts.includes('*')) {
    throw new Error(`Host not allowed: ${hostname}. Allowed hosts: ${CONFIG.allowedHosts.join(', ')}`);
  }
}

function validatePath(path) {
  // Normalize path
  const normalizedPath = path.replace(/\/+/g, '/').replace(/\/$/, '');

  // Check against allowed paths
  const isAllowed = CONFIG.allowedPaths.some(allowedPath =>
    normalizedPath.startsWith(allowedPath)
  );

  if (!isAllowed) {
    throw new Error(`Path not allowed: ${path}. Allowed prefixes: ${CONFIG.allowedPaths.join(', ')}`);
  }

  // Check for path traversal attempts
  if (normalizedPath.includes('..')) {
    throw new Error(`Path traversal not allowed: ${path}`);
  }
}

function validateCommand(command) {
  // Check blacklist first
  for (const blacklisted of CONFIG.commandBlacklist) {
    if (blacklisted && command.includes(blacklisted)) {
      throw new Error(`Command contains blacklisted pattern: ${blacklisted}`);
    }
  }

  // Check whitelist if configured
  if (CONFIG.commandWhitelist.length > 0) {
    const commandBase = command.trim().split(/\s+/)[0];
    if (!CONFIG.commandWhitelist.includes(commandBase)) {
      throw new Error(`Command not in whitelist: ${commandBase}. Allowed: ${CONFIG.commandWhitelist.join(', ')}`);
    }
  }
}

// ============================================================================
// SSH Operations
// ============================================================================

async function executeSSHCommand(conn, command) {
  return new Promise((resolve, reject) => {
    let stdout = '';
    let stderr = '';

    conn.exec(command, (err, stream) => {
      if (err) {
        reject(err);
        return;
      }

      stream.on('close', (code, signal) => {
        resolve({ stdout, stderr, exitCode: code });
      });

      stream.on('data', (data) => {
        stdout += data.toString();
      });

      stream.stderr.on('data', (data) => {
        stderr += data.toString();
      });
    });
  });
}

async function readRemoteFile(host, path) {
  const startTime = Date.now();
  let connectionId = null;

  try {
    validateHost(host);
    validatePath(path);

    const [username, hostname] = host.includes('@') ? host.split('@') : ['root', host];
    const { connectionId: connId, connection } = await connectionPool.getConnection(hostname, username);
    connectionId = connId;

    const result = await executeSSHCommand(connection, `cat "${path}"`);

    if (result.exitCode !== 0) {
      throw new Error(`Failed to read file: ${result.stderr}`);
    }

    recordMetric('read_file', true, Date.now() - startTime);
    return { success: true, content: result.stdout };
  } catch (error) {
    recordMetric('read_file', false, Date.now() - startTime);
    throw error;
  } finally {
    if (connectionId !== null) {
      connectionPool.releaseConnection(connectionId);
    }
  }
}

async function writeRemoteFile(host, path, content) {
  const startTime = Date.now();
  let connectionId = null;

  try {
    validateHost(host);
    validatePath(path);

    const [username, hostname] = host.includes('@') ? host.split('@') : ['root', host];
    const { connectionId: connId, connection } = await connectionPool.getConnection(hostname, username);
    connectionId = connId;

    // Escape content for shell
    const escapedContent = content.replace(/'/g, "'\\''");
    const command = `cat > "${path}" << 'EOF_SSH_MCP'\n${escapedContent}\nEOF_SSH_MCP`;

    const result = await executeSSHCommand(connection, command);

    if (result.exitCode !== 0) {
      throw new Error(`Failed to write file: ${result.stderr}`);
    }

    recordMetric('write_file', true, Date.now() - startTime);
    return { success: true, bytesWritten: content.length };
  } catch (error) {
    recordMetric('write_file', false, Date.now() - startTime);
    throw error;
  } finally {
    if (connectionId !== null) {
      connectionPool.releaseConnection(connectionId);
    }
  }
}

async function executeRemoteCommand(host, command, workingDir = null) {
  const startTime = Date.now();
  let connectionId = null;

  try {
    validateHost(host);
    validateCommand(command);

    if (workingDir) {
      validatePath(workingDir);
    }

    const [username, hostname] = host.includes('@') ? host.split('@') : ['root', host];
    const { connectionId: connId, connection } = await connectionPool.getConnection(hostname, username);
    connectionId = connId;

    const fullCommand = workingDir ? `cd "${workingDir}" && ${command}` : command;
    const result = await executeSSHCommand(connection, fullCommand);

    recordMetric('exec_command', true, Date.now() - startTime);
    return {
      success: true,
      stdout: result.stdout,
      stderr: result.stderr,
      exitCode: result.exitCode
    };
  } catch (error) {
    recordMetric('exec_command', false, Date.now() - startTime);
    throw error;
  } finally {
    if (connectionId !== null) {
      connectionPool.releaseConnection(connectionId);
    }
  }
}

async function listRemoteDirectory(host, path) {
  const startTime = Date.now();
  let connectionId = null;

  try {
    validateHost(host);
    validatePath(path);

    const [username, hostname] = host.includes('@') ? host.split('@') : ['root', host];
    const { connectionId: connId, connection } = await connectionPool.getConnection(hostname, username);
    connectionId = connId;

    const result = await executeSSHCommand(connection, `ls -la "${path}"`);

    if (result.exitCode !== 0) {
      throw new Error(`Failed to list directory: ${result.stderr}`);
    }

    recordMetric('list_dir', true, Date.now() - startTime);
    return { success: true, listing: result.stdout };
  } catch (error) {
    recordMetric('list_dir', false, Date.now() - startTime);
    throw error;
  } finally {
    if (connectionId !== null) {
      connectionPool.releaseConnection(connectionId);
    }
  }
}

async function globRemoteFiles(host, pattern, basePath = '/') {
  const startTime = Date.now();
  let connectionId = null;

  try {
    validateHost(host);
    validatePath(basePath);

    const [username, hostname] = host.includes('@') ? host.split('@') : ['root', host];
    const { connectionId: connId, connection } = await connectionPool.getConnection(hostname, username);
    connectionId = connId;

    const command = `find "${basePath}" -name "${pattern}" -type f 2>/dev/null`;
    const result = await executeSSHCommand(connection, command);

    const files = result.stdout.trim().split('\n').filter(f => f.length > 0);

    recordMetric('glob_files', true, Date.now() - startTime);
    return { success: true, files };
  } catch (error) {
    recordMetric('glob_files', false, Date.now() - startTime);
    throw error;
  } finally {
    if (connectionId !== null) {
      connectionPool.releaseConnection(connectionId);
    }
  }
}

async function checkRemoteExists(host, path) {
  const startTime = Date.now();
  let connectionId = null;

  try {
    validateHost(host);
    validatePath(path);

    const [username, hostname] = host.includes('@') ? host.split('@') : ['root', host];
    const { connectionId: connId, connection } = await connectionPool.getConnection(hostname, username);
    connectionId = connId;

    const result = await executeSSHCommand(connection, `test -e "${path}" && echo "exists" || echo "not_found"`);

    const exists = result.stdout.trim() === 'exists';

    // Get type if exists
    let fileType = null;
    if (exists) {
      const typeResult = await executeSSHCommand(connection, `test -f "${path}" && echo "file" || (test -d "${path}" && echo "directory" || echo "other")`);
      fileType = typeResult.stdout.trim();
    }

    recordMetric('check_exists', true, Date.now() - startTime);
    return { success: true, exists, type: fileType };
  } catch (error) {
    recordMetric('check_exists', false, Date.now() - startTime);
    throw error;
  } finally {
    if (connectionId !== null) {
      connectionPool.releaseConnection(connectionId);
    }
  }
}


// ============================================================================
// MCP Server Setup
// ============================================================================

const server = new Server(
  {
    name: 'ssh-remote',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * List available tools
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'ssh_read_file',
        description: 'Read a file from a remote server via SSH. Requires SSH key authentication.',
        inputSchema: {
          type: 'object',
          properties: {
            host: {
              type: 'string',
              description: 'Remote host in format "user@hostname" or "hostname" (defaults to root)',
            },
            path: {
              type: 'string',
              description: 'Absolute path to the file on the remote server',
            },
          },
          required: ['host', 'path'],
        },
      },
      {
        name: 'ssh_write_file',
        description: 'Write content to a file on a remote server via SSH. Creates or overwrites the file.',
        inputSchema: {
          type: 'object',
          properties: {
            host: {
              type: 'string',
              description: 'Remote host in format "user@hostname" or "hostname"',
            },
            path: {
              type: 'string',
              description: 'Absolute path to the file on the remote server',
            },
            content: {
              type: 'string',
              description: 'Content to write to the file',
            },
          },
          required: ['host', 'path', 'content'],
        },
      },
      {
        name: 'ssh_exec',
        description: 'Execute a command on a remote server via SSH. Subject to command whitelist/blacklist.',
        inputSchema: {
          type: 'object',
          properties: {
            host: {
              type: 'string',
              description: 'Remote host in format "user@hostname" or "hostname"',
            },
            command: {
              type: 'string',
              description: 'Command to execute on the remote server',
            },
            workingDir: {
              type: 'string',
              description: 'Optional working directory for command execution',
            },
          },
          required: ['host', 'command'],
        },
      },
      {
        name: 'ssh_list_dir',
        description: 'List contents of a directory on a remote server via SSH.',
        inputSchema: {
          type: 'object',
          properties: {
            host: {
              type: 'string',
              description: 'Remote host in format "user@hostname" or "hostname"',
            },
            path: {
              type: 'string',
              description: 'Absolute path to the directory on the remote server',
            },
          },
          required: ['host', 'path'],
        },
      },
      {
        name: 'ssh_glob',
        description: 'Find files matching a glob pattern on a remote server via SSH.',
        inputSchema: {
          type: 'object',
          properties: {
            host: {
              type: 'string',
              description: 'Remote host in format "user@hostname" or "hostname"',
            },
            pattern: {
              type: 'string',
              description: 'Glob pattern to match (e.g., "*.py", "test_*.js")',
            },
            basePath: {
              type: 'string',
              description: 'Base path to search from (default: /)',
              default: '/',
            },
          },
          required: ['host', 'pattern'],
        },
      },
      {
        name: 'ssh_exists',
        description: 'Check if a file or directory exists on a remote server via SSH.',
        inputSchema: {
          type: 'object',
          properties: {
            host: {
              type: 'string',
              description: 'Remote host in format "user@hostname" or "hostname"',
            },
            path: {
              type: 'string',
              description: 'Absolute path to check on the remote server',
            },
          },
          required: ['host', 'path'],
        },
      },
      {
        name: 'ssh_get_metrics',
        description: 'Get SSH MCP server metrics (connections, operations, latency)',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
    ],
  };
});

/**
 * Handle tool calls
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    log('info', `Tool called: ${name}`, { args });

    switch (name) {
      case 'ssh_read_file': {
        const result = await readRemoteFile(args.host, args.path);
        return {
          content: [
            {
              type: 'text',
              text: result.content,
            },
          ],
        };
      }

      case 'ssh_write_file': {
        const result = await writeRemoteFile(args.host, args.path, args.content);
        return {
          content: [
            {
              type: 'text',
              text: `Successfully wrote ${result.bytesWritten} bytes to ${args.path}`,
            },
          ],
        };
      }

      case 'ssh_exec': {
        const result = await executeRemoteCommand(args.host, args.command, args.workingDir);
        return {
          content: [
            {
              type: 'text',
              text: `Exit Code: ${result.exitCode}\n\nStdout:\n${result.stdout}\n\nStderr:\n${result.stderr}`,
            },
          ],
        };
      }

      case 'ssh_list_dir': {
        const result = await listRemoteDirectory(args.host, args.path);
        return {
          content: [
            {
              type: 'text',
              text: result.listing,
            },
          ],
        };
      }

      case 'ssh_glob': {
        const result = await globRemoteFiles(args.host, args.pattern, args.basePath || '/');
        return {
          content: [
            {
              type: 'text',
              text: `Found ${result.files.length} files:\n${result.files.join('\n')}`,
            },
          ],
        };
      }

      case 'ssh_exists': {
        const result = await checkRemoteExists(args.host, args.path);
        return {
          content: [
            {
              type: 'text',
              text: result.exists
                ? `Path exists (type: ${result.type})`
                : 'Path does not exist',
            },
          ],
        };
      }

      case 'ssh_get_metrics': {
        const currentMetrics = getMetrics();
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(currentMetrics, null, 2),
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: 'text',
              text: `Unknown tool: ${name}`,
            },
          ],
          isError: true,
        };
    }
  } catch (error) {
    log('error', `Tool execution failed: ${name}`, { error: error.message, stack: error.stack });
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Start the server
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  log('info', 'SSH MCP Server running on stdio');
  log('info', 'Configuration', {
    allowedHosts: CONFIG.allowedHosts,
    allowedPaths: CONFIG.allowedPaths,
    maxConnectionsPerHost: CONFIG.maxConnectionsPerHost,
    sshKeyPath: CONFIG.sshKeyPath,
  });

  // Graceful shutdown
  process.on('SIGINT', async () => {
    log('info', 'Shutting down SSH MCP Server');
    await connectionPool.closeAll();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    log('info', 'Shutting down SSH MCP Server');
    await connectionPool.closeAll();
    process.exit(0);
  });
}

main().catch((error) => {
  log('error', 'Fatal error', { error: error.message, stack: error.stack });
  process.exit(1);
});


