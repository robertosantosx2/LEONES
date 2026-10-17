#!/usr/bin/env node
/**
 * Loopback-only OpenAI-compatible facade for LEONES' pinned Magnitude ICN.
 *
 * The pinned ICN uses /v1/chat/completions but requires model_instance_id,
 * always returns SSE, and exposes a non-OpenAI /v1/models response. This facade
 * translates those differences without modifying OpenDots or the submodule.
 */
import http from 'node:http';

const HOST = '127.0.0.1';
const PORT = Number(process.env.OPENDOTS_MAGNITUDE_PORT ?? 10101);
const ICN_URL = (process.env.MAGNITUDE_ICN_URL ?? 'http://127.0.0.1:8080').replace(/\/$/, '');
const INSTANCE_ID = process.env.MAGNITUDE_MODEL_INSTANCE_ID ?? '';
const MODEL_ALIAS = process.env.OPENAI_MODEL ?? 'local';
const MAX_BODY_BYTES = 1024 * 1024;
const ALLOWED_FIELDS = new Set([
  'model', 'messages', 'max_tokens', 'max_completion_tokens', 'temperature',
  'top_p', 'seed', 'tools', 'tool_choice', 'parallel_tool_calls',
  'reasoning_effort', 'thinking_budget_tokens', 'response_format',
  'chat_template_kwargs', 'stop', 'stream_options', 'cache_prompt',
  'ignore_eos', 'timings_per_token',
]);

function json(res, status, value) {
  const body = JSON.stringify(value);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body),
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
  });
  res.end(body);
}

async function readJson(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) throw Object.assign(new Error('Request body too large.'), { status: 413 });
    chunks.push(chunk);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    throw Object.assign(new Error('Request body must be valid JSON.'), { status: 400 });
  }
}

async function activeInstance() {
  if (!INSTANCE_ID) throw new Error('MAGNITUDE_MODEL_INSTANCE_ID is not configured.');
  const upstream = await fetch(`${ICN_URL}/v1/models/instances`, { signal: AbortSignal.timeout(5000) });
  if (!upstream.ok) throw new Error(`Magnitude ICN instances endpoint returned HTTP ${upstream.status}.`);
  const snapshot = await upstream.json();
  const instance = Array.isArray(snapshot.instances)
    ? snapshot.instances.find((item) => item?.id === INSTANCE_ID)
    : undefined;
  if (!instance || instance.lifecycle?._tag !== 'Ready') {
    throw new Error('Configured Magnitude model instance is not in Ready state. Load the model and set MAGNITUDE_MODEL_INSTANCE_ID to its exact id.');
  }
  return instance;
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url ?? '/', `http://${HOST}:${PORT}`);
    if (req.method === 'GET' && url.pathname === '/health') {
      const upstream = await fetch(`${ICN_URL}/health`, { signal: AbortSignal.timeout(5000) });
      if (!upstream.ok) return json(res, 503, { status: 'unavailable', upstreamStatus: upstream.status });
      await activeInstance();
      return json(res, 200, { status: 'ok', provider: 'magnitude-icn', model: MODEL_ALIAS });
    }

    if (req.method === 'GET' && url.pathname === '/v1/models') {
      await activeInstance();
      return json(res, 200, {
        object: 'list',
        data: [{ id: MODEL_ALIAS, object: 'model', created: 0, owned_by: 'magnitude-icn' }],
      });
    }

    if (req.method === 'POST' && url.pathname === '/v1/chat/completions') {
      const instance = await activeInstance();
      const input = await readJson(req);
      if (!Array.isArray(input.messages) || input.messages.length === 0) {
        return json(res, 400, { error: { message: 'messages must be a non-empty array.', type: 'invalid_request_error' } });
      }
      if (input.model && input.model !== MODEL_ALIAS) {
        return json(res, 400, { error: { message: `Unknown model alias. Configure OPENAI_MODEL=${MODEL_ALIAS}.`, type: 'invalid_request_error' } });
      }
      const body = {};
      for (const [key, value] of Object.entries(input)) {
        if (ALLOWED_FIELDS.has(key)) body[key] = value;
      }
      body.model = instance.configurationId;
      body.model_instance_id = instance.id;
      // The pinned ICN contract exposes SSE only; TanStack AI/OpenDots consumes a stream.
      body.stream = true;

      const controller = new AbortController();
      res.on('close', () => { if (!res.writableEnded) controller.abort(); });
      const upstream = await fetch(`${ICN_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      const contentType = upstream.headers.get('content-type') ?? 'application/json';
      res.writeHead(upstream.status, {
        'content-type': contentType,
        'cache-control': 'no-cache, no-transform',
        'x-content-type-options': 'nosniff',
        'x-accel-buffering': 'no',
      });
      if (!upstream.body) return res.end();
      for await (const chunk of upstream.body) {
        if (res.destroyed) break;
        res.write(Buffer.from(chunk));
      }
      return res.end();
    }

    return json(res, 404, { error: { message: 'Not found.', type: 'invalid_request_error' } });
  } catch (error) {
    if (res.headersSent) {
      res.destroy(error);
      return;
    }
    const status = Number(error?.status) || 503;
    return json(res, status, { error: { message: error instanceof Error ? error.message : 'Proxy request failed.', type: 'magnitude_proxy_error' } });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`OpenDots ↔ Magnitude compatibility facade listening on http://${HOST}:${PORT}/v1`);
  console.log(`Magnitude ICN: ${ICN_URL}; model alias: ${MODEL_ALIAS}`);
});
