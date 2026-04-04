import socket
import aio_sockets as aio
from log_util import log

async def udp_client(server_ip: str, server_port: int, family:socket.AddressFamily = socket.AF_INET):
    sock: aio.UDPSocket
    async with await aio.create_udp_socket(remote_addr=(server_ip, server_port), family=family) as sock:
        laddr, raddr = sock.getsockname(), sock.getpeername()

        async def udp_recv_loop():
            while True:
                data, raddr = await sock.recvfrom()
                log(f'{laddr} recv from {raddr}: {data}')
                if not data:
                    break

        aio.create_task(udp_recv_loop())

        for i in range(3):
            data = f'Hi {i}'.encode()
            log(f'{laddr} send to {raddr}: {data}')
            sock.sendto(data, None)

        await aio.sleep(1) # wait and make udp_recv_loop have time to receive

async def start_udp_client():
    await udp_client('127.0.0.1', 25000)
    await aio.wait_all_tasks_done() # wait for udp_recv_loop to finish

aio.run(start_udp_client())