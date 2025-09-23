#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author: yinkaisheng@foxmail.com
# support python 3.8+
from typing import (Any, Awaitable, Callable, Coroutine, List, Optional, Set, Tuple, Union)
from asyncio import DatagramProtocol, DatagramTransport, Event, StreamReader, StreamWriter, Queue, Task, TimeoutError
from asyncio import (all_tasks, base_events, create_task, gather, get_running_loop, open_connection,
                     run, sleep, start_server, trsock, wait, wait_for)
from asyncio import FIRST_COMPLETED
from asyncio.streams import _DEFAULT_LIMIT


__version__ = '0.1.0'

IPv4Address = Tuple[str, int]
IPv6Address = Tuple[str, int, int, int]  # (host, port, flow_info, scope_id)
IPAddress = Union[IPv4Address, IPv6Address]
logfunc = print


try:
    from asyncio import to_thread # python 3.9 introduced to_thread
except ImportError:
    import functools
    import contextvars
    from asyncio import events

    async def to_thread(func, /, *args, **kwargs):
        """Asynchronously run function *func* in a separate thread.

        Any *args and **kwargs supplied for this function are directly passed
        to *func*. Also, the current :class:`contextvars.Context` is propagated,
        allowing context variables from the main thread to be accessed in the
        separate thread.

        Return a coroutine that can be awaited to get the eventual result of *func*.
        """
        loop = events.get_running_loop()
        ctx = contextvars.copy_context()
        func_call = functools.partial(ctx.run, func, *args, **kwargs)
        return await loop.run_in_executor(None, func_call)


class TCPSocket:
    def __init__(self, reader: StreamReader, writer: StreamWriter):
        self.reader = reader
        self.writer = writer

    async def send(self, data: bytes) -> None:
        self.writer.write(data)
        await self.writer.drain()

    async def recv(self, n: int = 8192) -> bytes:
        return await self.reader.read(n) # if n is -1, read until EOF, will block until socket is closed

    async def recv_exactly(self, n: int) -> bytes:
        return await self.reader.readexactly(n)

    async def recv_timeout(self, n: int = 8192, timeout: float = 10) -> bytes:
        """
        You should catch TimeoutError when calling this method.
        """
        return await wait_for(self.reader.read(n), timeout=timeout)

    async def close(self) -> None:
        self.writer.close()
        await self.writer.wait_closed()

    def getsockname(self) -> IPAddress:
        return self.writer.get_extra_info('sockname')

    def getpeername(self) -> IPAddress:
        return self.writer.get_extra_info('peername')

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        await self.close()


async def start_tcp_server(client_connected_cb: Callable[[TCPSocket], Awaitable[None]],
                           ip: str = None, port: int = None,
                           *, limit=_DEFAULT_LIMIT, **kwds) -> base_events.Server:
    async def tcp_client_cb(reader: StreamReader, writer: StreamWriter):
        sock = TCPSocket(reader, writer)
        await client_connected_cb(sock)
    return await start_server(tcp_client_cb, ip, port, limit=limit, **kwds)


async def open_tcp_connection(host: str = None, port: int = None, *, limit=_DEFAULT_LIMIT, **kwds) -> TCPSocket:
    reader, writer = await open_connection(host, port, limit=limit, **kwds)
    return TCPSocket(reader, writer)


class UDPProtocol(DatagramProtocol):
    def __init__(self, queue_size: int):
        self.error: Optional[Exception] = None
        self.packets_queue = Queue(queue_size)

    def connection_made(self, transport: DatagramTransport) -> None:
        pass # real type: proactor_events._ProactorDatagramTransport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.packets_queue.put_nowait((None, None))

    def datagram_received(self, data: bytes, addr: IPAddress) -> None:
        self.packets_queue.put_nowait((data, addr))

    def error_received(self, exc: Exception) -> None:
        self.error = exc
        self.packets_queue.put_nowait((None, None))

    async def recvfrom(self) -> Tuple[bytes, IPAddress]:
        return await self.packets_queue.get()

    def raise_if_error(self) -> None:
        if self.error is None:
            return
        error = self.error
        self.error = None
        raise error


class UDPSocket:
    """
    Use function `asyncudp.create_udp_socket()` to create an instance of this class.
    """

    def __init__(self, transport: DatagramTransport, protocol: UDPProtocol):
        self.transport = transport
        self.protocol = protocol

    def sendto(self, data: bytes, addr: IPAddress = None) -> None:
        self.transport.sendto(data, addr)
        self.protocol.raise_if_error()

    async def recvfrom(self) -> Tuple[bytes, IPAddress]:
        data_and_addr = await self.protocol.recvfrom()
        self.protocol.raise_if_error()
        return data_and_addr

    async def recvfrom_timeout(self, timeout: float = 10) -> Tuple[bytes, IPAddress]:
        """
        You should catch TimeoutError when calling this method.
        """
        return await wait_for(self.recvfrom(), timeout=timeout)

    def close(self) -> None:
        self.transport.close()

    def getsockname(self) -> IPAddress:
        return self.transport.get_extra_info('sockname')

    def getpeername(self) -> IPAddress:
        return self.transport.get_extra_info('peername')

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        self.close()


async def create_udp_socket(local_addr: Tuple[str, int] = None, remote_addr: Tuple[str, int] = None,
                        family: int = 0, proto: int = 0, flags: int = 0,
                        # reuse_address=None,
                        reuse_port=None,
                        allow_broadcast=None,
                        sock=None,
                        queue_size: int = 0) -> UDPSocket:
    transport: DatagramTransport
    protocol: UDPProtocol
    transport, protocol = await get_running_loop().create_datagram_endpoint(
        lambda: UDPProtocol(queue_size),
        local_addr=local_addr, remote_addr=remote_addr,
        family=family, proto=proto, flags=flags,
        # reuse_address=reuse_address, # python 3.11+ does not support reuse_address
        reuse_port=reuse_port,
        allow_broadcast=allow_broadcast,
        sock=sock)
    return UDPSocket(transport, protocol)


async def wait_all_tasks_done(tasks: List[Task] = None, log_result: bool = True) -> None:
    Cyan = "\033[96m"
    Green = "\033[92m"
    Magenta = "\033[95m"
    Reset = "\033[0m"

    if tasks is not None:
        ret: List[Any] = await gather(*tasks, return_exceptions=True)
        if log_result:
            for task, result in zip(tasks, ret):
                if isinstance(result, Exception):
                    logfunc(f'task: {Green}{task.get_name()}{Reset} function: {Cyan}{task.get_coro().__name__}{Reset} gets an exception: {Magenta}{result!r}{Reset}')
                else:
                    logfunc(f'task: {Green}{task.get_name()}{Reset} function: {Cyan}{task.get_coro().__name__}{Reset} returns: {result!r}')
        return

    task_empty_times = 0
    while True:
        # if a task launch another task,
        # asyncio.all_tasks() may not get sub task when first called,
        # need a loop to get all tasks
        tasks: Set[Task] = all_tasks()
        for task in tasks: # set has no order
            if task.get_name() == 'Task-1':
                # Task-1 is the main task(called by asyncio.run), must remove it
                # coro = task.get_coro()
                # logfunc(task.get_name(), coro.__name__, task, coro)
                tasks.remove(task)
                break
        if tasks:
            tasks = list(tasks) # convert set to list, make it ordered
            ret: List[Any] = await gather(*tasks, return_exceptions=True)
            if log_result:
                for task, result in zip(tasks, ret):
                    if isinstance(result, Exception):
                        logfunc(f'task: {Green}{task.get_name()}{Reset} function: {Cyan}{task.get_coro().__name__}{Reset} gets an exception: {Magenta}{result!r}{Reset}')
                    else:
                        logfunc(f'task: {Green}{task.get_name()}{Reset} function: {Cyan}{task.get_coro().__name__}{Reset} returns: {result!r}')
            task_empty_times = 0
        else:
            task_empty_times += 1
            if task_empty_times > 2:
                break