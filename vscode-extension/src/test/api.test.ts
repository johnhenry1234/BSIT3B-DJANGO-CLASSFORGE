import assert from 'node:assert/strict';
import { test } from 'node:test';

import { ClassForgeApiError, ClassForgeClient } from '../api';

interface Call {
  url: string;
  init: RequestInit;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function capture(handler: (call: Call) => Response | Promise<Response>): {
  fetchImpl: typeof fetch;
  calls: Call[];
} {
  const calls: Call[] = [];
  const fetchImpl = (async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const call = { url: String(input), init };
    calls.push(call);
    return handler(call);
  }) as typeof fetch;
  return { fetchImpl, calls };
}

test('createToken POSTs credentials to the token endpoint', async () => {
  const { fetchImpl, calls } = capture(() =>
    jsonResponse({ ok: true, token: 'cf_abc' }, 201),
  );
  const client = new ClassForgeClient({ baseUrl: 'https://classforge.test/', fetchImpl });

  const token = await client.createToken('student', 'secret', 'Laptop');

  assert.equal(token, 'cf_abc');
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://classforge.test/api/v1/auth/token/');
  assert.equal(calls[0].init.method, 'POST');
  const headers = calls[0].init.headers as Record<string, string>;
  assert.equal(headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(String(calls[0].init.body)), {
    username: 'student',
    password: 'secret',
    name: 'Laptop',
  });
});

test('authenticated requests send a bearer token', async () => {
  const { fetchImpl, calls } = capture(() =>
    jsonResponse({ user: { username: 'student' }, scopes: ['read'] }),
  );
  const client = new ClassForgeClient({ baseUrl: 'https://classforge.test', fetchImpl });
  client.setToken('cf_token');

  const me = await client.me();

  assert.equal(me.user.username, 'student');
  const headers = calls[0].init.headers as Record<string, string>;
  assert.equal(headers.Authorization, 'Bearer cf_token');
});

test('missing token fails before making a request', async () => {
  const { fetchImpl, calls } = capture(() => jsonResponse({}));
  const client = new ClassForgeClient({ baseUrl: 'https://classforge.test', fetchImpl });

  await assert.rejects(() => client.me(), (error: unknown) => {
    assert.ok(error instanceof ClassForgeApiError);
    assert.equal(error.status, 401);
    return true;
  });
  assert.equal(calls.length, 0);
});

test('API error payloads become ClassForgeApiError', async () => {
  const { fetchImpl } = capture(() =>
    jsonResponse({ ok: false, error: 'You are not enrolled in this course.' }, 403),
  );
  const client = new ClassForgeClient({ baseUrl: 'https://classforge.test', fetchImpl });
  client.setToken('cf_token');

  await assert.rejects(() => client.listCourses(), (error: unknown) => {
    assert.ok(error instanceof ClassForgeApiError);
    assert.equal(error.status, 403);
    assert.match(error.message, /not enrolled/);
    return true;
  });
});

test('network failures are reported clearly', async () => {
  const fetchImpl = (async () => {
    throw new Error('ECONNREFUSED');
  }) as unknown as typeof fetch;
  const client = new ClassForgeClient({ baseUrl: 'https://classforge.test', fetchImpl });
  client.setToken('cf_token');

  await assert.rejects(() => client.health(), /Could not reach the ClassForge server/);
});

test('uploadFiles sends multipart files, paths and metadata', async () => {
  const { fetchImpl, calls } = capture(() =>
    jsonResponse(
      {
        project: { id: 1 },
        snapshot: { id: 2, version: 1, manifest: [] },
        submission: null,
        assessment: null,
      },
      201,
    ),
  );
  const client = new ClassForgeClient({ baseUrl: 'https://classforge.test', fetchImpl });
  client.setToken('cf_token');

  await client.submitFiles(
    7,
    [
      { path: 'README.md', content: new Uint8Array(Buffer.from('# hi')) },
      { path: 'src/app.py', content: new Uint8Array(Buffer.from('print(1)')) },
    ],
    {
      note: 'first pass',
      branch: 'main',
      ignoreFile: {
        name: '.classforgeignore',
        content: new Uint8Array(Buffer.from('docs/**')),
      },
    },
  );

  assert.equal(calls[0].url, 'https://classforge.test/api/v1/assignments/7/submit/');
  const form = calls[0].init.body;
  assert.ok(form instanceof FormData);
  assert.deepEqual(JSON.parse(String(form.get('paths'))), ['README.md', 'src/app.py']);
  assert.equal(form.get('source'), 'vscode');
  assert.equal(form.get('create_submission'), '1');
  assert.equal(form.get('note'), 'first pass');
  assert.equal(form.get('branch'), 'main');
  assert.equal(form.getAll('files[]').length, 2);
  assert.equal(form.get('classforgeignore') instanceof Blob, true);
  const headers = calls[0].init.headers as Record<string, string>;
  assert.equal(headers['Content-Type'], undefined, 'fetch must set the multipart boundary');
});

test('feedback and status endpoints are decoded', async () => {
  const { fetchImpl, calls } = capture((call) => {
    if (call.url.endsWith('/status/')) {
      return jsonResponse({ snapshot: { id: 2 }, assessment: { id: 3 } });
    }
    return jsonResponse({ assessment: { id: 3 }, grade: null });
  });
  const client = new ClassForgeClient({ baseUrl: 'https://classforge.test', fetchImpl });
  client.setToken('cf_token');

  const status = await client.snapshotStatus(2);
  const feedback = await client.snapshotFeedback(2);

  assert.equal(status.snapshot.id, 2);
  assert.equal(feedback.assessment?.id, 3);
  assert.match(calls[0].url, /snapshots\/2\/status\/$/);
  assert.match(calls[1].url, /snapshots\/2\/feedback\/$/);
});
