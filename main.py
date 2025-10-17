"""Main entry point for logo similarity clustering with real-time progress and bounded concurrency."""

import asyncio
import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import Config
from src.logo_extractor import LogoExtractor
from src.image_processor import ImageProcessor
from src.clusterer import Clusterer
from src.utils import setup_logging

from tqdm import tqdm  # progress bars

import logging
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

setup_logging()
logger = logging.getLogger("logo-similarity")

class LogoSimilarityPipeline:
    """Main pipeline for logo extraction and clustering."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.config.ensure_dirs()
        self.stats = {
            'total_domains': 0,
            'logos_extracted': 0,
            'logos_processed': 0,
        }
    
    async def extract_all_logos(self, domains: List[str]) -> Dict[str, str]:
        """Extract logo URLs from all domains with per-batch progress."""
        logger.info(f"Extracting logos from {len(domains)} domains...")
        logo_urls: Dict[str, str] = {}
        total_batches = (len(domains) + self.config.BATCH_SIZE - 1) // self.config.BATCH_SIZE

        async with LogoExtractor(self.config) as extractor:
            with tqdm(total=total_batches, desc="Extracting (batches)", unit="batch") as pbar:
                for i in range(0, len(domains), self.config.BATCH_SIZE):
                    batch = domains[i:i + self.config.BATCH_SIZE]
                    batch_num = i // self.config.BATCH_SIZE + 1
                    logger.info(f"Processing batch {batch_num}/{total_batches}")
                    batch_results = await extractor.extract_batch(batch)
                    logo_urls.update(batch_results)

                    self.stats['logos_extracted'] = sum(1 for url in logo_urls.values() if url)
                    pbar.set_postfix(extracted=self.stats['logos_extracted'])
                    pbar.update(1)
                    await asyncio.sleep(0.2)
        
        logger.info(f"Extracted {self.stats['logos_extracted']}/{len(domains)} logos "
                    f"({(self.stats['logos_extracted']/len(domains)*100 if domains else 0):.1f}%)")
        return logo_urls
    
    async def process_all_images(self, logo_urls: Dict[str, str]) -> Dict[str, Dict]:
        """Process all logo images and compute hashes with bounded concurrency and chunking."""
        logger.info(f"Processing {len(logo_urls)} logo images...")
        logo_data: Dict[str, Dict] = {}
        items: List[Tuple[str, str]] = [(d, u) for d, u in logo_urls.items() if u]
        sem = asyncio.Semaphore(self.config.MAX_CONCURRENT)
        chunk_size = getattr(self.config, "HASH_CHUNK_SIZE", 300)

        async with ImageProcessor(self.config) as processor:
            async def worker(domain: str, url: str):
                async with sem:
                    try:
                        data = await processor.process_logo(url)
                        return domain, data
                    except Exception as e:
                        logger.debug(f"Failed to process {domain}: {e}")
                        return domain, None

            processed = 0
            for j in range(0, len(items), chunk_size):
                chunk = items[j:j + chunk_size]
                tasks = [worker(d, u) for d, u in chunk]
                for coro in tqdm(asyncio.as_completed(tasks), total=len(chunk), desc="Hashing (images)", unit="img"):
                    domain, data = await coro
                    if data:
                        logo_data[domain] = data
                        processed += 1

        self.stats['logos_processed'] = processed
        logger.info(f"Successfully processed {processed}/{len(items)} logos "
                    f"({(processed/len(items)*100 if items else 0):.1f}%)")
        return logo_data
    
    def cluster_logos(self, logo_data: Dict[str, Dict]):
        """Cluster logos by similarity."""
        logger.info("Clustering logos by similarity...")
        clusterer = Clusterer(self.config)
        clusters = clusterer.cluster_by_similarity(logo_data)
        logger.info(f"Found {len(clusters)} clusters")
        return clusters
    
    def save_results(self, clusters, logo_data: Dict):
        """Save clustering results to files."""
        output_dir = Path(self.config.OUTPUT_DIR)
        output_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"Writing outputs to {output_dir.resolve()}")

        clusters_json = [
            {'cluster_id': i, 'size': len(cluster), 'domains': list(cluster)}
            for i, cluster in enumerate(clusters)
        ]
        with open(output_dir / 'clusters.json', 'w', encoding='utf-8') as f:
            json.dump(clusters_json, f, indent=2)
        
        rows = []
        for i, cluster in enumerate(clusters):
            for domain in cluster:
                rows.append({
                    'cluster_id': i,
                    'domain': domain,
                    'logo_url': logo_data.get(domain, {}).get('url', ''),
                    'cluster_size': len(cluster)
                })
        pd.DataFrame(rows).to_csv(output_dir / 'clusters.csv', index=False)
        
        with open(output_dir / 'statistics.json', 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2)
        
        logger.info(f"- clusters.json: {len(clusters)} clusters")
        logger.info(f"- clusters.csv: {len(rows)} domain-cluster mappings")
    
    async def run(self, input_file: str):
        logger.info("Logo Similarity Clustering Pipeline")
        logger.info("="*59)
        logger.info(f"Loading domains from {input_file}...")
        df = pd.read_parquet(input_file)
        domains = df['domain'].tolist()
        self.stats['total_domains'] = len(domains)
        logger.info(f"Loaded {len(domains)} domains")
        logo_urls = await self.extract_all_logos(domains)
        logo_data = await self.process_all_images(logo_urls)
        clusters = self.cluster_logos(logo_data)
        self.save_results(clusters, logo_data)
        logger.info("="*59)
        logger.info("Pipeline Complete!")
        logger.info(f"Total domains: {self.stats['total_domains']}")
        logger.info(f"Logos extracted: {self.stats['logos_extracted']}")
        logger.info(f"Logos processed: {self.stats['logos_processed']}")
        logger.info(f"Clusters found: {len(clusters)}")
        logger.info("="*59)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Logo Similarity Clustering')
    parser.add_argument('--input', default='logos.snappy.parquet', help='Input parquet file')
    parser.add_argument('--batch-size', type=int, default=None, help='Batch size (overrides config)')
    parser.add_argument('--max-concurrent', type=int, default=None, help='Max concurrent requests (overrides config)')
    parser.add_argument('--hash-chunk-size', type=int, default=None, help='Hash scheduling chunk size (overrides config)')
    parser.add_argument('--output', type=str, default=None, help='Output directory (overrides config)')
    args = parser.parse_args()

    config = Config()
    if args.batch_size is not None:
        config.BATCH_SIZE = args.batch_size
    if args.max_concurrent is not None:
        config.MAX_CONCURRENT = args.max_concurrent
    if args.hash_chunk_size is not None:
        config.HASH_CHUNK_SIZE = args.hash_chunk_size
    if args.output is not None:
        config.OUTPUT_DIR = args.output

    pipeline = LogoSimilarityPipeline(config)
    asyncio.run(pipeline.run(args.input))

if __name__ == '__main__':
    main()