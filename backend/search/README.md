# SEQUENCE SEARCH

**Status:** **Done** prototype for Nov 13 demo

## What it does
Allows users to search a DNA sequence against 7 *Plasmodiophora brassicae* (clubroot pathogen) customer reference genomes. It provides our custom NCBI BLAST+ CLI integration wrapped in FastAPI. 

Unlike standalone BLAST tools that only return raw sequence coordinates, our API bridges the "Phenotype-to-Genotype Gap" by parsing matching sequence headers (e.g., `SA13`, `SC19`) and returning field metadata (collection year, county of origin, and official CCD/Williams pathotype).

## Setup
### Requirements & Versions
* **Operating System:** Linux, macOS, or WSL2 (Ubuntu 22.04 / 24.04)
* **NCBI BLAST+ CLI:** v2.12.0+ (`sudo apt install ncbi-blast+`)
* **Docker:** Required for running the SequenceServer baseline
* **Python:** 3.10+ with `fastapi`, `uvicorn`, `pydantic`, and `matplotlib` (optional)

### Customer Data Placement
* Place the customer reference FASTA files in:
  `~/dev/sequenceserver_db/` (or `data/genomics/fasta/`)
* Compiled BLAST databases will reside in:
  `~/dev/blast_db/` (or `data/genomics/blast_db/`)

---

## How to run

### 1. Run SequenceServer (Baseline)
Spin up the SequenceServer Docker container mounting the FASTA files:
```bash
docker run -it --rm \
  -p 4567:4567 \
  -v ~/dev/sequenceserver_db:/db \
  wurmlab/sequenceserver
```
* **URL:** `http://localhost:4567`

### 2. Build the Unified BLAST Database
Combine the 7 assemblies into a single reference and compile the binary database index:
```bash
mkdir -p ~/dev/blast_db
cat ~/dev/sequenceserver_db/*.fa > ~/dev/blast_db/pb_all_genomes.fa

makeblastdb \
  -in ~/dev/blast_db/pb_all_genomes.fa \
  -dbtype nucl \
  -title "P_brassicae_7_Genomes" \
  -parse_seqids \
  -out ~/dev/blast_db/pb_genomes_db
```

### 3. Run the Performance Benchmark Script
Run the automated query-size vs. latency benchmark (generates `benchmark_results.png`):
```bash
cd ~/dev/blast_sim
python3 benchmark.py
```

### 4. Run the FastAPI Wrapper Service
Activate your virtual environment and start the web server:
```bash
cd ~/dev/blast_sim
source venv/bin/activate
uvicorn main:app --reload --port 8000
```
* **API Documentation & Swagger UI:** `http://localhost:8000/docs`

---

## Inputs and outputs

### Endpoint: `POST /api/v1/genomics/blast`

### Example Request
```json
{
  "sequence": "GCCACATTCGAAAACTGCACGAAGTCGGCGTTCGAGAGCTGATGCGCGACAAGGGCCTCTACCAGGTGCACGAGCTGCAGATGGGATTCCAGCGCCGGATTGGCCCGATCGAAGCCGTCTGGGTCGCTGATGAGCTTCTGGAAACGTAC",
  "program": "auto",
  "evalue": 0.001,
  "max_hits": 5
}
```

### Example Response
```json
{
  "status": "success",
  "query_info": {
    "query_length": 88,
    "task_used": "megablast",
    "evalue_cutoff": 0.001,
    "total_hits": 1
  },
  "hits": [
    {
      "hit_id": "SA13#1#ptg000002l",
      "hit_title": "",
      "hsps": [
        {
          "num": 1,
          "bit_score": 163.6,
          "score": 88,
          "evalue": 6.1e-40,
          "identity": 88,
          "query_from": 1,
          "query_to": 88,
          "hit_from": 1454421,
          "hit_to": 1454508,
          "hit_strand": "Plus",
          "align_len": 88,
          "gaps": 0
        }
      ],
      "field_metadata": {
        "isolate_id": "P6C_isolateSA13",
        "county": "Athabasca County",
        "year": 2015,
        "ccd_pathotype": "6C",
        "williams": "Pathotype 6"
      }
    }
  ]
}
```

---

## Open questions and notes

### Decisions Made
* **Smart Task Routing:** Queries $\le 50$ bp are automatically routed to `blastn` (sensitive word size $W=7\text{--}11$ for diagnostic PCR primers); queries $> 50$ bp are routed to `megablast` (word size $W=28$ for $40\times$ faster contig/gene matching).
* **In-Memory Zero-Disk IPC:** Queries are streamed directly to BLAST via an in-memory STDIN pipe (`-query -`), eliminating temporary file writes, disk I/O bottlenecks, and shell injection vulnerabilities.

### Known Limitations
* **Nucleotide Only for Demo:** Currently supports `blastn` / `megablast`. Protein searches (`blastp`, `blastx`) require GFF3 gene annotations to extract proteomes in Phase 2.
* **Unanchored Pathotypes:** Field pathotypes without a fully assembled reference genome (e.g., `8P`) do not have a dedicated FASTA entry and will align to the closest evolutionary reference genome.

### Open Questions for Customer / Lab

#### Search Parameters & Target Queries
1. **Advanced Options:** Will we be using any of the other parameters in SequenceServer (advanced options)?
2. **Search Preferences:** For BLAST, what are users searching for the most? Nucleotides (`blastn`) or translated proteins/effectors (`blastx` / `blastp`)?
3. **Mismatches:** What is the number of mismatches you would like to allow in BLAST or *in silico* PCR?
4. **Standard Primers:** Are there standard primer sets (*in silico*) or queries (BLAST) that are constantly used?

#### Genomic Assets, Effectors & Annotations
5. **Effectors & Transcripts:** Will we be using effectors and RNA transcriptions in SequenceServer? And will they be in FASTA format?
6. **VCF Baseline:** Which of the 7 reference FASTA genomes were the 45 customer VCF variant files aligned against?
7. **Gene Summary UI:** When users want to look for a gene, did you want a similar look to UniProt summaries with annotations and download links?
8. **ENCODE Visuals:** For ENCODE, did you want the simple searching feature where users can select (year, pathotype, etc.) or was it more for the visual aspect?

#### Metadata Linkage & Database Schema
9. **Reference Naming Link:** How do the reference file names or IDs relate to pathotyping? For example, is `P3H_isolateSC19.fa` related to pathotypes with CCD 3x or Williams 3?
10. **Field Translation Table:** Is there an official lookup table or column that maps our 7 sequenced isolates (`S16`, `ST40`, `SC19`, `SS23`, `ST23`, `SW46`, `SA13`) to their original `location-int-year` field sample codes?
11. **Canonical Isolate ID:** What is the canonical naming convention for `isolate_id` in the database (e.g., `P2A_isolateS16` vs. `isolateS16` vs. `S16`)?
12. **Metadata Fields:** Can we get a list of the exact metadata attributes that you would want attached to the isolates?
13. **Pre-Filtering:** Will people ever need to search by metadata (location, date, etc.) before running a sequence search, or is the general search sufficient? (e.g., searching only isolates collected after 2022).
14. **Location Privacy:** Should field sample coordinates on the public map be fuzzed to county/municipality centroids to protect producer privacy?

#### Data Governance, Downloads & Lifecycle
15. **Downloads:** Will people be able to download the raw FASTA files, or just view the matches after the query?
16. **Database Versioning:** Do we need versioning? (e.g., a researcher wants to replicate an exact search that was used in a published study, so they select database version 1.2).
17. **Update Frequency:** How often will new genomes or isolates be added to the server, if at all?