import assert from 'node:assert/strict';
import { once } from 'node:events';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { after, before, test } from 'node:test';

let icn;
let proxy;
let icnUrl;
let proxyUrl;
let proxyPort;
let lastCompletion;

async function listen(server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return server.address().port;
}

async function freePort() {
  const server = http.createServer();
  const port = await listen(server);
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  return port;
}

before(async () => {
  icn = http.createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://127.0.0.1');
    if (req.method === 'GET' && url.pathname === '/health') {
      res.writeHead(200, { 'content-type': 'application/json' });
      return res.end(JSON.stringify({ status: 'ok' }));
    }
    if (req.method === 'GET' && url.pathname === '/v1/models/instances') {
      res.writeHead(200, { 'content-type': 'application/json' });
      return res.end(JSON.stringify({
        revision: 1,
        instances: [{ id: 'instance-test-123', configurationId: 'config-test', lifecycle: { _tag: 'Ready' } }],
      }));
    }
    if (req.method === 'POST' && url.pathname === '/v1/chat/completions') {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      lastCompletion = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      res.writeHead(200, { 'content-type': 'text/event-stream' });
      res.end(
        'data: {"id":"chat-test","object":"chat.completion.chunk","created":1,"model":"local","choices":[{"index":0,"delta":{"content":"LOCAL_OK"},"finish_reason":null}]}\n\n' +
        'data: [DONE]\n\n',
      );
      return;
    }
    res.writeHead(404, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: 'not found' }));
  });
  const icnPort = await listen(icn);
  icnUrl = `http://127.0.0.1:${icnPort}`;
  proxyPort = await freePort();
  proxyUrl = `http://127.0.0.1:${proxyPort}`;
  proxy = spawn(process.execPath, ['scripts/integrations/opendots_magnitude_proxy.mjs'], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      MAGNITUDE_ICN_URL: icnUrl,
      MAGNITUDE_MODEL_INSTANCE_ID: 'instance-test-123',
      OPENAI_MODEL: 'local',
      OPENDOTS_MAGNITUDE_PORT: String(proxyPort),
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  proxy.stderr.on('data', () => {});
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${proxyUrl}/health`);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error('Compatibility proxy did not become healthy within 5 seconds.');
});

after(async () => {
  if (proxy && proxy.exitCode === null) {
    proxy.kill('SIGTERM');
    await Promise.race([once(proxy, 'exit'), new Promise((resolve) => setTimeout(resolve, 1000))]);
  }
  if (icn?.listening) {
    await new Promise((resolve, reject) => icn.close((error) => error ? reject(error) : resolve()));
  }
});

test('advertises a standard OpenAI model list for a Ready ICN instance', async () => {
  const response = await fetch(`${proxyUrl}/v1/models`);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.object, 'list');
  assert.deepEqual(body.data.map((model) => model.id), ['local']);
});

test('maps OpenDots chat requests to ICN instance IDs and preserves tools over SSE', async () => {
  const response = await fetch(`${proxyUrl}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      model: 'local',
      messages: [{ role: 'user', content: 'Say LOCAL_OK' }],
      max_completion_tokens: 32,
      tools: [{ type: 'function', function: { name: 'example_tool', description: 'Test', parameters: { type: 'object', properties: {} } } }],
      stream: true,
    }),
  });
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type') ?? '', /text\/event-stream/);
  const body = await response.text();
  assert.match(body, /LOCAL_OK/);
  assert.match(body, /data: \[DONE\]/);
  assert.equal(lastCompletion.model_instance_id, 'instance-test-123');
  assert.equal(lastCompletion.model, 'local');
  assert.equal(lastCompletion.stream, true);
  assert.equal(lastCompletion.tools[0].function.name, 'example_tool');
});
