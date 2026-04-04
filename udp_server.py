import socket
import aio_sockets as aio
from log_util import log

async def udp_server(host: str, port: int, family:socket.AddressFamily = socket.AF_INET):
    sock: aio.UDPSocket = await aio.create_udp_socket(local_addr=(host, port), family=family)
    log(f'serving on {sock.getsockname()} {family!r}')
    async with sock:
        while True:
            data, raddr = await sock.recvfrom()
            log(f'recv from {raddr}: {data}')
            log(f'send to {raddr}: {data}')
            sock.sendto(data, raddr)

aio.run(udp_server('0.0.0.0', 25000))