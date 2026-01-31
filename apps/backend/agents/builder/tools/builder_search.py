"""
Search tools for the Builder Agent. Uses Postgres (BuilderProfileRepository, BuilderServiceRepository); IDs are UUID strings.
Tools return JSON strings so ToolMessage content is valid JSON for the agent.
"""
import asyncio
import json
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

from common.db import get_db_session_ctx
from common.repositories.builder_profile_repository import BuilderProfileRepository
from common.repositories.builder_service_repository import BuilderServiceRepository
from services.embeddings.service import embed_text
from services.vector_search.qdrant_service import search_builder_profiles, search_builder_services


async def _search_async(
    query: str,
    collection_name: str,
    k: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Vector search via Qdrant; fetch full docs from Postgres by UUID."""
    try:
        if not query:
            return {"success": True, "query": query, "results": [], "count": 0}
        query_vec = embed_text(query)
        if collection_name == "builder_profiles":
            qdrant_results = await search_builder_profiles(
                query_vector=query_vec,
                limit=k,
                filters=None,
            )
        elif collection_name == "builder_services":
            qdrant_results = await search_builder_services(
                query_vector=query_vec,
                limit=k,
                filters=None,
            )
        else:
            return {"success": False, "error": f"Unknown collection: {collection_name}", "query": query, "results": [], "count": 0}
        if not qdrant_results:
            return {"success": True, "query": query, "results": [], "count": 0}
        doc_ids = [r["id"] for r in qdrant_results if r.get("id")]
        async with get_db_session_ctx() as session:
            if collection_name == "builder_profiles":
                repo = BuilderProfileRepository(session)
                docs = await repo.list_by_ids(doc_ids)
            else:
                repo = BuilderServiceRepository(session)
                docs = await repo.list_by_ids(doc_ids)
        score_map = {r["id"]: r["score"] for r in qdrant_results}
        results = []
        for doc in docs:
            doc_id = doc.get("id") or doc.get("_id")
            if doc_id in score_map:
                doc["_id"] = doc_id
                doc["score"] = score_map[doc_id]
                if doc.get("builder_id") is not None:
                    doc["builder_id"] = str(doc["builder_id"])
                results.append(doc)
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        if collection_name == "builder_services":
            try:
                import json
                print("--- [Builder Search Tool] Services payload ---")
                print(json.dumps({"query": query, "count": len(results), "results": results}, ensure_ascii=False, indent=2)[:8000])
            except Exception:
                pass
        print(f"[DEBUG] Search completed: {len(results)} results for query '{query}' with filters: {filters}")
        # Short summary for LLM to avoid token limit; full results go in state for API
        lines = []
        for i, r in enumerate(results[:8], 1):
            name = (r.get("company_name") or r.get("service_name") or r.get("title") or "Item")[:40]
            city = (r.get("city") or (r.get("location") or {}).get("city") or "")[:25]
            lines.append(f"{i}. {name} - {city}")
        summary_for_llm = ("Found {} results:\n".format(len(results)) + "\n".join(lines)) if results else "No results found."
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "summary_for_llm": summary_for_llm,
        }
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "count": 0,
            "summary_for_llm": f"Search failed: {e}. Please try again.",
        }


def _run_async_search(search_coro):
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, search_coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(search_coro)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "count": 0,
            "summary_for_llm": f"Search failed: {e}. Please try again.",
        }


def _builder_profile_search_impl(query: str, filters: Optional[Dict[str, Any]] = None) -> str:
    """Returns JSON string so ToolMessage content is valid JSON."""
    search_coro = _search_async(
        query,
        collection_name="builder_profiles",
        k=5,
        filters=filters,
    )
    result = _run_async_search(search_coro)
    return json.dumps(result, default=str)


@tool
def builder_profile_search_tool(query: str) -> str:
    """
    Searches for builder profiles based on a natural language query.
    Use this to find builders, construction companies, or contractors.
    """
    filters = None
    try:
        from .filter_extractor import extract_builder_filters
        filters = extract_builder_filters(query)
    except Exception as e:
        print(f"Filter extraction failed (continuing without filters): {e}")
    return _builder_profile_search_impl(query, filters)


def _builder_service_search_impl(query: str, filters: Optional[Dict[str, Any]] = None) -> str:
    """Returns JSON string so ToolMessage content is valid JSON."""
    search_coro = _search_async(
        query,
        collection_name="builder_services",
        k=5,
        filters=filters,
    )
    result = _run_async_search(search_coro)
    return json.dumps(result, default=str)


@tool
def builder_service_search_tool(query: str) -> str:
    """
    Searches for specific services offered by builders.
    Use this to find services like 'kitchen remodeling', 'roof repair', or 'new home construction'.
    """
    filters = None
    try:
        from .filter_extractor import extract_service_filters
        filters = extract_service_filters(query)
    except Exception as e:
        print(f"Filter extraction failed (continuing without filters): {e}")
    return _builder_service_search_impl(query, filters)
