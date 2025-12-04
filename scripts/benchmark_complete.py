#!/usr/bin/env python3
"""
Benchmark completo de optimizaciones
"""
import requests
import time
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style

init()

API_URL = "http://localhost:5000"

TEST_PAYLOAD = {
    "data": [
        "machine learning",
        "en",
        [
            ["1", "1", "Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed."]
        ]
    ],
    "threshold": 0.70,
    "use_faiss": True
}


def colored_print(text, color=Fore.WHITE):
    """Print con color"""
    print(f"{color}{text}{Style.RESET_ALL}")


def benchmark_endpoint(
    endpoint: str,
    payload: dict,
    num_requests: int = 100,
    concurrency: int = 10
):
    """Benchmark endpoint"""
    url = f"{API_URL}{endpoint}"
    
    colored_print(f"\n{'='*60}", Fore.CYAN)
    colored_print(f"🚀 Benchmarking: {endpoint}", Fore.CYAN)
    colored_print(f"   Requests: {num_requests}", Fore.CYAN)
    colored_print(f"   Concurrency: {concurrency}", Fore.CYAN)
    colored_print(f"{'='*60}", Fore.CYAN)
    
    def single_request():
        start = time.perf_counter()
        try:
            response = requests.post(url, json=payload, timeout=30)
            elapsed = time.perf_counter() - start
            return {
                'success': response.status_code == 200,
                'elapsed': elapsed,
                'status': response.status_code,
                'size': len(response.content)
            }
        except Exception as e:
            return {
                'success': False,
                'elapsed': 0,
                'error': str(e)
            }
    
    # Warmup
    colored_print("🔥 Warming up...", Fore.YELLOW)
    for _ in range(5):
        single_request()
    
    # Benchmark
    colored_print("⏱️  Running benchmark...", Fore.YELLOW)
    start_total = time.perf_counter()
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(single_request) for _ in range(num_requests)]
        results = [f.result() for f in as_completed(futures)]
    
    total_time = time.perf_counter() - start_total
    
    # Análisis
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    times = [r['elapsed'] for r in successful]
    
    if times:
        colored_print("\n📊 RESULTS:", Fore.GREEN)
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Success rate: {len(successful)/num_requests*100:.1f}%")
        print(f"   Throughput: {num_requests/total_time:.1f} req/s")
        print()
        colored_print("   Response times:", Fore.YELLOW)
        print(f"   Mean: {statistics.mean(times)*1000:.0f}ms")
        print(f"   Median: {statistics.median(times)*1000:.0f}ms")
        print(f"   P95: {sorted(times)[int(len(times)*0.95)]*1000:.0f}ms")
        print(f"   P99: {sorted(times)[int(len(times)*0.99)]*1000:.0f}ms")
        print(f"   Min: {min(times)*1000:.0f}ms")
        print(f"   Max: {max(times)*1000:.0f}ms")
        print(f"   Std Dev: {statistics.stdev(times)*1000:.0f}ms")
        
        if successful:
            avg_size = statistics.mean([r['size'] for r in successful])
            print(f"\n   Avg response size: {avg_size/1024:.1f} KB")
    
    if failed:
        colored_print(f"\n❌ Failed requests: {len(failed)}", Fore.RED)
    
    return {
        'throughput': num_requests/total_time,
        'mean_latency': statistics.mean(times) if times else 0,
        'p95_latency': sorted(times)[int(len(times)*0.95)] if times else 0,
        'success_rate': len(successful)/num_requests*100
    }


def test_health():
    """Test health endpoint"""
    colored_print("\n🏥 Testing health endpoint...", Fore.CYAN)
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        if response.status_code == 200:
            colored_print("✅ Health check passed", Fore.GREEN)
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Redis: {data.get('redis')}")
            print(f"   FAISS papers: {data.get('faiss', {}).get('total_papers', 0)}")
            return True
        else:
            colored_print(f"❌ Health check failed: {response.status_code}", Fore.RED)
            return False
    except Exception as e:
        colored_print(f"❌ Health check error: {e}", Fore.RED)
        return False


def main():
    """Main benchmark"""
    colored_print("""
╔══════════════════════════════════════════════════════════════╗
║        XPLAGIAX SourceX - BENCHMARK COMPLETO                 ║
║                   Version 2.1.0                               ║
╚══════════════════════════════════════════════════════════════╝
    """, Fore.CYAN)
    
    # Health check
    if not test_health():
        colored_print("\n❌ Server not ready. Start the server first.", Fore.RED)
        sys.exit(1)
    
    # Benchmark similarity search
    results = benchmark_endpoint(
        "/api/similarity-search",
        TEST_PAYLOAD,
        num_requests=100,
        concurrency=10
    )
    
    # Resumen final
    colored_print(f"\n{'='*60}", Fore.CYAN)
    colored_print("📈 FINAL SUMMARY", Fore.GREEN)
    colored_print(f"{'='*60}", Fore.CYAN)
    print(f"Throughput: {results['throughput']:.1f} req/s")
    print(f"Mean latency: {results['mean_latency']*1000:.0f}ms")
    print(f"P95 latency: {results['p95_latency']*1000:.0f}ms")
    print(f"Success rate: {results['success_rate']:.1f}%")
    
    # Comparación con baseline
    BASELINE_THROUGHPUT = 45  # req/s antes
    BASELINE_LATENCY = 850  # ms antes
    
    throughput_improvement = (results['throughput'] / BASELINE_THROUGHPUT - 1) * 100
    latency_improvement = (1 - results['mean_latency']*1000 / BASELINE_LATENCY) * 100
    
    print(f"\n🚀 Improvements vs baseline:")
    print(f"   Throughput: {throughput_improvement:+.1f}%")
    print(f"   Latency: {latency_improvement:+.1f}%")
    
    colored_print(f"\n{'='*60}\n", Fore.CYAN)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        colored_print("\n\n⚠️ Benchmark interrupted", Fore.YELLOW)
        sys.exit(0)