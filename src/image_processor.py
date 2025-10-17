"""Image processing and hashing module."""
import io
import logging
from typing import Optional, Dict
from PIL import Image
import imagehash
import aiohttp
from src.config import Config

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Process and hash logo images."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Setup async context."""
        timeout = aiohttp.ClientTimeout(total=self.config.TIMEOUT)
        connector = aiohttp.TCPConnector(
            limit=self.config.MAX_CONCURRENT,
            limit_per_host=self.config.MAX_CONCURRENT,
            enable_cleanup_closed=True
        )
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup async context."""
        if self.session:
            await self.session.close()
    
    async def download_image(self, url: str) -> Optional[Image.Image]:
        """Download and load an image from URL."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                image_data = await response.read()
                img = Image.open(io.BytesIO(image_data))
                if not self._validate_image(img):
                    return None
                return img
        except Exception as e:
            logger.debug(f"Failed to download image from {url}: {e}")
            return None
    
    def _validate_image(self, img: Image.Image) -> bool:
        """Validate image meets requirements."""
        width, height = img.size
        if width < self.config.MIN_IMAGE_SIZE or height < self.config.MIN_IMAGE_SIZE:
            return False
        return True
    
    def normalize_image(self, img: Image.Image) -> Image.Image:
        """Normalize image for comparison."""
        if img.mode not in ['RGB', 'L', 'RGBA']:
            img = img.convert('RGB')

        if img.mode == 'P':
            img = img.convert('RGBA').convert('RGB')
        img = img.resize((self.config.NORMALIZE_SIZE, self.config.NORMALIZE_SIZE), Image.Resampling.LANCZOS)
        return img
    
    def compute_hashes(self, img: Image.Image) -> Dict[str, str]:
        """Compute multiple perceptual hashes for an image."""
        normalized = self.normalize_image(img)
        return {
            'phash': str(imagehash.phash(normalized)),
            'dhash': str(imagehash.dhash(normalized)),
            'ahash': str(imagehash.average_hash(normalized)),
            'whash': str(imagehash.whash(normalized)),
        }
    
    async def process_logo(self, url: str) -> Optional[Dict]:
        """Download and process a logo image."""
        img = await self.download_image(url)
        if not img:
            return None
        try:
            hashes = self.compute_hashes(img)
            return {
                'url': url,
                'hashes': hashes,
                'size': img.size,
                'format': img.format,
            }
        except Exception as e:
            logger.error(f"Failed to process image from {url}: {e}")
            return None
