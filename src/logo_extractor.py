"""Logo extraction module with multiple fallback strategies."""
import aiohttp
import asyncio
import logging
import warnings
from typing import Optional, Dict, List
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from src.config import Config
from src.utils import normalize_url, is_valid_image_url
import random

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logger = logging.getLogger(__name__)

class LogoExtractor:
    """Extract logos from websites using multiple strategies."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Setup async context."""
        timeout = aiohttp.ClientTimeout(total=self.config.TIMEOUT)
        connector = aiohttp.TCPConnector(
            limit=self.config.MAX_CONCURRENT,           # total connections cap
            limit_per_host=self.config.MAX_CONCURRENT,  # keep simple cap per host too
            enable_cleanup_closed=True
        )
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup async context."""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with random user agent."""
        return {
            'User-Agent': random.choice(self.config.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    async def extract_logo_url(self, domain: str) -> Optional[str]:
        """Extract logo URL from a domain using multiple strategies."""
        base_url = f"https://{domain}"
        try:
            # Parse HTML for logo
            logo_url = await self._extract_from_html(base_url)
            if logo_url:
                return logo_url
            
            logo_url = await self._try_common_paths(base_url)
            if logo_url:
                return logo_url
            
            # Fallback to favicon
            return f"{base_url}/favicon.ico"
        except Exception as e:
            logger.warning(f"Failed to extract logo from {domain}: {e}")
            return f"{base_url}/favicon.ico"
    
    async def _extract_from_html(self, base_url: str) -> Optional[str]:
        """Extract logo from HTML parsing."""
        try:
            async with self.session.get(base_url, headers=self._get_headers()) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                try:
                    soup = BeautifulSoup(html, 'lxml')
                except Exception:
                    soup = BeautifulSoup(html, 'html.parser')
                
                # <link> rel icons
                for rel in ['icon', 'shortcut icon', 'apple-touch-icon', 'apple-touch-icon-precomposed']:
                    link = soup.find('link', rel=lambda x: x and rel in x.lower())
                    if link and link.get('href'):
                        url = normalize_url(link['href'], base_url)
                        if is_valid_image_url(url):
                            return url
                
                # meta image
                for prop in ['og:image', 'twitter:image', 'twitter:image:src']:
                    meta = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
                    if meta and meta.get('content'):
                        url = normalize_url(meta['content'], base_url)
                        if is_valid_image_url(url):
                            return url
                
                # <img> with logo hints
                for img in soup.find_all('img'):
                    alt = (img.get('alt') or '').lower()
                    if any(k in alt for k in ['logo', 'brand']):
                        url = normalize_url(img.get('src'), base_url)
                        if is_valid_image_url(url):
                            return url
                    classes = ' '.join(img.get('class', [])).lower()
                    id_attr = (img.get('id') or '').lower()
                    if any(k in classes + id_attr for k in ['logo', 'brand', 'header-logo', 'site-logo']):
                        url = normalize_url(img.get('src'), base_url)
                        if is_valid_image_url(url):
                            return url
                return None
        except Exception as e:
            logger.debug(f"HTML parsing failed for {base_url}: {e}")
            return None
    
    async def _try_common_paths(self, base_url: str) -> Optional[str]:
        """Try common logo paths."""
        common_paths = [
            '/logo.png', '/logo.svg',
            '/assets/logo.png', '/assets/logo.svg',
            '/images/logo.png', '/img/logo.png',
            '/static/logo.png', '/static/images/logo.png',
            '/wp-content/uploads/logo.png',
        ]
        for path in common_paths:
            url = f"{base_url}{path}"
            try:
                async with self.session.head(url, headers=self._get_headers(), allow_redirects=True) as response:
                    if response.status == 200:
                        return url
            except Exception:
                continue
        return None
    
    async def extract_batch(self, domains: List[str]) -> Dict[str, Optional[str]]:
        """Extract logos from multiple domains concurrently."""
        # bound concurrency explicitly
        sem = asyncio.Semaphore(self.config.MAX_CONCURRENT)

        async def worker(d: str):
            async with sem:
                return await self.extract_logo_url(d)

        tasks = [worker(domain) for domain in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        output: Dict[str, Optional[str]] = {}
        for domain, result in zip(domains, results):
            if isinstance(result, Exception):
                logger.error(f"Error extracting logo from {domain}: {result}")
                output[domain] = None
            else:
                output[domain] = result
        return output
