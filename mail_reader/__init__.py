"""
Mail Reader - A tool for reading and analyzing emails
"""

from .core.email_reader import EmailReader
from .core.email_processor import EmailProcessor
from .utils.email_parser import EmailParser
from .utils.ad_detector import AdvertisementDetector
from .utils.stats_manager import StatsManager

__version__ = '0.1.0' 