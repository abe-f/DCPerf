#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import multiprocessing
import os
import pathlib
import shlex
import subprocess
import time
from typing import List


BENCHPRESS_ROOT = pathlib.Path(os.path.abspath(__file__)).parents[2]
TAO_BENCH_DIR = os.path.join(BENCHPRESS_ROOT, "benchmarks", "tao_bench")

MEM_USAGE_FACTOR = 0.75  # not really matter
MAX_CLIENT_CONN = 32768


def get_affinitize_nic_path():
    default_path = "/usr/local/bin/affinitize_nic"
    if os.path.exists(default_path):
        return default_path
    else:
        return os.path.join(TAO_BENCH_DIR, "affinitize/affinitize_nic.py")


def sanitize_clients_per_thread(val=380):
    ncores = len(os.sched_getaffinity(0))
    max_clients_per_thread = MAX_CLIENT_CONN // ncores
    return min(val, max_clients_per_thread)


def run_cmd(
    cmd: List[str],
    timeout=None,
    for_real=True,
) -> str:
    print(" ".join(cmd))
    if for_real:
        proc = subprocess.Popen(
            cmd,
            stderr=subprocess.STDOUT,
        )
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait()


def run_server(args):
    n_cores = len(os.sched_getaffinity(0))
    print("ABE_PRINT: n_cores = " + str(n_cores))
    print("ABE_PRINT: os.sched_getaffinity(0) = " + str(os.sched_getaffinity(0)))
    n_channels = int(n_cores * args.nic_channel_ratio)
    # set # channels
    try:
        cmd = ["ethtool", "-L", args.interface_name, "combined", str(n_channels)]
        run_cmd(cmd)
    except Exception as e:
        print(f"Failed to set channels to {n_channels}: {str(e)}")
    # set affinity
    try:
        cmd = [
            get_affinitize_nic_path(),
            "-f",
            "-a",
            "--xps",
        ]
        if args.hard_binding:
            cmd += [
                "--cpu",
                #" ".join(str(x) for x in range(n_channels)),
                str(list(os.sched_getaffinity(0))),
                #" ".join(str(x) for x in os.sched_getaffinity(0)),
            ]
        else:
            cmd += [
                "-A",
                "all-nodes",
                "--max-cpus",
                str(n_channels),
            ]
        run_cmd(cmd)
    except Exception as e:
        print(f"Failed to set affinity: {str(e)}")
    # number of threads for various paths
    n_threads = max(int(n_cores * args.fast_threads_ratio), 1)
    n_dispatchers = max(int(n_threads * args.dispatcher_to_fast_ratio), 1)
    n_slow_threads = max(int(n_threads * args.slow_to_fast_ratio), 1)
    # memory size
    n_mem = int(args.memsize * 1024 * MEM_USAGE_FACTOR)
    # port number
    if args.port_number > 0:
        port_num = args.port_number
    else:
        port_num = 11211
    print(
        f"Use {n_channels} NIC channels, {n_threads} fast threads and {n_mem} MB cache memory"
    )
    s_binary = os.path.join(TAO_BENCH_DIR, "tao_bench_server")
    extended_options = [
        "lru_crawler",
        f"ssl_chain_cert={os.path.join(TAO_BENCH_DIR, 'certs/example.crt')}",
        f"ssl_key={os.path.join(TAO_BENCH_DIR, 'certs/example.key')}",
        f"tao_it_gen_file={os.path.join(TAO_BENCH_DIR, 'leader_sizes.json')}",
        "tao_max_item_size=65536",
        "tao_gen_payload=0",
        f"tao_slow_dispatchers={n_dispatchers}",
        f"tao_num_slow_threads={n_slow_threads}",
        "tao_max_slow_reqs=1024",
        "tao_worker_sleep_ns=100",
        "tao_dispatcher_sleep_ns=100",
        "tao_slow_sleep_ns=100",
        "tao_slow_path_sleep_us=0",
        "tao_compress_items=1",
        "tao_stats_sleep_ms=5000",
        f"tao_slow_use_semaphore={args.slow_threads_use_semaphore}",
        f"tao_pin_threads={args.pin_threads}",
    ]
    server_cmd = [
        s_binary,
        "-c",
        "180000",
        "-u",
        "nobody",
        "-m",
        str(n_mem),
        "-t",
        str(n_threads),
        "-B",
        "binary",
        "-p",
        str(port_num),
        "-I",
        "16m",
        "-Z",
        "-o",
        ",".join(extended_options),
    ]
    timeout = args.warmup_time + args.test_time + 180
    run_cmd(server_cmd, timeout, args.real)


def get_client_cmd(args, n_seconds):
    # threads
    if args.num_threads > 0:
        n_threads = args.num_threads
    else:
        n_threads = len(os.sched_getaffinity(0)) - 6
        if n_threads <= 0:
            n_threads = int(len(os.sched_getaffinity(0)) * 0.8)
    # clients
    if args.clients_per_thread > 0:
        n_clients = sanitize_clients_per_thread(args.clients_per_thread)
    else:
        n_clients = sanitize_clients_per_thread(380)
    # server port number
    if args.server_port_number > 0:
        server_port_num = args.server_port_number
    else:
        server_port_num = 11211

    # mem size
    n_bytes_per_item = 434  # average from collected distribution
    mem_size_mb = int(args.server_memsize * 1024 * MEM_USAGE_FACTOR)
    n_key_min = 1
    n_keys = int(mem_size_mb * 1024 * 1024 / n_bytes_per_item)
    n_key_max = int(n_keys / args.target_hit_ratio)
    n_key_max = int(n_key_max * args.tunning_factor)
    # command
    s_binary = os.path.join(TAO_BENCH_DIR, "tao_bench_client")
    s_host = args.server_hostname
    s_cert = os.path.join(TAO_BENCH_DIR, "./certs/example.crt")
    s_key = os.path.join(TAO_BENCH_DIR, "./certs/example.key")
    client_cmd = [
        s_binary,
        "-s",
        s_host,
        "-p",
        str(server_port_num),
        "-P",
        "memcache_binary",
        f"--cert={s_cert}",
        f"--key={s_key}",
        "--tls",
        "--tls-skip-verify",
        f"--key-pattern={args.access_dist.replace('_', ':')}",
        #f"--key-pattern=R:R",
        "--distinct-client-seed",
        "--randomize",
        "-R",
        "--hide-histogram",
        "--expiry-range=1800-1802",
        f"--data-size-range={args.data_size_min}-{args.data_size_max}",
        f"--ratio={args.set_get_ratio.replace('_', ':')}",
        #f"--ratio=0:1"
        f"--key-minimum={n_key_min}",
        f"--key-maximum={n_key_max}",
        "-t",
        str(n_threads),
        f"--clients={n_clients}",
        "--threads-coherence=0",
        "--clients-coherence=3",
        "--key-bytes=220",
        f"--test-time={n_seconds}",
    ]
    return client_cmd


def run_client(args):
    if args.sanity > 0:
        cmd = f"iperf3 -c {args.server_hostname} -P4"
        subprocess.run(shlex.split(cmd))

    print("warm up phase ...")
    cmd = get_client_cmd(args, n_seconds=args.warmup_time)
    run_cmd(cmd, timeout=args.warmup_time + 30, for_real=args.real)
    if args.real:
        time.sleep(5)
    print("execution phase ...")
    cmd = get_client_cmd(args, n_seconds=args.test_time)
    run_cmd(cmd, timeout=args.test_time + 30, for_real=args.real)


def init_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # sub-command parsers
    sub_parsers = parser.add_subparsers(help="Commands")
    server_parser = sub_parsers.add_parser(
        "server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="run server",
    )
    client_parser = sub_parsers.add_parser(
        "client",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="run client",
    )
    # server-side arguments
    server_parser.add_argument(
        "--memsize", type=int, required=True, help="memory size, e.g. 64 or 96"
    )
    server_parser.add_argument(
        "--nic-channel-ratio",
        type=float,
        default=0.5,
        help="ratio of # NIC channels to # logical cores",
    )
    server_parser.add_argument(
        "--fast-threads-ratio",
        type=float,
        default=0.75,
        help="ratio of # fast threads to # logical cores",
    )
    server_parser.add_argument(
        "--dispatcher-to-fast-ratio",
        type=float,
        default=0.25,
        help="ratio of # dispatchers to # fast threads",
    )
    server_parser.add_argument(
        "--slow-to-fast-ratio",
        type=float,
        default=3,
        help="ratio of # fast threads to # slow threads",
    )
    server_parser.add_argument(
        "--slow-threads-use-semaphore",
        type=int,
        default=0,
        help="use semaphore to wait for slow requests, set to 0 to turn off",
    )
    server_parser.add_argument(
        "--pin-threads",
        type=int,
        default=0,
        help="pin tao bench threads to dedicated cpu cores, set to nonzero to turn on",
    )
    server_parser.add_argument(
        "--interface-name",
        type=str,
        default="eth0",
        help="name of the NIC interface",
    )
    server_parser.add_argument(
        "--hard-binding",
        action="store_true",
        help="hard bind NIC channels to cores",
    )
    server_parser.add_argument(
        "--port-number",
        type=int,
        default=11211,
        help="port number of server",
    )
    # client-side arguments
    client_parser.add_argument(
        "--set-get-ratio", type=str, default="0_1", help="Set to 0_1 for 0 writes, 30_70 for 30% writes"
    )
    client_parser.add_argument(
        "--access-dist", type=str, default="R_R", help="Set this to X_X, where X is either R, G, or Z for random, gaussian, or zipf distribution (SET_GET)"
    )
    client_parser.add_argument(
        "--server-hostname", type=str, required=True, help="server hostname"
    )
    client_parser.add_argument(
        "--server-memsize",
        type=int,
        required=True,
        help="server memory size, e.g. 64, 96",
    )
    client_parser.add_argument(
        "--num-threads",
        type=int,
        default=0,
        help="# threads; default 0 - use (core count - 6)",
    )
    client_parser.add_argument(
        "--target-hit-ratio", type=float, default=0.9, help="target hit ratio"
    )
    client_parser.add_argument(
        "--data-size-min", type=int, default=8191, help="minimum data size"
    )
    client_parser.add_argument(
        "--data-size-max", type=int, default=8193, help="maximum data size"
    )
    client_parser.add_argument(
        "--tunning-factor",
        type=float,
        default=0.807,
        help="tuning factor for key range to get target hit ratio",
    )
    client_parser.add_argument(
        "--clients-per-thread",
        type=int,
        default=sanitize_clients_per_thread(380),
        help="Number of clients per thread",
    )
    client_parser.add_argument(
        "--server-port-number",
        type=int,
        default=11211,
        help="port number of server",
    )
    client_parser.add_argument(
        "--sanity",
        type=int,
        default=0,
        help="sanity check for the network bandwidth and latency between the server and the client.",
    )

    # for both server & client
    for x_parser in [server_parser, client_parser]:
        x_parser.add_argument(
            "--warmup-time", type=int, default=1200, help="warmup time in seconds"
        )
        x_parser.add_argument(
            "--test-time", type=int, default=360, help="test time in seconds"
        )
        x_parser.add_argument("--real", action="store_true", help="for real")
    # functions
    server_parser.set_defaults(func=run_server)
    client_parser.set_defaults(func=run_client)
    return parser


if __name__ == "__main__":
    parser = init_parser()
    args = parser.parse_args()
    args.func(args)
