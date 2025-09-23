#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author: yinkaisheng@foxmail.com
# support python 3.8+
import os
import sys
import json
import socket
from datetime import datetime

import aio_sockets as aio
from log_util import Fore, log

# do not create a asyncio Queue, Event, etc. in global scope in python3.9 or lower version,
#   otherwise it will cause error: attached to a different loop
# if you create a asyncio Queue in global scope in python3.9 or lower version,
#   await queue.get() will block forever even the producer puts an item to queue later
_echo_queue: aio.Queue = None


async def tcp_client(server_ip: str, server_port: int, timeout: int = 5):
    log(f'connect to {server_ip}:{server_port}')
    family=socket.AF_INET6 if ':' in server_ip else socket.AF_INET
    try:
        sock = await aio.open_tcp_connection(server_ip, server_port, family=family)
    except Exception as ex:
        log(f'open_connection failed, {Fore.Red}{ex!r}{Fore.Reset}')
        return
    laddr = sock.getsockname()
    raddr = sock.getpeername()
    log(f'connected, local address={laddr}')
    while True:
        msg = {
            "time": str(datetime.now()),
        }
        data = json.dumps(msg).encode()
        log(f'{laddr} send to {raddr}: {data}')
        await sock.send(data)
        try:
            data = await sock.recv_timeout(n=8192, timeout=timeout)
            log(f'{laddr} recv: {data}')
            if not data:
                log(f'server closed connection from {laddr}')
                break
        except TimeoutError as ex:
            log(f'{laddr} recv timeout, ex={ex!r}')
        input = await _echo_queue.get()
        if input == 'q':
            log(f'{laddr} client close connection')
            break
    await sock.close()
    await sock.close() # can call many times


async def udp_client(server_ip: str, server_port: int, timeout: int = 2):
    family=socket.AF_INET6 if ':' in server_ip else socket.AF_INET
    # when set remote_addr, it can only send to and receive from remote_addr
    async with await aio.create_udp_socket(remote_addr=(server_ip, server_port), family=family) as sock:
        laddr = sock.getsockname()
        raddr = sock.getpeername()

        async def udp_recv_loop():
            while True:
                data, raddr = await sock.recvfrom()
                log(f'{laddr} recv from {raddr}: {data}')
                if not data:
                    break

        aio.create_task(udp_recv_loop())

        seq = 0
        while True:
            msg = {
                "time": str(datetime.now()),
                "seq": seq
            }
            seq += 1
            data = json.dumps(msg).encode()
            log(f'{laddr} send to {raddr}: {data}')
            sock.sendto(data, None)
            inputs = await _echo_queue.get()
            if inputs == 'q':
                break


async def read_input_loop():
    while True:
        line = await aio.to_thread(sys.stdin.readline)
        line = line.strip()
        log(f'line={line!r}, q size = {_echo_queue.qsize()}')
        if line == 'q':
            log('exit')
            await _echo_queue.put(line)
            break
        else:
            await _echo_queue.put(line)


async def async_main(server: str, port: int, udp: bool, count: int):
    global _echo_queue
    _echo_queue = aio.Queue()
    aio.create_task(read_input_loop())
    client_func = udp_client if udp else tcp_client
    for _ in range(count):
        aio.create_task(client_func(server, port, timeout=2))

    await aio.wait_all_tasks_done()


def main(server: str, port: int, udp: bool, count: int):
    print(f'{Fore.Magenta}press {Fore.Green}Enter{Fore.Magenta} to send message, press {Fore.Red}q{Fore.Magenta} to exit{Fore.Reset}')
    aio.run(async_main(server, port, udp, count))


if __name__ == '__main__':
    file = os.path.basename(__file__)
    print(f'use {Fore.Cyan}python {file} -s ::1 -p 25000{Fore.Reset} as an IPv6 tcp client')
    print(f'use {Fore.Cyan}python {file} -s ::1 -p 25000 -u {Fore.Reset} as an IPv6 udp client')
    print(f'use {Fore.Cyan}python {file} -s 127.0.0.1 -p 25000{Fore.Reset} as an IPv4 tcp client')
    print(f'use {Fore.Cyan}python {file} -s 127.0.0.1 -p 25000 -u{Fore.Reset} as an IPv4 udp client')

    try:
        import click
        has_click = True
    except:
        has_click = False

    if has_click:
        @click.command()
        @click.option('-s', '--server', default='127.0.0.1', prompt='input server ip', help='server ip')
        @click.option('-p', '--port', type=int, default=25000, prompt='input server port', help='server port')
        @click.option('-u', '--udp', is_flag=True, default=False, flag_value=True, prompt='is udp', help='udp mode')
        @click.option('-c', '--count', type=int, default=1, prompt='input client count', help='client count')
        def _wrap_function(server: str, port: int, udp: bool, count: int):
            main(server, port, udp, count)
        _wrap_function()
    else:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('-s', '--server', default='127.0.0.1', help='server ip')
        parser.add_argument('-p', '--port', type=int, default=25000, help='server port')
        parser.add_argument('-u', '--udp', default=False, action='store_true', help='udp mode')
        parser.add_argument('-c', '--count', type=int, default=1, help='client count')

        args = parser.parse_args()
        main(args.server, args.port, args.udp, args.count)
