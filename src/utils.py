"""Utility functions for logo similarity project."""
import logging
from urllib.parse import urljoin, urlparse
from typing import Optional

def setup_logging(level=logging.INFO):
    """Configure logging for the application."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logo_similarity.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def normalize_url(url: str, base_url: str) -> Optional[str]:
    """
    Normalize a URL by resolving relative paths.
    
    Args:
        url: The URL to normalize
        base_url: The base URL for resolving relative paths
        
    Returns:
        Normalized absolute URL or None if invalid
    """
    if not url:
        return None
    
    # Handle protocol-relative URLs
    if url.startswith('//'):
        parsed_base = urlparse(base_url)
        return f"{parsed_base.scheme}:{url}"
    
    # Handle absolute URLs
    if url.startswith('http://') or url.startswith('https://'):
        return url
    
    # Handle relative URLs
    return urljoin(base_url, url)

def is_valid_image_url(url: str) -> bool:
    """
    Check if a URL appears to be a valid image URL.
    
    Args:
        url: The URL to validate
        
    Returns:
        True if URL appears to be for an image
    """
    if not url:
        return False
    
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp'}
    parsed = urlparse(url.lower())
    
    for ext in valid_extensions:
        if parsed.path.endswith(ext):
            return True
    
    if any(keyword in parsed.path.lower() for keyword in ['logo', 'icon', 'favicon']):
        return True
    
    return False

def get_domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc or parsed.path
