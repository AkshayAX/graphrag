# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Access control filtering for GraphRAG queries."""

from typing import Any
from uuid import UUID

from graphrag.data_model.entity import Entity
from graphrag.data_model.relationship import Relationship
from graphrag.data_model.text_unit import TextUnit


class AccessControlFilter:
    """Filter entities, relationships, and text units based on access control metadata.

    Implements Option C: Filtered Context approach where entities are visible but only
    show text units and relationships that the user has access to.

    Access Control Rules:
    - public: Accessible to all users
    - domain: Accessible to users with matching domains
    - private: Accessible only to the owner
    """

    def __init__(
        self,
        user_id: str | UUID | None = None,
        user_domains: list[str] | None = None,
    ):
        """Initialize access control filter.

        Args:
            user_id: The ID of the current user (for private document access)
            user_domains: List of domain tags the user has access to (e.g., ["finance", "engineering"])
        """
        self.user_id = str(user_id) if user_id else None
        self.user_domains = set(user_domains) if user_domains else set()

    def can_access_document(self, attributes: dict[str, Any] | None) -> bool:
        """Check if user can access a document/text unit based on its attributes.

        Args:
            attributes: Dictionary containing access control metadata:
                - access_type: "public" | "domain" | "private"
                - owner_id: UUID of document owner (for private docs)
                - access_domains: List of domain tags (for domain-restricted docs)

        Returns:
            True if user has access, False otherwise
        """
        if not attributes:
            return True  # Default: allow if no access control metadata

        access_type = attributes.get("access_type", "public")

        # Public documents are accessible to everyone
        if access_type == "public":
            return True

        # Private documents are only accessible to the owner
        if access_type == "private":
            if not self.user_id:
                return False
            owner_id = attributes.get("owner_id")
            return str(owner_id) == self.user_id if owner_id else False

        # Domain-restricted documents require matching domain
        if access_type == "domain":
            doc_domains = attributes.get("access_domains", [])
            if isinstance(doc_domains, str):
                # Handle case where domains might be stored as comma-separated string
                doc_domains = [d.strip() for d in doc_domains.split(",")]
            doc_domains_set = set(doc_domains) if doc_domains else set()
            return bool(self.user_domains & doc_domains_set)  # Any overlap grants access

        # Unknown access type - deny by default for security
        return False

    def filter_text_units(self, text_units: list[TextUnit]) -> list[TextUnit]:
        """Filter text units based on access control.

        Args:
            text_units: List of text units to filter

        Returns:
            Filtered list containing only accessible text units
        """
        return [tu for tu in text_units if self.can_access_document(tu.attributes)]

    def filter_entities_by_source(
        self,
        entities: list[Entity],
        accessible_text_unit_ids: set[str],
    ) -> list[Entity]:
        """Filter entities: include if user has access to at least one source text unit.

        This implements Option C: entities remain visible if user has access to ANY
        source document, but the context will only include accessible text units.

        Args:
            entities: List of entities to filter
            accessible_text_unit_ids: Set of text unit IDs the user can access

        Returns:
            Filtered list of entities
        """
        if not accessible_text_unit_ids:
            # If no accessible text units, return empty list
            return []

        filtered_entities = []
        for entity in entities:
            # Check if entity has any text unit sources we can access
            if hasattr(entity, "text_unit_ids") and entity.text_unit_ids:
                # Include entity if ANY of its source text units are accessible
                if any(
                    tu_id in accessible_text_unit_ids for tu_id in entity.text_unit_ids
                ):
                    filtered_entities.append(entity)
            else:
                # No source tracking - include by default
                # You could change this to exclude for stricter security
                filtered_entities.append(entity)

        return filtered_entities

    def filter_relationships_by_source(
        self,
        relationships: list[Relationship],
        accessible_text_unit_ids: set[str],
    ) -> list[Relationship]:
        """Filter relationships based on accessible source text units.

        Args:
            relationships: List of relationships to filter
            accessible_text_unit_ids: Set of text unit IDs the user can access

        Returns:
            Filtered list of relationships
        """
        if not accessible_text_unit_ids:
            return []

        filtered_relationships = []
        for rel in relationships:
            # Check if relationship has any text unit sources we can access
            if hasattr(rel, "text_unit_ids") and rel.text_unit_ids:
                # Include relationship if ANY of its source text units are accessible
                if any(
                    tu_id in accessible_text_unit_ids for tu_id in rel.text_unit_ids
                ):
                    filtered_relationships.append(rel)
            else:
                # No source tracking - include by default
                filtered_relationships.append(rel)

        return filtered_relationships

    def filter_context_data(
        self,
        text_units: list[TextUnit] | None = None,
        entities: list[Entity] | None = None,
        relationships: list[Relationship] | None = None,
    ) -> tuple[list[TextUnit], list[Entity], list[Relationship]]:
        """Filter all context data based on access control.

        This is a convenience method that filters text units first, then uses
        the accessible text unit IDs to filter entities and relationships.

        Args:
            text_units: List of text units
            entities: List of entities
            relationships: List of relationships

        Returns:
            Tuple of (filtered_text_units, filtered_entities, filtered_relationships)
        """
        # Filter text units first
        filtered_text_units = (
            self.filter_text_units(text_units) if text_units else []
        )
        accessible_tu_ids = {tu.id for tu in filtered_text_units}

        # Filter entities based on accessible text units
        filtered_entities = []
        if entities:
            filtered_entities = self.filter_entities_by_source(
                entities, accessible_tu_ids
            )

        # Filter relationships based on accessible text units
        filtered_relationships = []
        if relationships:
            filtered_relationships = self.filter_relationships_by_source(
                relationships, accessible_tu_ids
            )

        return filtered_text_units, filtered_entities, filtered_relationships
