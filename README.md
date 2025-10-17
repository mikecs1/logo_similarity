# logo_similarity

Logo similarity between companies without ML — a lightweight pipeline to extract logos from domains, compute perceptual image hashes, and cluster visually-similar logos.

This repository provides a full pipeline that:
- loads a list of domains (Parquet),
- extracts logo / favicon URLs from each site (multiple extraction strategies),
- downloads and normalizes images,
- computes perceptual hashes (pHash / dHash / aHash / wHash),
- groups similar logos into clusters,
- and writes human-friendly outputs (JSON, CSV, statistics).

This project is designed to be pragmatic and robust (no heavy ML models) and to run on a developer machine or a small VM.

---

Table of contents
- Features
- Quickstart
- Requirements
- Configuration
- CLI / Usage
- Output files
- Tuning & performance tips
- Windows notes & common issues
- Troubleshooting
- Contributing
- License

---

Features
- Multiple logo extraction strategies:
  - parse HTML (<link>, <meta>, <img>),
  - try common logo paths (/logo.png, /logo.svg, etc.),
  - fallback to /favicon.ico.
- Perceptual image hashing using multiple hash types for robust comparisons.
- Simple clustering based on hash distances.
- Progress bars and logs for real-time monitoring.
- Configurable batching and concurrency for safe runs on different machines.
- Outputs: clusters.json, clusters.csv, statistics.json.

---

Quickstart (local)
1. Create & activate a virtualenv (recommended)
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate

2. Install dependencies
   pip install -r requirements.txt

3. Prepare an input Parquet file
   - The pipeline expects a Parquet file with a `domain` column. Example:
     - logos.snappy.parquet
   - To create a small test file from a larger Parquet:
     python - <<'PY'
     import pandas as pd
     df = pd.read_parquet('logos.snappy.parquet')
     df.head(50).to_parquet('logos.small.parquet')
     PY

4. Run the pipeline (example)
   py main.py --input logos.small.parquet --batch-size 10 --max-concurrent 10 --output ./output

   Notes:
   - `py` is used in examples on Windows; you can use `python` on all platforms.
   - The run will log progress and write results to the output directory (see `--output` or `src/config.py`).

---

Requirements
- Python 3.8+ (tested with 3.11/3.12/3.13)
- Packages: see `requirements.txt` (pandas, pyarrow, aiohttp, beautifulsoup4, lxml, Pillow, imagehash, networkx, tqdm, etc.)

Install:
pip install -r requirements.txt

---

Configuration
Primary settings live in `src/config.py`. Key settings:
- TIMEOUT — per-request timeout (seconds)
- MAX_RETRIES — retry count for network requests
- RETRY_DELAY — delay between retries
- BATCH_SIZE — number of domains per extraction batch
- MAX_CONCURRENT — maximum concurrent HTTP requests
- HASH_CHUNK_SIZE — how many image-hash tasks to schedule at once
- OUTPUT_DIR — where output files are written

Modify `src/config.py` or override via CLI flags at runtime (see CLI below).

---

CLI / Usage
Run `main.py` with optional flags:
- --input: path to input Parquet (default: logos.snappy.parquet)
- --batch-size: override BATCH_SIZE (int)
- --max-concurrent: override MAX_CONCURRENT (int)
- --hash-chunk-size: override HASH_CHUNK_SIZE (int)
- --output: override OUTPUT_DIR (path)

Example:
py main.py --input logos.small.parquet --batch-size 20 --max-concurrent 10 --output ./output

---

Output files
After a successful run the pipeline writes these files to the output folder:
- clusters.json — array of clusters { cluster_id, size, domains[...] }
- clusters.csv — per-domain mapping: cluster_id, domain, logo_url, cluster_size
- statistics.json — run statistics (total_domains, logos_extracted, logos_processed, ...)

Files are written at the end of the run (after extraction, hashing and clustering).

---

Tuning & performance tips
- Batch size:
  - Larger batch sizes reduce total batches but increase per-batch work.
  - Typical values: 50–150. On small machines use lower values (20–50).
- Concurrency:
  - MAX_CONCURRENT controls simultaneous HTTP connections.
  - On Windows use conservative values: 10–30.
- Timeouts & retries:
  - Use TIMEOUT = 6–10s and MAX_RETRIES = 0–1 for faster failover on slow or blocking sites.
- Hash chunking:
  - HASH_CHUNK_SIZE prevents scheduling too many image tasks at once (helpful on Windows).
- Network:
  - Use a reliable network. If you run from behind corporate proxies or firewalls, configure them or run from a different network.

---

Windows notes & common issues
- You may see repeated asyncio Proactor callback errors like:
  OSError: [WinError 10022] An invalid argument was supplied
  These are typically non-fatal logs caused by remote connection resets and the Windows Proactor event loop. They can be reduced by:
  - lowering MAX_CONCURRENT
  - reducing TIMEOUT and MAX_RETRIES
  - using a TCPConnector with limited connections
- Do NOT switch to the Selector loop on Windows unless you also reduce concurrency to avoid select() file descriptor limits.
- If log spam is too noisy during debugging, temporarily silence asyncio logging in `main.py`:
  logging.getLogger('asyncio').setLevel(logging.CRITICAL)

---

Troubleshooting
- No output files:
  - Confirm the run completed and you saw the "Writing outputs to ..." log line.
  - Confirm `OUTPUT_DIR` path (default `./output`) and permissions.
  - Search the workspace for clusters.json: `Get-ChildItem -Recurse -Filter clusters.json` (PowerShell) or `find . -name clusters.json` (Linux/macOS).
- Very slow runs:
  - Increase BATCH_SIZE to reduce number of batches (but keep concurrency safe).
  - Increase MAX_CONCURRENT only if your OS / network can handle it.
  - Confirm TIMEOUT and MAX_RETRIES are reasonable.
- Too many socket errors (Windows):
  - Reduce MAX_CONCURRENT and batch-size. Use HASH_CHUNK_SIZE to limit scheduled image tasks.
- Parquet read/write errors:
  - Ensure `pyarrow` is installed and compatible with your pandas version.

---

Development & tests
- The repo is organized into `src/` modules. You can run `main.py` as the entry-point.
- To test changes quickly, create a very small input Parquet (10–50 domains) and run with small batch-size and concurrency:
  py main.py --input logos.small.parquet --batch-size 5 --max-concurrent 5 --output ./output-test

---

Contributing
- Contributions, bug reports and suggestions are welcome.
- Open issues describing the problem, logs and steps to reproduce.
- For code changes, please open a pull request with a clear description and small, focused changes.

---

License
- Please add the appropriate license file to the repo (LICENSE). If you’d like a suggestion, use MIT or Apache-2.0.

---

Contact / support
- If you hit a bug: open an issue and include:
  - command run, full console logs (or tail of the log), Python version, OS, and small reproduction dataset if possible.
- For urgent help paste the last 50 lines of the console log and I can help debug.

---

Thanks for using logo_similarity — if you want I can:
- add a small example dataset and a ready-to-run demo script, or
- create a minimal CI job to run basic lints / tests on PRs.
