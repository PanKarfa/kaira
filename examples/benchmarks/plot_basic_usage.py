"""
==========================
Basic Benchmark Usage
==========================

This example demonstrates the basic usage of the Kaira benchmarking system,
including running individual benchmarks, creating and running benchmark suites,
and saving/analyzing results.

The Kaira benchmarking system provides tools for:

* Running individual benchmarks with different configurations
* Creating and executing benchmark suites
* Analyzing and visualizing benchmark results
* Comparing performance across different algorithms and parameters
"""

# %%
# Setting up the Environment
# ---------------------------
# First, let's import the necessary modules and set up our environment.

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Import Kaira benchmarking components
from kaira.benchmarks import BenchmarkConfig, BenchmarkSuite, StandardRunner, create_benchmark

# Set random seed for reproducibility
np.random.seed(42)

# %%
# Running a BER Simulation Benchmark
# -----------------------------------
# Let's start with a basic BER (Bit Error Rate) simulation benchmark using BPSK modulation.


def run_ber_benchmark():
    """Run a BER simulation benchmark."""
    print("Running BER Simulation Benchmark...")

    # Create benchmark instance
    ber_benchmark = create_benchmark("ber_simulation", modulation="bpsk")

    # Configure benchmark
    config = BenchmarkConfig(name="ber_example", snr_range=list(range(-5, 11)), block_length=100000, verbose=True)

    # Run benchmark
    runner = StandardRunner(verbose=True)
    result = runner.run_benchmark(ber_benchmark, **config.to_dict())

    # Plot results
    plt.figure(figsize=(10, 6))
    plt.semilogy(result.metrics["snr_range"], result.metrics["ber_simulated"], "bo-", label="Simulated")
    plt.semilogy(result.metrics["snr_range"], result.metrics["ber_theoretical"], "r--", label="Theoretical")
    plt.xlabel("SNR (dB)")
    plt.ylabel("Bit Error Rate")
    plt.title("BPSK BER Performance")
    plt.legend()
    plt.grid(True)
    plt.show()

    print(f"Benchmark completed in {result.execution_time:.2f} seconds")
    print("RMSE between simulated and theoretical: {:.6f}".format(result.metrics["rmse"]))

    return result


# %%
# Running a Throughput Benchmark
# -------------------------------
# Next, let's run a throughput benchmark to measure data processing speeds.


def run_throughput_benchmark():
    """Run a throughput benchmark."""
    print("\nRunning Throughput Benchmark...")

    # Create benchmark instance
    throughput_benchmark = create_benchmark("throughput_test")

    # Configure benchmark - pass payload_sizes as runtime kwargs instead of config
    config = BenchmarkConfig(name="throughput_example", num_trials=5)

    # Run benchmark with payload_sizes as kwargs
    runner = StandardRunner(verbose=True)
    result = runner.run_benchmark(throughput_benchmark, payload_sizes=[1000, 10000, 100000], **config.to_dict())

    # Display results
    print("\nThroughput Results:")
    for size, stats in result.metrics["throughput_results"].items():
        print("  Payload size {}: {:.2f} ± {:.2f} bits/s".format(size, stats["mean"], stats["std"]))

    print("Peak throughput: {:.2f} bits/s".format(result.metrics["peak_throughput"]))

    return result


# %%
# Creating and Running Benchmark Suites
# --------------------------------------
# Benchmark suites allow you to run multiple related benchmarks together and
# analyze their collective performance.


def run_benchmark_suite():
    """Run a complete benchmark suite."""
    print("\nRunning Benchmark Suite...")

    # Create benchmark suite
    suite = BenchmarkSuite(name="Communication System Benchmarks", description="Comprehensive evaluation of communication system performance")

    # Add benchmarks to suite
    suite.add_benchmark(create_benchmark("channel_capacity", channel_type="awgn"))
    suite.add_benchmark(create_benchmark("ber_simulation", modulation="bpsk"))
    suite.add_benchmark(create_benchmark("throughput_test"))
    suite.add_benchmark(create_benchmark("latency_test"))

    # Configure and run suite - use block_length instead of num_bits
    config = BenchmarkConfig(name="suite_example", snr_range=[-5, 0, 5, 10], block_length=10000, verbose=True)

    runner = StandardRunner(verbose=True)
    runner.run_suite(suite, num_bits=10000, **config.to_dict())

    # Get summary
    summary = suite.get_summary()
    print("\nSuite Summary:")
    print("  Total benchmarks: {}".format(summary["total_benchmarks"]))
    print("  Successful: {}".format(summary["successful"]))
    print("  Failed: {}".format(summary["failed"]))
    print("  Total execution time: {:.2f}s".format(summary["total_execution_time"]))

    # Save results
    output_dir = Path("./benchmark_results")
    suite.save_results(output_dir)
    print("\nResults saved to:", output_dir)

    return suite


# %%
# Putting It All Together
# ------------------------
# Now let's run all the benchmark examples and display the results.

if __name__ == "__main__":
    # Run individual benchmarks
    print("Running BER Benchmark...")
    ber_result = run_ber_benchmark()

    print("\nRunning Throughput Benchmark...")
    throughput_result = run_throughput_benchmark()

    # Run benchmark suite
    print("\nRunning Benchmark Suite...")
    suite = run_benchmark_suite()

    print("\n" + "=" * 50)
    print("All benchmarking examples completed successfully!")
    print("=" * 50)

# %%
# Summary
# -------
# This example demonstrated the core features of the Kaira benchmarking system:
#
# 1. **Individual Benchmarks**: Running single benchmarks with specific configurations
# 2. **Throughput Testing**: Measuring data processing performance across different payload sizes
# 3. **Benchmark Suites**: Organizing and running multiple related benchmarks
# 4. **Result Management**: Saving and analyzing benchmark results
#
# The benchmarking system provides a flexible framework for evaluating communication
# system performance across different algorithms, configurations, and scenarios.
