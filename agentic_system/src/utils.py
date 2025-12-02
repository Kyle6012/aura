from dataclasses import dataclass
from typing import Dict, Any, Optional
import numpy as np

@dataclass
class Document:
    # unique identifier for the document
    id: str
    # text content of the document
    content: str
    # metadata associated with the document
    metadata: Dict[str, Any]
    # vector embedding of the document content
    embedding: Optional[np.ndarray] = None
