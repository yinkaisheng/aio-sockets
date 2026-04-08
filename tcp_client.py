import asyncio
import socket
import aio_sockets as aio
from log_util import Fore, log

async def tcp_client(server_ip: str, server_port: int, timeout: int = 5,
                     family:socket.AddressFamily = socket.AF_INET):
    log(f'connect to {server_ip}:{server_port}')
    sock: aio.TCPSocket = await aio.open_tcp_connection(server_ip, server_port, family=family)
    laddr, raddr = sock.getsockname(), sock.getpeername()
    log(f'connected, local address={laddr}')
    async with sock:
        for i in range(3):
            data = f'Hi {i}'.encode()
            log(f'{laddr} send to {raddr}: {data}')
            if i == 0:
                await sock.send(data)
            # data = await sock.recv()
            try:
                data = await sock.recv_timeout(n=8192, timeout=timeout)
                log(f'{laddr} recv: {data}')
                if not data:
                    log(f'server closed connection from {laddr}')
                    break
            except asyncio.TimeoutError as ex:
                log(f'{laddr} recv timeout, ex={ex!r}')

aio.run(tcp_client('127.0.0.1', 25000))