"""Privileged TCP forwarder used by the IP LOGGER for ports below 1024.

This script is deliberately self-contained: it is executed by a separate,
elevated interpreter (pkexec / UAC / osascript).  It listens on the privileged
port and pipes every connection to the unprivileged loopback site hosted by
``IpLogger`` inside the main application.

The parent signals shutdown by creating the ``stop_file``.  A log file is
written on failure so the GUI can show a useful message when the native
password prompt is cancelled or the listener cannot be bound.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import traceback
from pathlib import Path

CHUNK_SIZE = 64 * 1024


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(CHUNK_SIZE):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        try:
            writer.close()
        except (ConnectionError, OSError):
            pass


async def _relay(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    target_host: str,
    target_port: int,
    connections: set[asyncio.Task],
    header: bytes = b"",
) -> None:
    try:
        server_reader, server_writer = await asyncio.open_connection(
            target_host, target_port
        )
    except OSError:
        client_writer.close()
        return

    if header:
        # Announce the real client to the app via PROXY protocol v1.
        server_writer.write(header)
        try:
            await server_writer.drain()
        except (ConnectionError, OSError):
            client_writer.close()
            server_writer.close()
            return

    upstream = asyncio.create_task(_pipe(client_reader, server_writer))
    downstream = asyncio.create_task(_pipe(server_reader, client_writer))
    for task in (upstream, downstream):
        connections.add(task)
        task.add_done_callback(connections.discard)
    await asyncio.gather(upstream, downstream, return_exceptions=True)


def _proxy_header(peer: tuple | None, local: tuple | None) -> bytes:
    """Build a PROXY protocol v1 header for the accepted connection."""
    if not peer:
        return b"PROXY UNKNOWN\r\n"
    source = str(peer[0])
    source_port = peer[1] if len(peer) > 1 else 0
    family = "TCP6" if ":" in source else "TCP4"
    if local:
        destination = str(local[0])
        destination_port = local[1] if len(local) > 1 else 0
    else:
        destination = "::" if family == "TCP6" else "0.0.0.0"
        destination_port = 0
    line = f"PROXY {family} {source} {destination} {source_port} {destination_port}\r\n"
    return line.encode("ascii", "ignore")


async def _serve(
    listen_port: int,
    target_port: int,
    stop_file: Path,
    stop_event: asyncio.Event,
) -> None:
    connections: set[asyncio.Task] = set()

    async def accept(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        header = _proxy_header(
            writer.get_extra_info("peername"),
            writer.get_extra_info("sockname"),
        )
        task = asyncio.create_task(
            _relay(reader, writer, "127.0.0.1", target_port, connections, header)
        )
        connections.add(task)
        task.add_done_callback(connections.discard)

    servers: list[asyncio.AbstractServer] = []
    for host in ("0.0.0.0", "::"):
        try:
            servers.append(
                await asyncio.start_server(accept, host=host, port=listen_port)
            )
        except OSError:
            continue
    if not servers:
        raise OSError(f"Could not bind privileged port {listen_port}")

    try:
        while not stop_event.is_set() and not stop_file.exists():
            await asyncio.wait_for(stop_event.wait(), timeout=0.25)
    except TimeoutError:
        pass
    finally:
        for server in servers:
            server.close()
        for server in servers:
            await server.wait_closed()
        if connections:
            for task in list(connections):
                task.cancel()
            await asyncio.gather(*connections, return_exceptions=True)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("listen_port", type=int)
    parser.add_argument("target_port", type=int)
    parser.add_argument("stop_file", type=Path)
    parser.add_argument("log_file", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop_event = asyncio.Event()

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        loop.run_until_complete(
            _serve(args.listen_port, args.target_port, args.stop_file, stop_event)
        )
    except BaseException:
        try:
            args.log_file.write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        return 1
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
