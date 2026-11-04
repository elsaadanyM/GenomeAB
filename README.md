# Genome AB

A web-based research platform for *Plasmodiophora brassicae*, the pathogen that causes clubroot in canola. This platform brings the Plant Pathology Laboratory's pathotyping workflow and genomic data into one interface: pathotype classification, genome browsing, sequence search, in-silico PCR and pangenome exploration.

**Current goal:** a working local demo (pathotyping, genome browser, sequence search) before the customer meeting on November 13.

## Directory structure

```
GenomeAB/
├── backend/
│   ├── pathotyping/   # Pathotyping pipeline (ported from R to Python) + API
│   ├── search/        # Sequence search (SequenceServer / NCBI BLAST+)
│   ├── pcr/           # In-silico PCR (not started)
│   └── pangenome/     # Pangenome exploration (not started)
├── frontend/          # React app: pathotyping UI + embedded JBrowse and SequenceServer
└── docs/              # Documents and supporting notes
```

Each active folder gets its own README with setup and run instructions.

## Data

Customer data (FASTA, VCF, pangenome and Excel files) are **not stored in this repository**. Get it from the [customer's google drive](https://drive.google.com/drive/u/3/folders/1fE1K7ygIkBmGPvn8lA40f93Ljsf-_nQT) and place it in a local `data/` folder at the repo root or inside the folder you’re working in. Every `data/` folder is ignored by git.