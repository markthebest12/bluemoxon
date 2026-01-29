#!/usr/bin/env python3
"""Performance benchmark script for the social circles endpoint.

This script measures response time metrics for the /api/v1/social-circles endpoint
across different max_books parameter values. Supports concurrent request mode for
realistic load testing with staggered request launches.

Usage:
    python backend/scripts/benchmark_social_circles.py
    python backend/scripts/benchmark_social_circles.py --iterations 20 --env prod
    python backend/scripts/benchmark_social_circles.py --concurrent 5 --iterations 50
    python backend/scripts/benchmark_social_circles.py --dry-run
    python backend/scripts/benchmark_social_circles.py --env prod --yes-i-mean-production

Output:
    JSON with timing metrics (min, max, avg, p95, p99) for each max_books value,
    plus throughput metrics (total time, requests/second) in concurrent mode.
"""

# ruff: noqa: T201

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

# Environment configuration
ENVIRONMENTS = {
    "staging": "https://staging.api.bluemoxon.com",
    "prod": "https://api.bluemoxon.com",
}

# Default max_books values to test
DEFAULT_MAX_BOOKS_VALUES = [100, 500, 1000, 5000]

# Endpoint path
ENDPOINT_PATH = "/api/v1/social-circles"

# Stagger delay between concurrent request launches (seconds)
CONCURRENT_STAGGER_DELAY = 0.05


@dataclass
class TimingMetrics:
    """Container for timing metrics in milliseconds."""

    min_ms: float
    max_ms: float
    avg_ms: float
    p95_ms: float
    p99_ms: float


@dataclass
class BenchmarkResult:
    """Result for a single benchmark run."""

    endpoint: str
    max_books: int
    iterations: int
    metrics: TimingMetrics
    environment: str
    concurrency: int = 1
    total_time_ms: float = 0.0
    requests_per_second: float = 0.0
    timestamp: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )
    errors: int = 0


def calculate_percentile(data: list[float], percentile: float) -> float:
    """Calculate the given percentile of a sorted list of values.

    Args:
        data: List of numeric values (will be sorted).
        percentile: Percentile to calculate (0-100).

    Returns:
        The value at the given percentile.
    """
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = (len(sorted_data) - 1) * percentile / 100
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_data):
        return sorted_data[-1]
    weight = index - lower
    return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight


def load_api_key(env: str) -> str:
    """Load API key from the appropriate key file.

    Args:
        env: Environment name ('staging' or 'prod').

    Returns:
        The API key as a string.

    Raises:
        FileNotFoundError: If the key file does not exist.
    """
    key_file = Path.home() / ".bmx" / f"{env}.key"
    if not key_file.exists():
        raise FileNotFoundError(f"API key file not found: {key_file}")
    return key_file.read_text().strip()


async def measure_request(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    max_books: int,
) -> tuple[float, bool]:
    """Make a single request and measure response time.

    Args:
        client: The async HTTP client.
        url: The full URL to request.
        headers: Request headers including authorization.
        max_books: The max_books parameter value.

    Returns:
        Tuple of (response_time_ms, success).
    """
    params = {"max_books": max_books}
    start = time.perf_counter()
    try:
        response = await client.get(url, headers=headers, params=params)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, response.status_code == 200
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, False


async def run_benchmark(
    env: str,
    max_books: int,
    iterations: int,
    api_key: str,
    concurrency: int = 1,
) -> BenchmarkResult:
    """Run benchmark for a specific max_books value.

    Args:
        env: Environment name ('staging' or 'prod').
        max_books: The max_books parameter to test.
        iterations: Number of requests to make.
        api_key: API key for authentication.
        concurrency: Number of concurrent requests (1 = sequential).

    Returns:
        BenchmarkResult with timing metrics.
    """
    base_url = ENVIRONMENTS[env]
    url = f"{base_url}{ENDPOINT_PATH}"
    headers = {"X-API-Key": api_key}

    timings: list[float] = []
    errors = 0

    wall_start = time.perf_counter()

    if concurrency <= 1:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(iterations):
                elapsed_ms, success = await measure_request(client, url, headers, max_books)
                if success:
                    timings.append(elapsed_ms)
                else:
                    errors += 1
                print(
                    f"  Iteration {i + 1}/{iterations}: "
                    f"{elapsed_ms:.1f}ms {'OK' if success else 'FAILED'}"
                )
    else:
        semaphore = asyncio.Semaphore(concurrency)
        results_list: list[tuple[int, float, bool]] = []

        async def bounded_request(client: httpx.AsyncClient, index: int) -> tuple[int, float, bool]:
            async with semaphore:
                elapsed_ms, success = await measure_request(client, url, headers, max_books)
                return index, elapsed_ms, success

        stagger_ms = CONCURRENT_STAGGER_DELAY * 1000
        print(
            f"  Sending {iterations} requests with concurrency={concurrency} "
            f"(stagger={stagger_ms:.0f}ms)..."
        )
        limits = httpx.Limits(max_connections=concurrency)
        async with httpx.AsyncClient(timeout=60.0, limits=limits) as client:
            tasks: list[asyncio.Task[tuple[int, float, bool]]] = []
            for i in range(iterations):
                task = asyncio.create_task(bounded_request(client, i))
                tasks.append(task)
                if i < iterations - 1:
                    await asyncio.sleep(CONCURRENT_STAGGER_DELAY)
            results_list = [await t for t in tasks]

        results_list.sort(key=lambda x: x[0])
        for index, elapsed_ms, success in results_list:
            if success:
                timings.append(elapsed_ms)
            else:
                errors += 1
            print(
                f"  Request {index + 1}/{iterations}: "
                f"{elapsed_ms:.1f}ms {'OK' if success else 'FAILED'}"
            )

    wall_end = time.perf_counter()
    total_time_ms = (wall_end - wall_start) * 1000
    successful_count = len(timings)
    total_requests = successful_count + errors
    requests_per_second = total_requests / (total_time_ms / 1000) if total_time_ms > 0 else 0

    if not timings:
        metrics = TimingMetrics(
            min_ms=0,
            max_ms=0,
            avg_ms=0,
            p95_ms=0,
            p99_ms=0,
        )
    else:
        metrics = TimingMetrics(
            min_ms=round(min(timings), 2),
            max_ms=round(max(timings), 2),
            avg_ms=round(statistics.mean(timings), 2),
            p95_ms=round(calculate_percentile(timings, 95), 2),
            p99_ms=round(calculate_percentile(timings, 99), 2),
        )

    return BenchmarkResult(
        endpoint=ENDPOINT_PATH,
        max_books=max_books,
        iterations=iterations,
        metrics=metrics,
        environment=env,
        concurrency=concurrency,
        total_time_ms=round(total_time_ms, 2),
        requests_per_second=round(requests_per_second, 2),
        errors=errors,
    )


def result_to_dict(result: BenchmarkResult) -> dict:
    """Convert BenchmarkResult to dictionary for JSON output.

    Args:
        result: The benchmark result to convert.

    Returns:
        Dictionary representation of the result.
    """
    d = asdict(result)
    return d


async def main_async(args: argparse.Namespace) -> list[dict]:
    """Run all benchmarks asynchronously.

    Args:
        args: Parsed command line arguments.

    Returns:
        List of benchmark results as dictionaries.
    """
    env = args.env
    iterations = args.iterations
    concurrency = args.concurrent
    max_books_values = args.max_books if args.max_books else DEFAULT_MAX_BOOKS_VALUES

    print(f"Loading API key for {env}...")
    try:
        api_key = load_api_key(env)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    mode_label = f"concurrent (x{concurrency})" if concurrency > 1 else "sequential"
    print(f"Running benchmark against {ENVIRONMENTS[env]}")
    print(f"Mode: {mode_label}")
    print(f"Iterations per test: {iterations}")
    print(f"Testing max_books values: {max_books_values}")
    print("-" * 60)

    results = []
    for max_books in max_books_values:
        print(f"\nBenchmarking max_books={max_books}...")
        result = await run_benchmark(env, max_books, iterations, api_key, concurrency=concurrency)
        results.append(result_to_dict(result))

        print(
            f"  Results: min={result.metrics.min_ms}ms, max={result.metrics.max_ms}ms, "
            f"avg={result.metrics.avg_ms}ms, p95={result.metrics.p95_ms}ms, "
            f"p99={result.metrics.p99_ms}ms"
        )
        if concurrency > 1:
            print(
                f"  Throughput: {result.total_time_ms:.0f}ms total, "
                f"{result.requests_per_second:.1f} req/s"
            )
        else:
            print(f"  Wall time: {result.total_time_ms:.0f}ms total")
        if result.errors > 0:
            print(f"  Errors: {result.errors}/{iterations}")

    return results


def main() -> None:
    """Main entry point for the benchmark script."""
    parser = argparse.ArgumentParser(
        description="Performance benchmark for the social circles endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backend/scripts/benchmark_social_circles.py
  python backend/scripts/benchmark_social_circles.py --iterations 20
  python backend/scripts/benchmark_social_circles.py --env prod --iterations 5
  python backend/scripts/benchmark_social_circles.py --max-books 100 500
  python backend/scripts/benchmark_social_circles.py --concurrent 5 --iterations 50
  python backend/scripts/benchmark_social_circles.py -c 10 --iterations 100
  python backend/scripts/benchmark_social_circles.py --dry-run
  python backend/scripts/benchmark_social_circles.py --dry-run --concurrent 10
  python backend/scripts/benchmark_social_circles.py --env prod --yes-i-mean-production
        """,
    )
    parser.add_argument(
        "--env",
        type=str,
        choices=["staging", "prod"],
        default="staging",
        help="Environment to test against (default: staging)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations per max_books value (default: 10)",
    )
    parser.add_argument(
        "--max-books",
        type=int,
        nargs="+",
        dest="max_books",
        help=f"max_books values to test (default: {DEFAULT_MAX_BOOKS_VALUES})",
    )
    parser.add_argument(
        "--concurrent",
        "-c",
        type=int,
        default=1,
        dest="concurrent",
        help="Number of concurrent requests (default: 1 = sequential)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path for JSON results (default: stdout)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print benchmark configuration and exit without making requests",
    )
    parser.add_argument(
        "--yes-i-mean-production",
        action="store_true",
        dest="yes_production",
        help="Skip the production safety confirmation prompt",
    )

    args = parser.parse_args()

    # Validate concurrency
    if args.concurrent < 1:
        parser.error("--concurrent must be at least 1")
    if args.concurrent > 100:
        print(
            f"Warning: --concurrent {args.concurrent} exceeds httpx default pool size (100). "
            "Capping at 100.",
            file=sys.stderr,
        )
        args.concurrent = 100

    # Production safety check
    base_url = ENVIRONMENTS[args.env]
    is_production = "api.bluemoxon.com" in base_url and "staging" not in base_url
    if is_production and not args.yes_production:
        print("=" * 60)
        print("WARNING: You are targeting PRODUCTION")
        print(f"  URL: {base_url}")
        print("=" * 60)
        if args.dry_run:
            print("Aborting: use --yes-i-mean-production to target production.")
            sys.exit(1)
        try:
            answer = input("Type 'yes' to continue, anything else to abort: ")
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)
        if answer.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(1)

    # Dry-run: print configuration and exit
    max_books_values = args.max_books if args.max_books else DEFAULT_MAX_BOOKS_VALUES
    mode_label = f"concurrent (x{args.concurrent})" if args.concurrent > 1 else "sequential"
    if args.dry_run:
        print("DRY RUN - No requests will be made")
        print("-" * 60)
        print(f"Environment:   {args.env}")
        print(f"Base URL:      {base_url}")
        print(f"Endpoint:      {ENDPOINT_PATH}")
        print(f"Mode:          {mode_label}")
        if args.concurrent > 1:
            stagger_ms = CONCURRENT_STAGGER_DELAY * 1000
            print(f"Stagger delay: {stagger_ms:.0f}ms between launches")
        print(f"Iterations:    {args.iterations}")
        print(f"max_books:     {max_books_values}")
        total_requests = args.iterations * len(max_books_values)
        print(f"Total requests:{total_requests}")
        if args.output:
            print(f"Output file:   {args.output}")
        print("-" * 60)
        sys.exit(0)

    # Run benchmarks
    results = asyncio.run(main_async(args))

    # Output results
    output = {
        "benchmark": "social_circles",
        "environment": args.env,
        "base_url": ENVIRONMENTS[args.env],
        "results": results,
    }

    json_output = json.dumps(output, indent=2)

    if args.output:
        Path(args.output).write_text(json_output)
        print(f"\nResults written to {args.output}")
    else:
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS (JSON)")
        print("=" * 60)
        print(json_output)


if __name__ == "__main__":
    main()
