import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from .utils import Document
from together import Together
import os

class SemanticRetriever:
    """
    semantic retriever using Together AI embeddings and PostgreSQL storage.
    """
    
    def __init__(self, db_manager=None):
        """
        initialize retriever with database backend.
        
        Args:
            db_manager: DatabaseManager instance for persistent storage
        """
        self.db = db_manager
        self.client = Together(api_key=os.getenv("TOGETHER_API_KEY"))
        self.embedding_model = "togethercomputer/m2-bert-80M-8k-retrieval"
        
        # load documents from database if available
        if self.db:
            self._load_from_db()
        else:
            print("warning: no database connection, using in-memory storage")
            self.documents = []
    
    def _load_from_db(self):
        """load documents from database into memory."""
        try:
            db_docs = self.db.get_all_documents()
            self.documents = [
                Document(
                    id=doc['id'],
                    content=doc['content'],
                    metadata=doc['metadata'],
                    embedding=np.array(doc['embedding'])
                )
                for doc in db_docs
            ]
            print(f"loaded {len(self.documents)} documents from database")
        except Exception as e:
            print(f"error loading documents from db: {e}")
            self.documents = []
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """
        generate embedding using Together AI with retry logic.
        
        Args:
            text: input text
            
        Returns:
            numpy array of embedding vector
        """
        import time
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                embedding = response.data[0].embedding
                return np.array(embedding)
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg or "overloaded" in error_msg.lower():
                    if attempt < max_retries - 1:
                        print(f"API overloaded, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # exponential backoff
                        continue
                print(f"error generating embedding: {e}")
                # fallback to random for development
                return np.random.rand(768)
    
    def search(self, query: str, top_k: int = 3, filters: Optional[Dict] = None) -> List[Document]:
        """
        search for relevant documents using semantic similarity.
        
        Args:
            query (str): search query
            top_k (int): number of results to return
            filters (Optional[Dict]): metadata filters to apply
            
        Returns:
            List[Document]: most relevant documents
        """
        if not self.documents:
            return []
        
        # generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # compute similarities
        doc_embeddings = np.array([doc.embedding for doc in self.documents])
        similarities = cosine_similarity([query_embedding], doc_embeddings)[0]
        
        # create list of (index, similarity) tuples
        results = list(enumerate(similarities))
        
        # sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        # filter and get top-k
        final_results = []
        for idx, score in results:
            doc = self.documents[idx]
            
            # apply filters if provided
            if filters:
                match = True
                for key, value in filters.items():
                    # check if metadata has key and value matches
                    if key not in doc.metadata or doc.metadata[key] != value:
                        match = False
                        break
                if not match:
                    continue
            
            final_results.append(doc)
            if len(final_results) >= top_k:
                break
        
        return final_results
    
    def add_document(self, content: str, metadata: Dict[str, Any]):
        """
        dynamically add a document to the knowledge base.
        
        Args:
            content (str): document content
            metadata (Dict): document metadata
        """
        # generate unique id
        doc_id = f"doc_{len(self.documents)}_{hash(content) % 10000}"
        
        # generate embedding
        embedding = self._generate_embedding(content)
        
        # create document
        doc = Document(
            id=doc_id,
            content=content,
            metadata=metadata,
            embedding=embedding
        )
        
        self.documents.append(doc)
        
        # persist to database if available
        if self.db:
            try:
                self.db.add_document(
                    doc_id=doc_id,
                    content=content,
                    metadata=metadata,
                    embedding=embedding.tolist()
                )
                print(f"added document to database: {doc_id}")
            except Exception as e:
                print(f"error persisting document: {e}")
        else:
            print(f"added document to memory: {doc_id}")
