import asyncio

from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from loguru import logger
from app.config import settings


@tool
async def get_products_tool(query: str) -> str:
    """
    Returns a list of 5 top matched products from the assortment that match the user's query. Used for searching dishes, drinks, snacks, boxes, ingredients, or categories. Do NOT use this function to clarify details about a specific product, its price, weight, or serving count. Form the query only based on categories, ingredients, or general terms like 'set' or 'box'.
    Args:
         query (str): User's request for product search, advice, or recommendation. Examples: 'salads', 'croissants', 'vegetarian', 'available now', 'hot snacks', 'dishes', 'recommend', 'any dishes', 'all dishes', 'suggest boxes'.
    Returns:
         str: most relevant products.
    """

    embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)

    client = QdrantClient(
        url="https://0a87a722-2e15-4fc0-aa39-5c99fc2866ca.us-west-1-0.aws.cloud.qdrant.io:6333",
        api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.DI_UrA1AMY62uHlhTsWxIwhsdtyGU0KU2oiwY5e43Vc",
    )

    vectorstore = QdrantVectorStore(
        client=client,
        collection_name="products",
        embedding=embeddings,
        content_payload_key="content",
        metadata_payload_key="meta",
    )

    # all_items = client.scroll(
    #     collection_name="products",
    #     limit=1000,
    #     with_payload=True,
    #     with_vectors=False,
    #     offset=None,
    # )
    # for i in all_items[0]:
    #     print(i)
    # print(len(all_items[0]))
    # print(all_items)
    SCORE_THRESHOLD = 0.7
    TOP_K = 5
    try:
        docs_and_scores = await vectorstore.asimilarity_search_with_score(
            query=query,
            k=TOP_K,
        )
        result_documents = [
            doc.page_content
            for doc, score in docs_and_scores
            if score is None or score >= SCORE_THRESHOLD
        ]
        if not result_documents:
            return "Error retrieving products: no results found"
        return "\n".join(f"-\n{name}" for name in result_documents)

    except Exception as e:
        logger.warning(f"Failed to retrieve products: {e}")
        return f"Error retrieving products: {e}"


if __name__ == "__main__":
    print(asyncio.run(get_products_tool("соки, напої")))
