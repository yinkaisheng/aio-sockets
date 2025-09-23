#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author: yinkaisheng@foxmail.com
# support python 3.8+
import sys
import json
import socket
from datetime import datetime

import aio_sockets as aio
from log_util import Fore, log


_auto_disconnect: bool = False


async def tcp_client(sock: aio.TCPSocket):
    raddr: aio.IPAddress = sock.getpeername()
    log(f'new client {raddr}')
    while True:
        data = await sock.recv()
        if not data:
            log(f'remote {raddr} closed')
            break
        log(f'recv: {data} from {raddr}')
        msg = {
            "time": str(datetime.now()),
            "client": f'{raddr[0]}:{raddr[1]}'
        }
        data = json.dumps(msg).encode()
        log(f'send: {data} to   {raddr}')
        await sock.send(data)
        if _auto_disconnect:
            log(f'server closes {raddr}')
            break
    await sock.close()


async def tcp_server(host: str = '0.0.0.0', port: int = 25000):
    if not host:
        family = socket.AF_UNSPEC
        support = 'IPv4 and IPv6'
    elif ':' in host:
        family=socket.AF_INET6
        support = 'IPv6'
    else:
        family=socket.AF_INET
        support = 'IPv4'
    async with await aio.start_tcp_server(tcp_client, host, port, family=family) as server:
        sock: aio.trsock.TransportSocket = server.sockets[0]
        log(f'serving on {sock.getsockname()} {family!r}, support {support}')
        await server.serve_forever()


async def udp_server(host: str = '0.0.0.0', port: int = 25000):
    if not host:
        family=socket.AF_INET6
        support = 'IPv4 and IPv6'
        raw_sock = socket.socket(family, socket.SOCK_DGRAM)
        raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        raw_sock.bind((host, port))
        sock = await aio.create_udp_socket(sock=raw_sock)
    elif ':' in host:
        family=socket.AF_INET6
        support = 'IPv6'
        sock = await aio.create_udp_socket(local_addr=(host, port), family=family)
    else:
        family=socket.AF_INET
        support = 'IPv4'
        sock = await aio.create_udp_socket(local_addr=(host, port), family=family)
    log(f'serving on {sock.getsockname()} {family!r}, support {support}')
    async with sock:
        while True:
            data, raddr = await sock.recvfrom()
            log(f'recv from {raddr}: {data}')
            if raddr[0].startswith('::ffff:'):
                client_ip = raddr[0][7:] # client is ipv4
            else:
                client_ip = raddr[0]
            msg = {
                "time": str(datetime.now()),
                "client": f'{client_ip}:{raddr[1]}'
            }
            try:
                js = json.loads(data)
                seq = js.get('seq', None)
                if seq is not None:
                    msg['seq'] = seq
            except Exception as ex:
                pass
            data = json.dumps(msg).encode()
            log(f'send to {raddr}: {data}')
            sock.sendto(data, raddr)


def echo_server(host: str, port: int, net: str):
    if net == 'all':
        async def tcp_and_udp_server(host: str, port: int):
            aio.create_task(tcp_server(host, port))
            await udp_server(host, port)
        aio.run(tcp_and_udp_server(host, port))
    elif net == 'tcp':
        aio.run(tcp_server(host, port))
    elif net == 'udp':
        aio.run(udp_server(host, port))


def get_lan_ip(connect_host: str = '8.8.8.8') -> str:
    ip = ''
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((connect_host, 80))
        ip = sock.getsockname()[0]
    except Exception as ex:
        pass
    finally:
        sock.close()
    return ip


if __name__ == '__main__':
    print(f'{Fore.Cyan}{sys.executable} {Fore.Green}{sys.version}{Fore.Reset}')
    print(f'{Fore.Cyan}Local IP: {get_lan_ip()}\n\n{Fore.Reset}')

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', default='', choices=['0.0.0.0', '::', ''],
                        help='server host, "0.0.0.0" for IPv4, "::" for IPv6, "" for both, default: ""')
    parser.add_argument('-p', '--port', type=int, default=25000, help='server port')
    parser.add_argument('-n', '--net', type=str, default='all', choices=['tcp', 'udp', 'all'],
                        help='network type: tcp, udp, or all (default: all)')
    parser.add_argument('-d', '--disconnect', default=False, action='store_true',
                        help='tcp server auto disconnect after echo')

    args = parser.parse_args()
    _auto_disconnect = args.disconnect
    echo_server(args.host, args.port, args.net.lower())
