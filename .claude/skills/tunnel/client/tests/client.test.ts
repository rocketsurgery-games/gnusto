import {describe, it, before, after, afterEach} from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import net from 'node:net';
import {WebSocketServer, WebSocket as WsClient} from 'ws';
import {TunnelClient} from '../src/client.js';
import type {
  HelloMessage,
  ResponseMessage,
  ErrorMessage,
  ConnectedMessage,
  StreamDataMessage,
  StreamEndMessage,
  StreamErrorMessage,
  ClientMessage,
  RequestMessage,
} from '../src/types.js';

/** Wait for a condition to become true within a timeout. */
async function waitFor(
  fn: () => boolean,
  timeoutMs = 2000,
  intervalMs = 20,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (!fn()) {
    if (Date.now() > deadline)
      throw new Error(`waitFor timed out after ${timeoutMs}ms`);
    await new Promise(r => setTimeout(r, intervalMs));
  }
}

/** Collect the next N JSON messages from a WebSocket. */
function collectMessages(
  ws: WsClient,
  count: number,
): Promise<ClientMessage[]> {
  return new Promise(resolve => {
    const msgs: ClientMessage[] = [];
    const handler = (data: Buffer) => {
      msgs.push(JSON.parse(data.toString()));
      if (msgs.length >= count) {
        ws.off('message', handler);
        resolve(msgs);
      }
    };
    ws.on('message', handler);
  });
}

/** Wait for the next single message. */
function nextMessage(ws: WsClient): Promise<ClientMessage> {
  return collectMessages(ws, 1).then(msgs => msgs[0]);
}

describe('TunnelClient', () => {
  let wss: WebSocketServer;
  let httpServer: http.Server;
  let relayUrl: string;
  let logs: string[];

  before(async () => {
    httpServer = http.createServer();
    wss = new WebSocketServer({server: httpServer});
    await new Promise<void>(resolve => {
      httpServer.listen(0, '127.0.0.1', resolve);
    });
    const addr = httpServer.address() as {port: number};
    relayUrl = `ws://127.0.0.1:${addr.port}`;
  });

  after(() => {
    wss.close();
    httpServer.close();
  });

  afterEach(() => {
    // Close all relay-side connections between tests
    for (const ws of wss.clients) {
      ws.close();
    }
  });

  function createClient(target = 'http://localhost:9999'): TunnelClient {
    logs = [];
    return new TunnelClient({
      relayUrl,
      target,
      connectionId: 'test-connection-id',
      token: 'test-token',
      log: msg => logs.push(msg),
    });
  }

  it('starts disconnected', () => {
    const client = createClient();
    assert.equal(client.state, 'disconnected');
    assert.equal(client.tunnelId, undefined);
  });

  it('connects and receives ready', async () => {
    const client = createClient();

    const connectionPromise = new Promise<WsClient>(resolve => {
      wss.once('connection', resolve);
    });

    client.connect();
    assert.equal(client.state, 'connecting');

    const relayWs = await connectionPromise;
    const hello = (await nextMessage(relayWs)) as HelloMessage;

    assert.equal(hello.type, 'hello');
    assert.equal(hello.target, 'http://localhost:9999');
    assert.equal(hello.connectionId, 'test-connection-id');
    assert.equal(client.state, 'connected');

    relayWs.send(JSON.stringify({type: 'ready', tunnelId: 't_test123'}));
    await waitFor(() => client.state === 'ready');

    assert.equal(client.tunnelId, 't_test123');

    client.disconnect();
    assert.equal(client.state, 'disconnected');
  });

  it('responds to ping with pong', async () => {
    const client = createClient();

    const connectionPromise = new Promise<WsClient>(resolve => {
      wss.once('connection', resolve);
    });

    client.connect();
    const relayWs = await connectionPromise;
    await nextMessage(relayWs); // hello

    relayWs.send(JSON.stringify({type: 'ready', tunnelId: 't_ping'}));
    await waitFor(() => client.state === 'ready');

    // Send a ping
    relayWs.send(JSON.stringify({type: 'ping'}));
    const pong = await nextMessage(relayWs);
    assert.equal(pong.type, 'pong');

    client.disconnect();
  });

  it('proxies a request to localhost', async () => {
    // Spin up a tiny target HTTP server
    const targetServer = http.createServer((req, res) => {
      res.writeHead(200, {'Content-Type': 'text/plain', 'X-Custom': 'hello'});
      res.end('ok');
    });
    await new Promise<void>(resolve => {
      targetServer.listen(0, '127.0.0.1', resolve);
    });
    const targetAddr = targetServer.address() as {port: number};
    const targetUrl = `http://127.0.0.1:${targetAddr.port}`;

    const client = createClient(targetUrl);
    const connectionPromise = new Promise<WsClient>(resolve => {
      wss.once('connection', resolve);
    });

    client.connect();
    const relayWs = await connectionPromise;
    await nextMessage(relayWs); // hello

    relayWs.send(JSON.stringify({type: 'ready', tunnelId: 't_proxy'}));
    await waitFor(() => client.state === 'ready');

    // Send a request
    const req: RequestMessage = {
      type: 'request',
      requestId: 'r_1',
      method: 'GET',
      url: '/test?foo=bar',
      headers: {Accept: ['text/plain']},
      body: null,
    };
    relayWs.send(JSON.stringify(req));

    const resp = (await nextMessage(relayWs)) as ResponseMessage;
    assert.equal(resp.type, 'response');
    assert.equal(resp.requestId, 'r_1');
    assert.equal(resp.status, 200);
    assert.deepEqual(resp.headers['content-type'], ['text/plain']);
    assert.deepEqual(resp.headers['x-custom'], ['hello']);
    assert.equal(
      Buffer.from(resp.body!, 'base64').toString(),
      'ok',
    );

    client.disconnect();
    targetServer.close();
  });

  it('sends error when target is unreachable', async () => {
    // Target on a port nothing is listening on
    const client = createClient('http://127.0.0.1:1');
    const connectionPromise = new Promise<WsClient>(resolve => {
      wss.once('connection', resolve);
    });

    client.connect();
    const relayWs = await connectionPromise;
    await nextMessage(relayWs); // hello

    relayWs.send(JSON.stringify({type: 'ready', tunnelId: 't_err'}));
    await waitFor(() => client.state === 'ready');

    const req: RequestMessage = {
      type: 'request',
      requestId: 'r_err',
      method: 'GET',
      url: '/',
      headers: {},
      body: null,
    };
    relayWs.send(JSON.stringify(req));

    const errMsg = (await nextMessage(relayWs)) as ErrorMessage;
    assert.equal(errMsg.type, 'error');
    assert.equal(errMsg.requestId, 'r_err');
    assert.ok(errMsg.message.length > 0);

    client.disconnect();
  });

  /** Connect a client and complete the handshake, returning the relay WS. */
  async function connectAndReady(
    client: TunnelClient,
    tunnelId = 't_test',
  ): Promise<WsClient> {
    const connectionPromise = new Promise<WsClient>(resolve => {
      wss.once('connection', resolve);
    });
    client.connect();
    const relayWs = await connectionPromise;
    await nextMessage(relayWs); // hello
    relayWs.send(JSON.stringify({type: 'ready', tunnelId}));
    await waitFor(() => client.state === 'ready');
    return relayWs;
  }

  it('streams data bidirectionally through a CONNECT tunnel', async () => {
    // Start a TCP echo server as the local target.
    const echoServer = net.createServer(socket => {
      socket.on('data', chunk => socket.write(chunk));
    });
    await new Promise<void>(resolve => {
      echoServer.listen(0, '127.0.0.1', resolve);
    });
    const echoPort = (echoServer.address() as net.AddressInfo).port;

    const client = createClient(`http://127.0.0.1:${echoPort}`);
    const relayWs = await connectAndReady(client, 't_stream');

    // Send a connect message from the "relay".
    relayWs.send(
      JSON.stringify({
        type: 'connect',
        streamId: 's_1',
        host: `127.0.0.1:${echoPort}`,
      }),
    );

    // Wait for the client to confirm the connection.
    const connected = (await nextMessage(relayWs)) as ConnectedMessage;
    assert.equal(connected.type, 'connected');
    assert.equal(connected.streamId, 's_1');

    // Send data from relay → client → echo server → client → relay.
    const payload = Buffer.from('hello tunnel').toString('base64');
    relayWs.send(
      JSON.stringify({type: 'data', streamId: 's_1', data: payload}),
    );

    const echoed = (await nextMessage(relayWs)) as StreamDataMessage;
    assert.equal(echoed.type, 'data');
    assert.equal(echoed.streamId, 's_1');
    assert.equal(Buffer.from(echoed.data, 'base64').toString(), 'hello tunnel');

    // Close the stream from the relay side.
    relayWs.send(JSON.stringify({type: 'end', streamId: 's_1'}));

    // The client should send an 'end' back once the local socket closes.
    const end = (await nextMessage(relayWs)) as StreamEndMessage;
    assert.equal(end.type, 'end');
    assert.equal(end.streamId, 's_1');

    client.disconnect();
    echoServer.close();
  });

  it('sends stream_error when target is unreachable', async () => {
    const client = createClient('http://127.0.0.1:1');
    const relayWs = await connectAndReady(client, 't_stream_err');

    // Ask client to connect to a port nothing is listening on.
    relayWs.send(
      JSON.stringify({
        type: 'connect',
        streamId: 's_bad',
        host: '127.0.0.1:1',
      }),
    );

    const errMsg = (await nextMessage(relayWs)) as StreamErrorMessage;
    assert.equal(errMsg.type, 'stream_error');
    assert.equal(errMsg.streamId, 's_bad');
    assert.ok(errMsg.message.length > 0);

    client.disconnect();
  });

  it('cleans up streams on disconnect', async () => {
    // Start a TCP server that holds connections open.
    const holdServer = net.createServer(() => {
      // Don't close — just hold the connection.
    });
    await new Promise<void>(resolve => {
      holdServer.listen(0, '127.0.0.1', resolve);
    });
    const holdPort = (holdServer.address() as net.AddressInfo).port;

    const client = createClient(`http://127.0.0.1:${holdPort}`);
    const relayWs = await connectAndReady(client, 't_cleanup');

    // Open a stream.
    relayWs.send(
      JSON.stringify({
        type: 'connect',
        streamId: 's_cleanup',
        host: `127.0.0.1:${holdPort}`,
      }),
    );
    const connected = (await nextMessage(relayWs)) as ConnectedMessage;
    assert.equal(connected.type, 'connected');

    // Disconnect the client — should not throw or leak.
    client.disconnect();
    assert.equal(client.state, 'disconnected');

    holdServer.close();
  });

  it('reconnects after relay closes the connection', async () => {
    const client = createClient();

    let connectionCount = 0;
    const secondConnection = new Promise<WsClient>(resolve => {
      wss.on('connection', ws => {
        connectionCount++;
        if (connectionCount === 2) {
          resolve(ws);
        }
      });
    });

    const firstConnection = new Promise<WsClient>(resolve => {
      wss.once('connection', resolve);
    });

    client.connect();
    const firstWs = await firstConnection;
    await nextMessage(firstWs); // hello

    // Close the relay side — client should reconnect
    firstWs.close();

    const secondWs = await secondConnection;
    const hello = (await nextMessage(secondWs)) as HelloMessage;
    assert.equal(hello.type, 'hello');

    client.disconnect();
  });
});
