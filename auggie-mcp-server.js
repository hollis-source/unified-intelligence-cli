#!/usr/bin/env node

/**
 * Auggie MCP Server
 * Exposes auggie CLI capabilities as MCP tools for Claude Code
 *
 * Usage:
 * 1. Install: npm install -g @modelcontextprotocol/sdk
 * 2. Add to Claude Code config (~/.claude/config.json):
 *    {
 *      "mcpServers": {
 *        "auggie": {
 *          "command": "node",
 *          "args": ["/path/to/auggie-mcp-server.js"],
 *          "env": {
 *            "AUGGIE_REMOTE_HOST": "root@157.90.66.183",
 *            "AUGGIE_REMOTE_PATH": "/root/projects"
 *          }
 *        }
 *      }
 *    }
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { exec } from 'child_process';
import { promisify } from 'util';
import { executeAuggie, listSessions } from './lib/auggie_exec.js';

const execAsync = promisify(exec);

// Configuration
const REMOTE_HOST = process.env.AUGGIE_REMOTE_HOST || 'root@157.90.66.183';
const REMOTE_PATH = process.env.AUGGIE_REMOTE_PATH || '/root';
const AUGGIE_PATH = process.env.AUGGIE_PATH || 'auggie'; // assumes in PATH

const JUMP_HOST = process.env.AUGGIE_JUMP_HOST || process.env.SSH_JUMP_HOST || 'syd2';

/**
 * Execute auggie command on local or remote server (auto-detect)
 */
async function executeRemoteAuggie(workingDir, instruction, options = {}) {
  return executeAuggie(workingDir, instruction, options, {
    auggiePath: AUGGIE_PATH,
    remoteHost: REMOTE_HOST,
    jumpHost: JUMP_HOST,
  });
}

/**
 * Create and configure the MCP server
 */
const server = new Server(
  {
    name: 'auggie-remote',
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
        name: 'auggie_execute',
        description: 'Execute an auggie command on the remote server. Auggie is an agentic coding CLI that can analyze, edit, and refactor code using Claude Sonnet 4, 4.5, or GPT-5.',
        inputSchema: {
          type: 'object',
          properties: {
            instruction: {
              type: 'string',
              description: 'The instruction to give to auggie (e.g., "refactor this function to be more efficient")',
            },
            workingDir: {
              type: 'string',
              description: 'Working directory path on remote server',
              default: REMOTE_PATH,
            },
            model: {
              type: 'string',
              enum: ['sonnet4', 'sonnet4.5', 'gpt5'],
              description: 'AI model to use (sonnet4, sonnet4.5, or gpt5)',
            },
            outputFormat: {
              type: 'string',
              enum: ['text', 'json'],
              description: 'Output format (text or json)',
              default: 'text',
            },
            quiet: {
              type: 'boolean',
              description: 'Only show final output (no tool calls)',
              default: false,
            },
            compact: {
              type: 'boolean',
              description: 'Use compact logging',
              default: false,
            },
            maxTurns: {
              type: 'number',
              description: 'Maximum number of agentic turns',
            },
          },
          required: ['instruction'],
        },
      },
      {
        name: 'auggie_with_gpt5',
        description: 'Quick access to GPT-5 via auggie for tasks where OpenAI models might excel. Uses print and quiet modes for clean output.',
        inputSchema: {
          type: 'object',
          properties: {
            instruction: {
              type: 'string',
              description: 'The instruction to give to GPT-5',
            },
            workingDir: {
              type: 'string',
              description: 'Working directory path on remote server',
              default: REMOTE_PATH,
            },
          },
          required: ['instruction'],
        },
      },
      {
        name: 'auggie_sessions_list',
        description: 'List recent auggie sessions on the remote server',
        inputSchema: {
          type: 'object',
          properties: {
            limit: {
              type: 'number',
              description: 'Number of sessions to show',
              default: 5,
            },
          },
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
    switch (name) {
      case 'auggie_execute': {
        const result = await executeRemoteAuggie(
          args.workingDir || REMOTE_PATH,
          args.instruction,
          {
            model: args.model,
            outputFormat: args.outputFormat || 'text',
            quiet: args.quiet || false,
            compact: args.compact || false,
            maxTurns: args.maxTurns,
          }
        );

        if (!result.success) {
          return {
            content: [
              {
                type: 'text',
                text: `Error executing auggie:\n${result.error}\n\nStderr: ${result.stderr}`,
              },
            ],
            isError: true,
          };
        }

        // Parse JSON output if requested
        let output = result.stdout;
        if (args.outputFormat === 'json') {
          try {
            const parsed = JSON.parse(result.stdout);
            output = JSON.stringify(parsed, null, 2);
          } catch (e) {
            // Keep as-is if not valid JSON
          }
        }

        return {
          content: [
            {
              type: 'text',
              text: `Auggie Result:\n\n${output}${result.stderr ? `\n\nStderr: ${result.stderr}` : ''}`,
            },
          ],
        };
      }

      case 'auggie_with_gpt5': {
        const result = await executeRemoteAuggie(
          args.workingDir || REMOTE_PATH,
          args.instruction,
          {
            model: 'gpt5',
            quiet: true,
            print: true,
          }
        );

        if (!result.success) {
          return {
            content: [
              {
                type: 'text',
                text: `Error executing auggie with GPT-5:\n${result.error}`,
              },
            ],
            isError: true,
          };
        }

        return {
          content: [
            {
              type: 'text',
              text: `GPT-5 via Auggie:\n\n${result.stdout}`,
            },
          ],
        };
      }

      case 'auggie_sessions_list': {
        const limit = args.limit || 5;
        const modeSessions = await (async () => {
          // Prefer helper that handles local/remote
          try {
            const out = await listSessions({ remoteHost: REMOTE_HOST }, execAsync);
            return out;
          } catch (_) {
            // Fallback to direct SSH (backward compatible)
            const cmd = `ssh ${REMOTE_HOST} 'auggie session list --limit ${limit}'`;
            const { stdout } = await execAsync(cmd);
            return stdout;
          }
        })();

        return {
          content: [
            {
              type: 'text',
              text: `Auggie Sessions:\n\n${modeSessions}`,
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
  console.error('Auggie MCP Server running on stdio');
  console.error(`Remote host: ${REMOTE_HOST}`);
  console.error(`Jump host: ${JUMP_HOST}`);
  console.error(`Remote path: ${REMOTE_PATH}`);
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
