"""Clustering module using graph-based approach without ML algorithms."""
import logging
from typing import Dict, List, Set
import networkx as nx
import imagehash
from src.config import Config

logger = logging.getLogger(__name__)

class Clusterer:
    """Cluster logos based on perceptual hash similarity using graph theory."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
    
    def _compute_hash_distance(self, hash1: str, hash2: str) -> int:
        """Compute Hamming distance between two perceptual hashes."""
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except Exception as e:
            logger.error(f"Error computing hash distance: {e}")
            return 999
    
    def cluster_by_similarity(self, logo_data: Dict[str, Dict]) -> List[Set[str]]:
        """Cluster domains by logo similarity using graph-based approach."""
        G = nx.Graph()
        
        valid_domains = [
            domain for domain, data in logo_data.items()
            if data and 'hashes' in data and data['hashes'].get('phash')
        ]
        
        logger.info(f"Clustering {len(valid_domains)} domains with valid logo hashes")
        
        for domain in valid_domains:
            G.add_node(domain)
        
        for i, domain1 in enumerate(valid_domains):
            hash1 = logo_data[domain1]['hashes']['phash']
            
            for domain2 in valid_domains[i+1:]:
                hash2 = logo_data[domain2]['hashes']['phash']
                distance = self._compute_hash_distance(hash1, hash2)
                
                if distance <= self.config.NEAR_DUPLICATE_THRESHOLD:
                    G.add_edge(domain1, domain2, distance=distance)
        
        clusters = list(nx.connected_components(G))
        logger.info(f"Found {len(clusters)} clusters")
        
        return clusters
