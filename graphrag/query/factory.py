# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Query Factory methods to support CLI."""

from uuid import UUID

from graphrag.callbacks.query_callbacks import QueryCallbacks
from graphrag.config.models.graph_rag_config import GraphRagConfig
from graphrag.data_model.community import Community
from graphrag.data_model.community_report import CommunityReport
from graphrag.data_model.covariate import Covariate
from graphrag.data_model.entity import Entity
from graphrag.data_model.relationship import Relationship
from graphrag.data_model.text_unit import TextUnit
from graphrag.language_model.manager import ModelManager
from graphrag.language_model.providers.fnllm.utils import (
    get_openai_model_parameters_from_config,
)
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.filters.access_control import AccessControlFilter
from graphrag.query.structured_search.basic_search.basic_context import (
    BasicSearchContext,
)
from graphrag.query.structured_search.basic_search.search import BasicSearch
from graphrag.query.structured_search.drift_search.drift_context import (
    DRIFTSearchContextBuilder,
)
from graphrag.query.structured_search.drift_search.search import DRIFTSearch
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.tokenizer.get_tokenizer import get_tokenizer
from graphrag.vector_stores.base import BaseVectorStore


def get_local_search_engine(
    config: GraphRagConfig,
    reports: list[CommunityReport],
    text_units: list[TextUnit],
    entities: list[Entity],
    relationships: list[Relationship],
    covariates: dict[str, list[Covariate]],
    response_type: str,
    description_embedding_store: BaseVectorStore,
    system_prompt: str | None = None,
    callbacks: list[QueryCallbacks] | None = None,
) -> LocalSearch:
    """Create a local search engine based on data + configuration."""
    model_settings = config.get_language_model_config(config.local_search.chat_model_id)

    chat_model = ModelManager().get_or_create_chat_model(
        name="local_search_chat",
        model_type=model_settings.type,
        config=model_settings,
    )

    embedding_settings = config.get_language_model_config(
        config.local_search.embedding_model_id
    )

    embedding_model = ModelManager().get_or_create_embedding_model(
        name="local_search_embedding",
        model_type=embedding_settings.type,
        config=embedding_settings,
    )

    tokenizer = get_tokenizer(model_config=model_settings)

    ls_config = config.local_search

    model_params = get_openai_model_parameters_from_config(model_settings)

    return LocalSearch(
        model=chat_model,
        system_prompt=system_prompt,
        context_builder=LocalSearchMixedContext(
            community_reports=reports,
            text_units=text_units,
            entities=entities,
            relationships=relationships,
            covariates=covariates,
            entity_text_embeddings=description_embedding_store,
            embedding_vectorstore_key=EntityVectorStoreKey.ID,  # if the vectorstore uses entity title as ids, set this to EntityVectorStoreKey.TITLE
            text_embedder=embedding_model,
            tokenizer=tokenizer,
        ),
        tokenizer=tokenizer,
        model_params=model_params,
        context_builder_params={
            "text_unit_prop": ls_config.text_unit_prop,
            "community_prop": ls_config.community_prop,
            "conversation_history_max_turns": ls_config.conversation_history_max_turns,
            "conversation_history_user_turns_only": True,
            "top_k_mapped_entities": ls_config.top_k_entities,
            "top_k_relationships": ls_config.top_k_relationships,
            "include_entity_rank": True,
            "include_relationship_weight": True,
            "include_community_rank": False,
            "return_candidate_context": False,
            "embedding_vectorstore_key": EntityVectorStoreKey.ID,  # set this to EntityVectorStoreKey.TITLE if the vectorstore uses entity title as ids
            "max_context_tokens": ls_config.max_context_tokens,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
        },
        response_type=response_type,
        callbacks=callbacks,
    )


def get_global_search_engine(
    config: GraphRagConfig,
    reports: list[CommunityReport],
    entities: list[Entity],
    communities: list[Community],
    response_type: str,
    dynamic_community_selection: bool = False,
    map_system_prompt: str | None = None,
    reduce_system_prompt: str | None = None,
    general_knowledge_inclusion_prompt: str | None = None,
    callbacks: list[QueryCallbacks] | None = None,
) -> GlobalSearch:
    """Create a global search engine based on data + configuration."""
    model_settings = config.get_language_model_config(
        config.global_search.chat_model_id
    )

    model = ModelManager().get_or_create_chat_model(
        name="global_search",
        model_type=model_settings.type,
        config=model_settings,
    )

    model_params = get_openai_model_parameters_from_config(model_settings)

    # Here we get encoding based on specified encoding name
    tokenizer = get_tokenizer(model_config=model_settings)
    gs_config = config.global_search

    dynamic_community_selection_kwargs = {}
    if dynamic_community_selection:
        # TODO: Allow for another llm definition only for Global Search to leverage -mini models

        dynamic_community_selection_kwargs.update({
            "model": model,
            "tokenizer": tokenizer,
            "keep_parent": gs_config.dynamic_search_keep_parent,
            "num_repeats": gs_config.dynamic_search_num_repeats,
            "use_summary": gs_config.dynamic_search_use_summary,
            "concurrent_coroutines": model_settings.concurrent_requests,
            "threshold": gs_config.dynamic_search_threshold,
            "max_level": gs_config.dynamic_search_max_level,
            "model_params": {**model_params},
        })

    return GlobalSearch(
        model=model,
        map_system_prompt=map_system_prompt,
        reduce_system_prompt=reduce_system_prompt,
        general_knowledge_inclusion_prompt=general_knowledge_inclusion_prompt,
        context_builder=GlobalCommunityContext(
            community_reports=reports,
            communities=communities,
            entities=entities,
            tokenizer=tokenizer,
            dynamic_community_selection=dynamic_community_selection,
            dynamic_community_selection_kwargs=dynamic_community_selection_kwargs,
        ),
        tokenizer=tokenizer,
        max_data_tokens=gs_config.data_max_tokens,
        map_llm_params={**model_params},
        reduce_llm_params={**model_params},
        map_max_length=gs_config.map_max_length,
        reduce_max_length=gs_config.reduce_max_length,
        allow_general_knowledge=False,
        json_mode=False,
        context_builder_params={
            "use_community_summary": False,
            "shuffle_data": True,
            "include_community_rank": True,
            "min_community_rank": 0,
            "community_rank_name": "rank",
            "include_community_weight": True,
            "community_weight_name": "occurrence weight",
            "normalize_community_weight": True,
            "max_context_tokens": gs_config.max_context_tokens,
            "context_name": "Reports",
        },
        concurrent_coroutines=model_settings.concurrent_requests,
        response_type=response_type,
        callbacks=callbacks,
    )


def get_drift_search_engine(
    config: GraphRagConfig,
    reports: list[CommunityReport],
    text_units: list[TextUnit],
    entities: list[Entity],
    relationships: list[Relationship],
    description_embedding_store: BaseVectorStore,
    response_type: str,
    local_system_prompt: str | None = None,
    reduce_system_prompt: str | None = None,
    callbacks: list[QueryCallbacks] | None = None,
) -> DRIFTSearch:
    """Create a local search engine based on data + configuration."""
    chat_model_settings = config.get_language_model_config(
        config.drift_search.chat_model_id
    )

    chat_model = ModelManager().get_or_create_chat_model(
        name="drift_search_chat",
        model_type=chat_model_settings.type,
        config=chat_model_settings,
    )

    embedding_model_settings = config.get_language_model_config(
        config.drift_search.embedding_model_id
    )

    embedding_model = ModelManager().get_or_create_embedding_model(
        name="drift_search_embedding",
        model_type=embedding_model_settings.type,
        config=embedding_model_settings,
    )

    tokenizer = get_tokenizer(model_config=chat_model_settings)

    return DRIFTSearch(
        model=chat_model,
        context_builder=DRIFTSearchContextBuilder(
            model=chat_model,
            text_embedder=embedding_model,
            entities=entities,
            relationships=relationships,
            reports=reports,
            entity_text_embeddings=description_embedding_store,
            text_units=text_units,
            local_system_prompt=local_system_prompt,
            reduce_system_prompt=reduce_system_prompt,
            config=config.drift_search,
            response_type=response_type,
        ),
        tokenizer=tokenizer,
        callbacks=callbacks,
    )


def get_basic_search_engine(
    text_units: list[TextUnit],
    text_unit_embeddings: BaseVectorStore,
    config: GraphRagConfig,
    system_prompt: str | None = None,
    response_type: str = "multiple paragraphs",
    callbacks: list[QueryCallbacks] | None = None,
) -> BasicSearch:
    """Create a basic search engine based on data + configuration."""
    chat_model_settings = config.get_language_model_config(
        config.basic_search.chat_model_id
    )

    chat_model = ModelManager().get_or_create_chat_model(
        name="basic_search_chat",
        model_type=chat_model_settings.type,
        config=chat_model_settings,
    )

    embedding_model_settings = config.get_language_model_config(
        config.basic_search.embedding_model_id
    )

    embedding_model = ModelManager().get_or_create_embedding_model(
        name="basic_search_embedding",
        model_type=embedding_model_settings.type,
        config=embedding_model_settings,
    )

    tokenizer = get_tokenizer(model_config=chat_model_settings)

    bs_config = config.basic_search

    model_params = get_openai_model_parameters_from_config(chat_model_settings)

    return BasicSearch(
        model=chat_model,
        system_prompt=system_prompt,
        response_type=response_type,
        context_builder=BasicSearchContext(
            text_embedder=embedding_model,
            text_unit_embeddings=text_unit_embeddings,
            text_units=text_units,
            tokenizer=tokenizer,
        ),
        tokenizer=tokenizer,
        model_params=model_params,
        context_builder_params={
            "embedding_vectorstore_key": "id",
            "k": bs_config.k,
            "max_context_tokens": bs_config.max_context_tokens,
        },
        callbacks=callbacks,
    )


# Access Control Wrapper Functions


def get_local_search_engine_with_access_control(
    config: GraphRagConfig,
    reports: list[CommunityReport],
    text_units: list[TextUnit],
    entities: list[Entity],
    relationships: list[Relationship],
    covariates: dict[str, list[Covariate]],
    response_type: str,
    description_embedding_store: BaseVectorStore,
    user_id: str | UUID | None = None,
    user_domains: list[str] | None = None,
    system_prompt: str | None = None,
    callbacks: list[QueryCallbacks] | None = None,
) -> LocalSearch:
    """Create a local search engine with access control filtering.

    Args:
        config: GraphRAG configuration
        reports: List of community reports
        text_units: List of text units
        entities: List of entities
        relationships: List of relationships
        covariates: Dictionary of covariates
        response_type: Type of response expected
        description_embedding_store: Vector store for entity descriptions
        user_id: ID of the current user (for private document access)
        user_domains: List of domain tags the user has access to
        system_prompt: Optional custom system prompt
        callbacks: Optional query callbacks

    Returns:
        LocalSearch instance with access-controlled data
    """
    # Create access control filter
    access_filter = AccessControlFilter(user_id=user_id, user_domains=user_domains)

    # Filter data based on access control
    filtered_text_units, filtered_entities, filtered_relationships = (
        access_filter.filter_context_data(
            text_units=text_units,
            entities=entities,
            relationships=relationships,
        )
    )

    # IMPORTANT: Disable community reports for access-controlled queries
    # Community reports contain aggregated data from all sources and would leak restricted information
    # We pass an empty list to ensure only directly accessible data is used
    filtered_reports = []

    # Create search engine with filtered data
    return get_local_search_engine(
        config=config,
        reports=filtered_reports,  # Use empty reports to prevent data leakage
        text_units=filtered_text_units,
        entities=filtered_entities,
        relationships=filtered_relationships,
        covariates=covariates,
        response_type=response_type,
        description_embedding_store=description_embedding_store,
        system_prompt=system_prompt,
        callbacks=callbacks,
    )


def get_global_search_engine_with_access_control(
    config: GraphRagConfig,
    reports: list[CommunityReport],
    entities: list[Entity],
    communities: list[Community],
    response_type: str,
    user_id: str | UUID | None = None,
    user_domains: list[str] | None = None,
    dynamic_community_selection: bool = False,
    map_system_prompt: str | None = None,
    reduce_system_prompt: str | None = None,
    general_knowledge_inclusion_prompt: str | None = None,
    callbacks: list[QueryCallbacks] | None = None,
) -> GlobalSearch:
    """Create a global search engine with access control filtering.

    Args:
        config: GraphRAG configuration
        reports: List of community reports
        entities: List of entities
        communities: List of communities
        response_type: Type of response expected
        user_id: ID of the current user (for private document access)
        user_domains: List of domain tags the user has access to
        dynamic_community_selection: Whether to use dynamic community selection
        map_system_prompt: Optional custom map system prompt
        reduce_system_prompt: Optional custom reduce system prompt
        general_knowledge_inclusion_prompt: Optional general knowledge prompt
        callbacks: Optional query callbacks

    Returns:
        GlobalSearch instance with access-controlled data
    """
    # Create access control filter
    access_filter = AccessControlFilter(user_id=user_id, user_domains=user_domains)

    # Filter entities (global search primarily uses entities and community reports)
    filtered_entities = access_filter.filter_entities_by_source(
        entities=entities,
        accessible_text_unit_ids=set(),  # Global search doesn't directly use text units
    )

    # Note: Community reports aggregation may need special handling
    # For now, we filter entities which affects which communities are relevant

    return get_global_search_engine(
        config=config,
        reports=reports,
        entities=filtered_entities,
        communities=communities,
        response_type=response_type,
        dynamic_community_selection=dynamic_community_selection,
        map_system_prompt=map_system_prompt,
        reduce_system_prompt=reduce_system_prompt,
        general_knowledge_inclusion_prompt=general_knowledge_inclusion_prompt,
        callbacks=callbacks,
    )


def get_drift_search_engine_with_access_control(
    config: GraphRagConfig,
    reports: list[CommunityReport],
    text_units: list[TextUnit],
    entities: list[Entity],
    relationships: list[Relationship],
    description_embedding_store: BaseVectorStore,
    response_type: str,
    user_id: str | UUID | None = None,
    user_domains: list[str] | None = None,
    local_system_prompt: str | None = None,
    reduce_system_prompt: str | None = None,
    callbacks: list[QueryCallbacks] | None = None,
) -> DRIFTSearch:
    """Create a DRIFT search engine with access control filtering.

    Args:
        config: GraphRAG configuration
        reports: List of community reports
        text_units: List of text units
        entities: List of entities
        relationships: List of relationships
        description_embedding_store: Vector store for entity descriptions
        response_type: Type of response expected
        user_id: ID of the current user (for private document access)
        user_domains: List of domain tags the user has access to
        local_system_prompt: Optional custom local system prompt
        reduce_system_prompt: Optional custom reduce system prompt
        callbacks: Optional query callbacks

    Returns:
        DRIFTSearch instance with access-controlled data
    """
    # Create access control filter
    access_filter = AccessControlFilter(user_id=user_id, user_domains=user_domains)

    # Filter data based on access control
    filtered_text_units, filtered_entities, filtered_relationships = (
        access_filter.filter_context_data(
            text_units=text_units,
            entities=entities,
            relationships=relationships,
        )
    )

    return get_drift_search_engine(
        config=config,
        reports=reports,
        text_units=filtered_text_units,
        entities=filtered_entities,
        relationships=filtered_relationships,
        description_embedding_store=description_embedding_store,
        response_type=response_type,
        local_system_prompt=local_system_prompt,
        reduce_system_prompt=reduce_system_prompt,
        callbacks=callbacks,
    )


def get_basic_search_engine_with_access_control(
    text_units: list[TextUnit],
    text_unit_embeddings: BaseVectorStore,
    config: GraphRagConfig,
    user_id: str | UUID | None = None,
    user_domains: list[str] | None = None,
    system_prompt: str | None = None,
    response_type: str = "multiple paragraphs",
    callbacks: list[QueryCallbacks] | None = None,
) -> BasicSearch:
    """Create a basic search engine with access control filtering.

    Args:
        text_units: List of text units
        text_unit_embeddings: Vector store for text unit embeddings
        config: GraphRAG configuration
        user_id: ID of the current user (for private document access)
        user_domains: List of domain tags the user has access to
        system_prompt: Optional custom system prompt
        response_type: Type of response expected
        callbacks: Optional query callbacks

    Returns:
        BasicSearch instance with access-controlled data
    """
    # Create access control filter
    access_filter = AccessControlFilter(user_id=user_id, user_domains=user_domains)

    # Filter text units
    filtered_text_units = access_filter.filter_text_units(text_units)

    return get_basic_search_engine(
        text_units=filtered_text_units,
        text_unit_embeddings=text_unit_embeddings,
        config=config,
        system_prompt=system_prompt,
        response_type=response_type,
        callbacks=callbacks,
    )
