"""
Service Layer Package

This package contains business logic services that implement the application's
core functionality. Services are called by route handlers and interact with
repositories for data access.

Architecture:
- Routes (thin controllers) -> Services (business logic) -> Repositories (data access)
"""

from services.base_service import BaseService

__all__ = ['BaseService']
