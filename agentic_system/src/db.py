import os
import json
import time
from typing import Dict, List, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import numpy as np

Base = declarative_base()

class InteractionLog(Base):
    """interaction log model."""
    __tablename__ = 'interaction_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event = Column(String(100))
    details = Column(Text)

class KnowledgeDocument(Base):
    """knowledge base document with embeddings."""
    __tablename__ = 'knowledge_documents'
    
    id = Column(Integer, primary_key=True)
    doc_id = Column(String(100), unique=True)
    content = Column(Text)
    doc_metadata = Column(Text)  # JSON string (renamed to avoid SQLAlchemy reserved word)
    embedding = Column(Text)  # JSON array of floats
    created_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    """conversation session."""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True)
    title = Column(String(200))
    tags = Column(Text, default='')  # Comma-separated tags
    is_archived = Column(Integer, default=0)  # Use Integer for SQLite compatibility
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SessionMessage(Base):
    """chat message in a session."""
    __tablename__ = 'session_messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100))
    role = Column(String(20))  # user or assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class SessionDocument(Base):
    """document/image associated with a session."""
    __tablename__ = 'session_documents'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100))
    doc_id = Column(String(100))
    file_path = Column(Text)
    file_type = Column(String(50))  # pdf, image, etc
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    id = Column(Integer, primary_key=True)
    proficiency = Column(String, default="fundamental")
    topics_covered = Column(Text, default="[]") # Stored as JSON string

class DatabaseManager:
    """
    Manages PostgreSQL database connections and operations.
    """
    def __init__(self):
        self.engine = self._get_engine()
        Base.metadata.create_all(self.engine)
        self._migrate_schema()
        self.Session = sessionmaker(bind=self.engine)

    def _migrate_schema(self):
        """
        Check for missing columns and add them if necessary.
        This handles schema evolution for existing databases.
        """
        from sqlalchemy import text
        session = sessionmaker(bind=self.engine)()
        try:
            # Check if tags column exists in sessions
            try:
                session.execute(text("SELECT tags FROM sessions LIMIT 1"))
            except Exception:
                print("migrating schema: adding tags column to sessions")
                session.rollback()
                session.execute(text("ALTER TABLE sessions ADD COLUMN tags TEXT DEFAULT ''"))
                session.commit()
            
            # Check if is_archived column exists in sessions
            try:
                session.execute(text("SELECT is_archived FROM sessions LIMIT 1"))
            except Exception:
                print("migrating schema: adding is_archived column to sessions")
                session.rollback()
                session.execute(text("ALTER TABLE sessions ADD COLUMN is_archived INTEGER DEFAULT 0"))
                session.commit()
                
        except Exception as e:
            print(f"schema migration warning: {e}")
            session.rollback()
        finally:
            session.close()

    def _get_engine(self):
        """
        Creates the SQLAlchemy engine with retry logic for Docker startup.
        """
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db = os.getenv("POSTGRES_DB", "agentic_db")
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        
        url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        
        # retry connection for docker startup
        max_retries = 5
        for i in range(max_retries):
            try:
                engine = create_engine(url)
                engine.connect()
                return engine
            except Exception as e:
                if i == max_retries - 1:
                    raise e
                print(f"waiting for database... ({i+1}/{max_retries})")
                time.sleep(2)

    def log_interaction(self, event: str, details: dict):
        session = self.Session()
        try:
            log = InteractionLog(event=event, details=details)
            session.add(log)
            session.commit()
            return log.id
        finally:
            session.close()

    def get_profile(self):
        session = self.Session()
        try:
            profile = session.query(UserProfile).first()
            if not profile:
                profile = UserProfile()
                session.add(profile)
                session.commit()
            
            # parse topics_covered from JSON string
            try:
                topics = json.loads(profile.topics_covered) if profile.topics_covered else []
            except:
                topics = []
                
            return {"proficiency": profile.proficiency, "topics_covered": topics}
        finally:
            session.close()

    def update_profile(self, proficiency: str = None, topic: str = None):
        session = self.Session()
        try:
            profile = session.query(UserProfile).first()
            if not profile:
                profile = UserProfile()
                session.add(profile)
            
            if proficiency:
                profile.proficiency = proficiency
            
            if topic:
                # parse JSON string to list
                try:
                    current_topics = json.loads(profile.topics_covered) if profile.topics_covered else []
                except:
                    current_topics = []
                    
                if topic not in current_topics:
                    current_topics.append(topic)
                    profile.topics_covered = json.dumps(current_topics)
            
            session.commit()
            
            # return parsed data
            topics = json.loads(profile.topics_covered) if profile.topics_covered else []
            return {"proficiency": profile.proficiency, "topics_covered": topics}
        finally:
            session.close()
    
    def add_document(self, doc_id: str, content: str, metadata: Dict, embedding: List[float]) -> bool:
        """
        Add document to knowledge base.
        
        Args:
            doc_id: unique document identifier
            content: document text
            metadata: document metadata
            embedding: vector embedding
            
        Returns:
            bool: success status
        """
        session = self.Session()
        try:
            doc = KnowledgeDocument(
                doc_id=doc_id,
                content=content,
                doc_metadata=json.dumps(metadata),  # Use doc_metadata field
                embedding=json.dumps(embedding)
            )
            session.add(doc)
            session.commit()
            return True
        except Exception as e:
            print(f"error adding document: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_all_documents(self) -> List[Dict]:
        """
        Get all documents from knowledge base.
        
        Returns:
            List of documents with embeddings
        """
        session = self.Session()
        try:
            docs = session.query(KnowledgeDocument).all()
            return [{ 
                'id': doc.doc_id,
                'content': doc.content,
                'metadata': json.loads(doc.doc_metadata) if doc.doc_metadata else {},  # Read from doc_metadata
                'embedding': json.loads(doc.embedding) if doc.embedding else []
            } for doc in docs]
        except Exception as e:
            print(f"error retrieving documents: {e}")
            return []
        finally:
            session.close()
    
    # Session Management Methods
    def create_session(self, title: str = "New Session") -> str:
        """Create a new conversation session."""
        import uuid
        session_id = str(uuid.uuid4())[:8]
        session = self.Session()
        try:
            new_session = Session(
                session_id=session_id,
                title=title
            )
            session.add(new_session)
            session.commit()
            return session_id
        except Exception as e:
            print(f"error creating session: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def get_all_sessions(self, include_archived: bool = False) -> List[Dict]:
        """Get all sessions, optionally including archived ones."""
        session = self.Session()
        try:
            query = session.query(Session).order_by(Session.updated_at.desc())
            if not include_archived:
                query = query.filter_by(is_archived=0)
            sessions = query.all()
            return [{
                'session_id': s.session_id,
                'title': s.title,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'updated_at': s.updated_at.isoformat() if s.updated_at else None,
                'is_archived': bool(s.is_archived)
            } for s in sessions]
        except Exception as e:
            print(f"error getting sessions: {e}")
            return []
        finally:
            session.close()
    
    def save_message(self, session_id: str, role: str, content: str):
        """Save a chat message to session."""
        session = self.Session()
        try:
            message = SessionMessage(
                session_id=session_id,
                role=role,
                content=content
            )
            session.add(message)
            session.commit()
        except Exception as e:
            print(f"error saving message: {e}")
            session.rollback()
        finally:
            session.close()
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages for a session."""
        session = self.Session()
        try:
            messages = session.query(SessionMessage).filter_by(
                session_id=session_id
            ).order_by(SessionMessage.created_at).all()
            return [{
                'role': m.role,
                'content': m.content
            } for m in messages]
        except Exception as e:
            print(f"error getting messages: {e}")
            return []
        finally:
            session.close()
    
    def add_session_document(self, session_id: str, doc_id: str, file_path: str, file_type: str):
        """Associate a document with a session."""
        session = self.Session()
        try:
            doc = SessionDocument(
                session_id=session_id,
                doc_id=doc_id,
                file_path=file_path,
                file_type=file_type
            )
            session.add(doc)
            session.commit()
        except Exception as e:
            print(f"error adding session document: {e}")
            session.rollback()
        finally:
            session.close()
    
    def get_session_documents(self, session_id: str) -> List[Dict]:
        """Get all documents for a session."""
        session = self.Session()
        try:
            docs = session.query(SessionDocument).filter_by(
                session_id=session_id
            ).all()
            return [{
                'doc_id': d.doc_id,
                'file_path': d.file_path,
                'file_type': d.file_type,
                'created_at': d.created_at.isoformat() if d.created_at else None
            } for d in docs]
        except Exception as e:
            print(f"error getting session documents: {e}")
            return []
        finally:
            session.close()
    
    def update_session_title(self, session_id: str, title: str) -> bool:
        """Update session title."""
        session = self.Session()
        try:
            sess = session.query(Session).filter_by(session_id=session_id).first()
            if sess:
                sess.title = title
                sess.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            print(f"error updating session title: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def delete_session(self, session_id: str, hard_delete: bool = False) -> bool:
        """Delete a session and all related data."""
        session = self.Session()
        try:
            if hard_delete:
                # Delete all related messages
                session.query(SessionMessage).filter_by(session_id=session_id).delete()
                # Delete all related documents
                session.query(SessionDocument).filter_by(session_id=session_id).delete()
                # Delete session
                session.query(Session).filter_by(session_id=session_id).delete()
            else:
                # Soft delete - just archive
                sess = session.query(Session).filter_by(session_id=session_id).first()
                if sess:
                    sess.is_archived = 1
                    sess.updated_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            print(f"error deleting session: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def archive_session(self, session_id: str) -> bool:
        """Archive a session (soft delete)."""
        return self.delete_session(session_id, hard_delete=False)
    
    def restore_session(self, session_id: str) -> bool:
        """Restore an archived session."""
        session = self.Session()
        try:
            sess = session.query(Session).filter_by(session_id=session_id).first()
            if sess:
                sess.is_archived = 0
                sess.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            print(f"error restoring session: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session."""
        session = self.Session()
        try:
            # Get message count
            message_count = session.query(SessionMessage).filter_by(
                session_id=session_id
            ).count()
            
            # Get document count
            doc_count = session.query(SessionDocument).filter_by(
                session_id=session_id
            ).count()
            
            # Get session info
            sess = session.query(Session).filter_by(session_id=session_id).first()
            
            return {
                'message_count': message_count,
                'document_count': doc_count,
                'created_at': sess.created_at.isoformat() if sess and sess.created_at else None,
                'updated_at': sess.updated_at.isoformat() if sess and sess.updated_at else None,
                'is_archived': bool(sess.is_archived) if sess else False
            }
        except Exception as e:
            print(f"error getting session stats: {e}")
            return {
                'message_count': 0,
                'document_count': 0,
                'created_at': None,
                'updated_at': None,
                'is_archived': False
            }
        finally:
            session.close()
    
    def export_session(self, session_id: str) -> Dict:
        """Export session to JSON format."""
        session = self.Session()
        try:
            # Get session info
            sess = session.query(Session).filter_by(session_id=session_id).first()
            if not sess:
                return {'error': 'Session not found'}
            
            # Get messages
            messages = self.get_session_messages(session_id)
            
            # Get documents
            documents = self.get_session_documents(session_id)
            
            # Get stats
            stats = self.get_session_stats(session_id)
            
            return {
                'session_id': session_id,
                'title': sess.title,
                'created_at': sess.created_at.isoformat() if sess.created_at else None,
                'updated_at': sess.updated_at.isoformat() if sess.updated_at else None,
                'is_archived': bool(sess.is_archived),
                'statistics': stats,
                'messages': messages,
                'documents': documents
            }
        except Exception as e:
            print(f"error exporting session: {e}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def import_session(self, session_data: Dict) -> str:
        """
        Import session from exported JSON data.
        
        Args:
            session_data (Dict): Exported session data
            
        Returns:
            str: New session ID or error message
        """
        session = self.Session()
        try:
            # Generate new session ID
            from uuid import uuid4
            new_session_id = str(uuid4())
            
            # Create new session
            new_session = Session(
                session_id=new_session_id,
                title=session_data.get('title', 'Imported Session'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_archived=0
            )
            session.add(new_session)
            session.flush()
            
            # Import messages
            messages = session_data.get('messages', [])
            for msg in messages:
                new_msg = SessionMessage(
                    session_id=new_session_id,
                    role=msg['role'],
                    content=msg['content'],
                    created_at=datetime.utcnow()
                )
                session.add(new_msg)
            
            # Import document references (if any)
            documents = session_data.get('documents', [])
            for doc in documents:
                new_doc = SessionDocument(
                    session_id=new_session_id,
                    filename=doc['filename'],
                    file_path=doc.get('file_path', ''),
                    uploaded_at=datetime.utcnow()
                )
                session.add(new_doc)
            
            session.commit()
            return new_session_id
            
        except Exception as e:
            print(f"error importing session: {e}")
            session.rollback()
            return f"error: {str(e)}"
        finally:
            session.close()
    
    def update_session_tags(self, session_id: str, tags: List[str]) -> bool:
        """Update tags for a session."""
        session = self.Session()
        try:
            sess = session.query(Session).filter_by(session_id=session_id).first()
            if sess:
                sess.tags = ','.join(tags) if tags else ''
                sess.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            print(f"error updating tags: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_session_tags(self, session_id: str) -> List[str]:
        """Get tags for a specific session."""
        session = self.Session()
        try:
            sess = session.query(Session).filter_by(session_id=session_id).first()
            if sess and sess.tags:
                return [t.strip() for t in sess.tags.split(',') if t.strip()]
            return []
        except Exception as e:
            print(f"error getting tags: {e}")
            return []
        finally:
            session.close()
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags across all sessions."""
        session = self.Session()
        try:
            sessions = session.query(Session).all()
            all_tags = set()
            for sess in sessions:
                if sess.tags:
                    tags = [t.strip() for t in sess.tags.split(',') if t.strip()]
                    all_tags.update(tags)
            return sorted(list(all_tags))
        except Exception as e:
            print(f"error getting all tags: {e}")
            return []
        finally:
            session.close()
    
    def get_analytics(self) -> Dict:
        """Get system-wide analytics."""
        session = self.Session()
        try:
            # Total sessions
            total_sessions = session.query(Session).filter_by(is_archived=0).count()
            archived_sessions = session.query(Session).filter_by(is_archived=1).count()
            
            # Total messages
            total_messages = session.query(SessionMessage).count()
            
            # Total documents
            total_documents = session.query(SessionDocument).count()
            
            # Calculate language usage from tool logs (if available)
            # This is a simplified version - you could track this more precisely
            language_usage = {
                'python': 0,
                'javascript': 0,
                'go': 0,
                'rust': 0,
                'c': 0,
                'cpp': 0
            }
            
            # Recent activity (last 7 days)
            from datetime import timedelta
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_sessions = session.query(Session).filter(
                Session.created_at >= week_ago
            ).count()
            
            recent_messages = session.query(SessionMessage).filter(
                SessionMessage.created_at >= week_ago
            ).count()
            
            # Tag usage
            all_tags = self.get_all_tags()
            tag_counts = {}
            for tag in all_tags:
                count = session.query(Session).filter(
                    Session.tags.like(f'%{tag}%')
                ).count()
                tag_counts[tag] = count
            
            return {
                'total_sessions': total_sessions,
                'archived_sessions': archived_sessions,
                'total_messages': total_messages,
                'total_documents': total_documents,
                'language_usage': language_usage,
                'recent_activity': {
                    'sessions_7d': recent_sessions,
                    'messages_7d': recent_messages
                },
                'tag_usage': tag_counts
            }
        except Exception as e:
            print(f"error getting analytics: {e}")
            return {}
        finally:
            session.close()


