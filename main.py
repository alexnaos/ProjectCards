"""main.py CLI для project-cards."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.frontmatter import parse_frontmatter, build_frontmatter, merge_frontmatter, frontmatter_to_yaml, read_card_file, write_card_file
from src.volume import iter_projects_with_volume, _count_files
from src.images import find_and_render_plans
from src.extractors import extract_text_from_file
from src.address import extract_address
from src.summarizer import summarize_text
