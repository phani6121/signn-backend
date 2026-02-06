"""
Firestore integration utilities for the backend API.
Provides helper functions for common Firestore operations.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from firebase_admin import firestore
from pydantic import BaseModel

from app.services.firebaseservice import get_firestore_client

logger = logging.getLogger(__name__)


class FirestoreManager:
    """Manager for Firestore database operations."""
    
    def __init__(self):
        self.db = get_firestore_client()
    
    def create_document(
        self,
        collection: str,
        document_id: str,
        data: Dict[str, Any],
        merge: bool = False
    ) -> Dict[str, Any]:
        """
        Create or update a document in Firestore.
        
        Args:
            collection: Name of the collection
            document_id: ID of the document
            data: Dictionary containing the document data
            merge: If True, merge with existing data; if False, overwrite
            
        Returns:
            The data that was written
        """
        try:
            # Add timestamp
            data_with_timestamp = {
                **data,
                "updated_at": datetime.utcnow(),
            }
            
            # If creating new document (not merging), add created_at
            if not merge and "created_at" not in data_with_timestamp:
                data_with_timestamp["created_at"] = datetime.utcnow()
            
            self.db.collection(collection).document(document_id).set(
                data_with_timestamp,
                merge=merge
            )
            
            logger.info(f"Document created/updated: {collection}/{document_id}")
            return data_with_timestamp
            
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise
    
    def get_document(
        self,
        collection: str,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a document from Firestore.
        
        Args:
            collection: Name of the collection
            document_id: ID of the document
            
        Returns:
            Document data or None if not found
        """
        try:
            doc = self.db.collection(collection).document(document_id).get()
            
            if doc.exists:
                logger.info(f"Document retrieved: {collection}/{document_id}")
                return doc.to_dict()
            else:
                logger.warning(f"Document not found: {collection}/{document_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving document: {e}")
            raise
    
    def query_documents(
        self,
        collection: str,
        filters: Optional[List[tuple]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query documents from Firestore.
        
        Args:
            collection: Name of the collection
            filters: List of (field, operator, value) tuples for filtering
            limit: Maximum number of documents to return
            
        Returns:
            List of documents matching the query
        """
        try:
            query = self.db.collection(collection)
            
            # Apply filters if provided
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            docs = query.limit(limit).stream()
            results = [doc.to_dict() for doc in docs]
            
            logger.info(f"Query executed on {collection}: found {len(results)} documents")
            return results
            
        except Exception as e:
            logger.error(f"Error querying documents: {e}")
            raise

    def get_document_by_field(
        self,
        collection: str,
        field: str,
        value: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single document by matching a field value.
        
        Returns:
            Dict with keys: "id" and "data", or None if not found.
        """
        try:
            query = self.db.collection(collection).where(field, "==", value).limit(1)
            docs = list(query.stream())
            if not docs:
                return None
            doc = docs[0]
            return {"id": doc.id, "data": doc.to_dict()}
        except Exception as e:
            logger.error(f"Error querying document by field: {e}")
            raise
    
    def update_document(
        self,
        collection: str,
        document_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update specific fields in a document.
        
        Args:
            collection: Name of the collection
            document_id: ID of the document
            data: Dictionary containing fields to update
            
        Returns:
            The updated data
        """
        try:
            # Add timestamp
            data_with_timestamp = {
                **data,
                "updated_at": datetime.utcnow(),
            }
            
            self.db.collection(collection).document(document_id).update(
                data_with_timestamp
            )
            
            logger.info(f"Document updated: {collection}/{document_id}")
            return data_with_timestamp
            
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise
    
    def delete_document(
        self,
        collection: str,
        document_id: str
    ) -> bool:
        """
        Delete a document from Firestore.
        
        Args:
            collection: Name of the collection
            document_id: ID of the document
            
        Returns:
            True if successful
        """
        try:
            self.db.collection(collection).document(document_id).delete()
            logger.info(f"Document deleted: {collection}/{document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
    
    def batch_write(
        self,
        operations: List[Dict[str, Any]]
    ) -> bool:
        """
        Perform batch write operations.
        
        Args:
            operations: List of operation dicts with keys:
                - 'type': 'set', 'update', or 'delete'
                - 'collection': collection name
                - 'document_id': document ID
                - 'data': data for set/update operations
                
        Returns:
            True if successful
        """
        try:
            batch = self.db.batch()
            
            for op in operations:
                op_type = op.get('type')
                collection = op.get('collection')
                doc_id = op.get('document_id')
                data = op.get('data', {})
                
                doc_ref = self.db.collection(collection).document(doc_id)
                
                if op_type == 'set':
                    data['updated_at'] = datetime.utcnow()
                    if 'created_at' not in data:
                        data['created_at'] = datetime.utcnow()
                    batch.set(doc_ref, data)
                    
                elif op_type == 'update':
                    data['updated_at'] = datetime.utcnow()
                    batch.update(doc_ref, data)
                    
                elif op_type == 'delete':
                    batch.delete(doc_ref)
            
            batch.commit()
            logger.info(f"Batch write completed: {len(operations)} operations")
            return True
            
        except Exception as e:
            logger.error(f"Error in batch write: {e}")
            raise


# Create a global instance
firestore_manager = FirestoreManager()
