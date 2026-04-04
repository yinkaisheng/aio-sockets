import socket
import aio_sockets as aio
from log_util import log

async def tcp_client(sock: aio.TCPSocket):
    raddr: aio.IPAddress = sock.getpeername()
    log(f'new client {raddr} connected')
    async with sock:
        while True:
            data = await sock.recv()
            if not data:
                log(f'remote {raddr} close connection')
                break
            log(f'recv: {data} from {raddr}')
            log(f'send: {data} to {raddr}')
            await sock.send(data)

async def tcp_server(host: str, port: int, family:socket.AddressFamily = socket.AF_INET):
    async with await aio.start_tcp_server(tcp_client, host, port, family=family) as server:
        sock: aio.trsock.TransportSocket = server.sockets[0]
        log(f'serving on {sock.getsockname()} {family!r}')
        await server.serve_forever()

aio.run(tcp_server('0.0.0.0', 25000)) # aio.run is just asyncio.run