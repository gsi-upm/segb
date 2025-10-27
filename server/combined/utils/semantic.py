from typing import Optional
from pydantic import BaseModel
from rdflib import Graph
import json

import logging
import os

logger = logging.getLogger("segb.server.utils.semantic")

logger.info("Loading module utils.semantic...")


# -------- AUX CLASSES FOR APP.PY ----------- #

class TTLContent(BaseModel):
    ttl_content: str
    user: str  # Optional, can be overridden by token
    
class DeleteRequest(BaseModel):
    user: Optional[str] = None