import os
import json
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="P. brassicae Genomics API")

# Allow web frontends to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.expanduser("~/dev/blast_db/pb_genomes_db")

# Mock database join: field_samples -> sample_pathotype_assignments
ISOLATE_METADATA = {
    "S16":  {"isolate_id": "P2A_isolateS16",  "county": "Sturgeon County",  "year": 2016, "ccd_pathotype": "2A", "williams": "Pathotype 2"},
    "ST40": {"isolate_id": "P3A_isolateST40", "county": "Camrose County",   "year": 2017, "ccd_pathotype": "3A", "williams": "Pathotype 3"},
    "SC19": {"isolate_id": "P3H_isolateSC19", "county": "Sturgeon County",  "year": 2019, "ccd_pathotype": "3H", "williams": "Pathotype 3"},
    "SS23": {"isolate_id": "P4A_isolateSS23", "county": "Strathcona County","year": 2018, "ccd_pathotype": "4A", "williams": "Pathotype 4"},
    "ST23": {"isolate_id": "P5X_isolateST23", "county": "Leduc County",     "year": 2018, "ccd_pathotype": "5X", "williams": "Pathotype 5"},
    "SW46": {"isolate_id": "P6B_isolateSW46", "county": "Westlock County",  "year": 2020, "ccd_pathotype": "6B", "williams": "Pathotype 6"},
    "SA13": {"isolate_id": "P6C_isolateSA13", "county": "Athabasca County", "year": 2015, "ccd_pathotype": "6C", "williams": "Pathotype 6"},
}

# Pydantic model for the BLAST request 
class BlastRequest(BaseModel):
    sequence: str = Field(..., min_length=15, description="DNA sequence to query")
    program: Optional[str] = Field(default="auto", description="auto, megablast, or blastn")
    evalue: float = Field(default=0.001, ge=0.0, description="Expectation value threshold")
    max_hits: int = Field(default=10, ge=1, le=50, description="Max alignments to return")

# get_metadata_for_hit function to extract isolate code and resolve field metadata
def get_metadata_for_hit(header_id: str) -> dict:
    """Extract isolate code and resolve field metadata."""
    isolate_code = header_id.split("#")[0]
    return ISOLATE_METADATA.get(
        isolate_code,
        {"isolate_id": "Unknown", "county": "Unknown", "year": None, "ccd_pathotype": "Unknown", "williams": "Unknown"}
    )

# post endpoint for BLAST search
@app.post("/api/v1/genomics/blast")
async def run_blast_search(query: BlastRequest):
    # 1. Clean incoming sequence
    clean_seq = "".join(query.sequence.split()).upper() # remove the whitespace and convert to uppercase

    # 2. Smart algorithm selection with expert override
    # if the user specifies a program, use it; otherwise, choose based on length (<=50 bp: blastn, >50 bp: megablast)
    if query.program in ["megablast", "blastn"]:
        task = query.program
    else:
        task = "blastn" if len(clean_seq) <= 50 else "megablast"

    # 3. Assemble command 
    cmd = [
        "blastn", # Using blastn for both tasks; megablast is a task within blastn
        "-db", DB_PATH,
        "-query", "-", # read query from STDIN pipe
        "-task", task, # task selection based on length or user override
        "-dust", "no", # Disable low-complexity filtering for short sequences
        "-outfmt", "15", # JSON output
        "-evalue", str(query.evalue), # Set e-value threshold
        "-max_target_seqs", str(query.max_hits), # Limit number of hits returned
        "-num_threads", "2" 
    ]

    # 4. Execute asynchronously with STDIN pipe
    # linux creates the pipe for us, so we can stream the query directly into BLAST's memory
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE, # pipe for streaming the query
        stdout=asyncio.subprocess.PIPE, # pipe for capturing output
        stderr=asyncio.subprocess.PIPE # pipe for capturing errors
    )

    # 5. Stream the FASTA query straight into BLAST's memory
    fasta_payload = f">web_query\n{clean_seq}\n".encode() # encode to bytes for stdin in asyncio
    stdout, stderr = await proc.communicate(input=fasta_payload) # python pushes the sequence bytes into the pipe (stdin) and waits for BLAST to finish
    # ^^ python reads the output from stdout and stderr pipes after BLAST completes

    # Check for errors in BLAST execution
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"BLAST CLI error: {stderr.decode()}")

    # 6. Parse JSON and link metadata
    blast_data = json.loads(stdout.decode())
    hits_list = []

    try:
        report = blast_data["BlastOutput2"]
        report = report[0]["report"] if isinstance(report, list) else report["report"] # Handle both list and dict formats coming from different BLAST versions
        raw_hits = report["results"]["search"].get("hits", [])

        for hit in raw_hits:
            hit_id = hit["description"][0]["id"]
            hit_title = hit["description"][0].get("title", "")
            
            hits_list.append({
                "hit_id": hit_id,
                "hit_title": hit_title,
                "hsps": hit.get("hsps", []),
                "field_metadata": get_metadata_for_hit(hit_id)
            })
    except (KeyError, IndexError, TypeError) as e:
        hits_list = []

    return {
        "status": "success",
        "query_info": {
            "query_length": len(clean_seq),
            "task_used": task,
            "evalue_cutoff": query.evalue,
            "total_hits": len(hits_list)
        },
        "hits": hits_list
    }