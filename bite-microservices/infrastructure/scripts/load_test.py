#!/usr/bin/env python3
"""
BITE.co Microservices Load Test
================================
Tests ASR 1 (Performance) and ASR 2 (Security) simultaneously.

Usage:
    python load_test.py --kong-ip <KONG_IP> --token <JWT_TOKEN> --users 100

Requirements:
    pip install requests statistics
"""
import argparse
import concurrent.futures
import statistics
import time
import sys
from datetime import date, timedelta

import requests


def parse_args():
    p = argparse.ArgumentParser(description='BITE.co Load Test')
    p.add_argument('--kong-ip', required=True, help='Kong EC2 public IP')
    p.add_argument('--kong-port', default='8000', help='Kong port (default: 8000)')
    p.add_argument('--token', default='', help='Valid JWT token for auth tests')
    p.add_argument('--company-id', default='1', help='Company ID to query')
    p.add_argument('--users', type=int, default=100, help='Concurrent users (default: 100)')
    p.add_argument('--requests-per-user', type=int, default=5, help='Requests per user')
    p.add_argument('--asr', choices=['1', '2', 'both'], default='both', help='Which ASR to test')
    return p.parse_args()


def make_asr1_request(base_url, company_id, token, user_id):
    """Single request for ASR 1 — expenses by area with valid auth."""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    url = (
        f"{base_url}/finops/expenses/by-area/"
        f"?company_id={company_id}"
        f"&start_date={start_date.isoformat()}"
        f"&end_date={end_date.isoformat()}"
    )
    headers = {'Authorization': f'Bearer {token}'} if token else {}

    start = time.time()
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        latency_ms = (time.time() - start) * 1000
        return {
            'user_id': user_id,
            'status_code': resp.status_code,
            'latency_ms': latency_ms,
            'source': resp.json().get('source', 'unknown') if resp.ok else 'error',
            'success': resp.status_code == 200,
        }
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return {
            'user_id': user_id,
            'status_code': 0,
            'latency_ms': latency_ms,
            'source': 'error',
            'success': False,
            'error': str(e),
        }


def make_asr2_unauthorized_request(base_url, company_id, user_id):
    """Single request for ASR 2 — no token, should get 403."""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    url = (
        f"{base_url}/finops/expenses/by-area/"
        f"?company_id={company_id}"
        f"&start_date={start_date.isoformat()}"
        f"&end_date={end_date.isoformat()}"
    )

    start = time.time()
    try:
        resp = requests.get(url, timeout=10)
        latency_ms = (time.time() - start) * 1000
        return {
            'user_id': user_id,
            'status_code': resp.status_code,
            'latency_ms': latency_ms,
            'blocked': resp.status_code == 403,
        }
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return {
            'user_id': user_id,
            'status_code': 0,
            'latency_ms': latency_ms,
            'blocked': False,
            'error': str(e),
        }


def run_asr1_test(base_url, company_id, token, num_users, requests_per_user):
    """ASR 1: p95 latency < 150ms under 100 concurrent users."""
    print(f"\n{'='*60}")
    print(f"ASR 1 — Performance Test")
    print(f"Target: p95 latency < 150ms | Users: {num_users} | Requests/user: {requests_per_user}")
    print(f"{'='*60}")

    all_results = []
    tasks = [(base_url, company_id, token, i) for i in range(num_users) for _ in range(requests_per_user)]

    start_wall = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(make_asr1_request, *task) for task in tasks]
        for f in concurrent.futures.as_completed(futures):
            all_results.append(f.result())
    total_time = time.time() - start_wall

    latencies = [r['latency_ms'] for r in all_results]
    success_count = sum(1 for r in all_results if r['success'])
    cache_hits = sum(1 for r in all_results if r.get('source') == 'cache')

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print(f"\nResults ({len(all_results)} total requests in {total_time:.1f}s):")
    print(f"  Success rate:  {success_count}/{len(all_results)} ({100*success_count/len(all_results):.1f}%)")
    print(f"  Cache hits:    {cache_hits}/{len(all_results)}")
    print(f"  Latency p50:   {p50:.1f}ms")
    print(f"  Latency p95:   {p95:.1f}ms  {'✅ PASS' if p95 < 150 else '❌ FAIL'} (target: <150ms)")
    print(f"  Latency p99:   {p99:.1f}ms")
    print(f"  Min/Max:       {min(latencies):.1f}ms / {max(latencies):.1f}ms")
    print(f"  Throughput:    {len(all_results)/total_time:.1f} req/s")

    asr_pass = p95 < 150
    print(f"\n  ASR 1 Result: {'✅ PASSED' if asr_pass else '❌ FAILED'}")
    return asr_pass, p95


def run_asr2_test(base_url, company_id, num_users):
    """ASR 2: 100% of unauthorized requests blocked with 403."""
    print(f"\n{'='*60}")
    print(f"ASR 2 — Security Test (Unauthorized Access)")
    print(f"Target: 100% of requests without valid role blocked with 403")
    print(f"{'='*60}")

    tasks = [(base_url, company_id, i) for i in range(num_users)]

    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(make_asr2_unauthorized_request, *task) for task in tasks]
        for f in concurrent.futures.as_completed(futures):
            all_results.append(f.result())

    blocked = sum(1 for r in all_results if r['blocked'])
    block_rate = 100 * blocked / len(all_results)

    auth_latencies = [r['latency_ms'] for r in all_results]
    auth_latencies.sort()
    auth_p95 = auth_latencies[int(len(auth_latencies) * 0.95)]

    print(f"\nResults ({len(all_results)} unauthorized requests):")
    print(f"  Blocked (403): {blocked}/{len(all_results)} ({block_rate:.1f}%)  {'✅ PASS' if block_rate == 100 else '❌ FAIL'}")
    print(f"  Auth latency p95: {auth_p95:.1f}ms  {'✅ PASS' if auth_p95 < 50 else '❌ FAIL'} (target: <50ms)")

    asr_pass = block_rate == 100 and auth_p95 < 50
    print(f"\n  ASR 2 Result: {'✅ PASSED' if asr_pass else '❌ FAILED'}")
    return asr_pass


def main():
    args = parse_args()
    base_url = f"http://{args.kong_ip}:{args.kong_port}"

    print(f"\n🚀 BITE.co Microservices Load Test")
    print(f"   Kong: {base_url}")
    print(f"   Company ID: {args.company_id}")

    results = {}

    if args.asr in ('1', 'both'):
        if not args.token:
            print("\n⚠️  WARNING: No --token provided. ASR 1 test may return 403.")
        passed, p95 = run_asr1_test(base_url, args.company_id, args.token, args.users, args.requests_per_user)
        results['ASR1'] = {'passed': passed, 'p95_ms': p95}

    if args.asr in ('2', 'both'):
        passed = run_asr2_test(base_url, args.company_id, args.users)
        results['ASR2'] = {'passed': passed}

    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    for asr, data in results.items():
        status = '✅ PASSED' if data['passed'] else '❌ FAILED'
        print(f"  {asr}: {status}")

    all_passed = all(d['passed'] for d in results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
