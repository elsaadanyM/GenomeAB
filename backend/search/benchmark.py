import os
import random
import subprocess
import tempfile
import time
import matplotlib.pyplot as plt

# Path to unified BLAST database
DB_PATH = os.path.expanduser("~/dev/blast_db/pb_genomes_db")

# test matrix covering the 5 biological scales
TEST_CASES_01 = [
    # (Label, Length in bp, BLAST Task)
    ("Diagnostic Primer", 25, "blastn"),        # Needs sensitive task for short length
    ("PCR Amplicon", 350, "megablast"),
    ("Average CDS Gene", 1500, "megablast"),
    ("Multi-Gene Scaffold", 25000, "megablast"),
    ("Full Contig Stress", 120000, "megablast") # 120 kb stress test
]

TEST_CASES_LOG_MB = [
    # (Label, Length in bp, BLAST Task)
    ("Short Query (megablast)", 50, "megablast"),
    ("S (megablast)", 100, "megablast"),
    ("Standard Gene", 1000, "megablast"),
    ("Standard Gene", 100000, "megablast"),
    ("Large Scaffold", 1000000, "megablast"),     # 1 Mb
    ("Half-Genome Stress", 10000000, "megablast") # 10 Mb (Heavy stress test)
]

TEST_CASES_LOG_BN = [
    # (Label, Length in bp, BLAST Task)
    ("Short Query (blastn)", 50, "blastn"),
    ("S (blastn)", 100, "blastn"),
    ("Standard Gene", 1000, "blastn"),
    ("Standard Gene", 100000, "blastn"),
    ("Large Scaffold", 1000000, "blastn"),     # 1 Mb
    ("Half-Genome Stress", 10000000, "blastn") # 10 Mb (Heavy stress test)
]

# fixed seed so every benchmark run tests the exact same sequence
random.seed(42)

def generate_dna_sequence(length: int) -> str:
    """Generates a pseudo-random DNA sequence of the specified length."""
    bases = ["A", "C", "G", "T"]
    return "".join(random.choices(bases, k=length))


def run_single_benchmark(label: str, length: int, task: str) -> dict:
    #  generate sequence
    sequence = generate_dna_sequence(length)
    
    #  write sequence to a temporary FASTA file
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".fa")
    temp_file.write(f">test\n{sequence}\n")
    temp_file.close()
    
    #  assemble the blastn command list
    cmd = [
        "blastn",
        "-db", DB_PATH,
        "-query", temp_file.name,
        "-task", task,
        "-outfmt", "6",
        "-num_threads", "2"
    ]
    
    #  measure time
    try: 
        start_time = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.perf_counter() - start_time
    finally:
        # clean up the temp file with os.remove()
        if (temp_file and os.path.exists(temp_file.name)):
            os.remove(temp_file.name)
    
    
    #  return the dictionary of results
    
    return {
    "label": label,
    "length": length,
    "task": task,
    "time_seconds": elapsed,
    "success": result.returncode == 0
    }

def plot_benchmark_results(results_mb, results_bn):
    """Plots the benchmark results using matplotlib."""
    length_mb = [int(r['length']) for r in results_mb]
    times_mb = [r['time_seconds'] for r in results_mb]
    
    length_bn = [int(r['length']) for r in results_bn]
    times_bn = [r['time_seconds'] for r in results_bn]

    plt.figure(figsize=(10, 6))
    plt.plot(length_mb, times_mb, marker='o', label='MEGABLAST')
    plt.plot(length_bn, times_bn, marker='s', label='BLASTN')
    plt.title("BLAST Benchmark Results")
    plt.xlabel("Query Length (bp)")
    plt.ylabel("Time (seconds)")
    plt.xscale('log')
    plt.grid(True, which="both", ls="--")
    plt.legend()
    plt.savefig("benchmark_results.png")

def main():
    print("\n--- Running Initial Test Cases ---\n")
    for label, length, task in TEST_CASES_01:
        result = run_single_benchmark(label, length, task)
        print(f"Benchmark: {result['label']}, Length: {result['length']} bp, Task: {result['task']}, Time: {result['time_seconds']:.4f} s, Success: {result['success']}")

    print("\n--- Running Additional Test Cases (MEGABLAST) ---\n")
    results_mb = []
    for label, length, task in TEST_CASES_LOG_MB:
            result = run_single_benchmark(label, length, task)
            results_mb.append(result)
            print(f"Benchmark: {result['label']}, Length: {result['length']} bp, Task: {result['task']}, Time: {result['time_seconds']:.4f} s, Success: {result['success']}")

    print("\n--- Running Additional Test Cases (BLASTN) ---\n")
    results_bn = []
    for label, length, task in TEST_CASES_LOG_BN:
            result = run_single_benchmark(label, length, task)
            results_bn.append(result)
            print(f"Benchmark: {result['label']}, Length: {result['length']} bp, Task: {result['task']}, Time: {result['time_seconds']:.4f} s, Success: {result['success']}")
    
    plot_benchmark_results(results_mb, results_bn)


if __name__ == "__main__":
    main()