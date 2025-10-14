// Minimal tests for lib/auggie_exec.js without external deps
import assert from 'node:assert';
import { buildAuggieCommand, getExecutionMode, executeAuggie } from '../../lib/auggie_exec.js';

// Test buildAuggieCommand
{
  const cmd = buildAuggieCommand('/work', 'do "X" now', {
    model: 'gpt5',
    print: true,
    quiet: true,
    outputFormat: 'json',
    compact: true,
    maxTurns: 3,
    auggiePath: 'auggie'
  });
  assert(cmd.includes('cd /work && auggie'));
  assert(cmd.includes('--model gpt5'));
  assert(cmd.includes('--output-format json'));
  assert(cmd.includes('--max-turns 3'));
  // Ensure quotes in instruction are escaped
  assert(cmd.includes('do \\"X\\" now'));
}

// Test getExecutionMode
{
  assert.equal(getExecutionMode(''), 'local');
  assert.equal(getExecutionMode('local'), 'local');
  assert.equal(getExecutionMode('this'), 'local');
  assert.equal(getExecutionMode('localhost'), 'local');
  assert.equal(getExecutionMode('root@1.2.3.4'), 'remote');
}

// Test executeAuggie with injected exec
{
  const fakeExec = async (cmd) => ({ stdout: `OK:${cmd}`, stderr: '' });
  const resLocal = await executeAuggie('/here', 'run it', { quiet: true }, { auggiePath: 'auggie', remoteHost: 'local', runLocalFn: fakeExec });
  assert(resLocal.success);
  assert(resLocal.stdout.startsWith('OK:cd /here && auggie'));

  const fakeSSH = async (host, cmd) => ({ stdout: `SSH:${host}:${cmd}`, stderr: '' });
  const resRemote = await executeAuggie('/there', 'run it', { quiet: true }, { auggiePath: 'auggie', remoteHost: 'root@1.2.3.4', runSSHFn: fakeSSH });
  assert(resRemote.success);
  assert(resRemote.stdout.startsWith('SSH:root@1.2.3.4:cd /there && auggie'));
}

// Test executeAuggie with jump host (ProxyJump via syd2)
{
  const fakeJump = async (jump, host, cmd) => ({ stdout: `JUMP:${jump}->${host}:${cmd}`, stderr: '' });
  const resJump = await executeAuggie('/jump', 'run it', { quiet: true }, { auggiePath: 'auggie', remoteHost: 'root@2.2.2.2', jumpHost: 'syd2', runSSHWithJumpFn: fakeJump });
  assert(resJump.success);
  assert(resJump.stdout.startsWith('JUMP:syd2->root@2.2.2.2:cd /jump && auggie'));
}


console.log('All tests passed for auggie_exec.js');

