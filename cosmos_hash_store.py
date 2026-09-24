import os
from datetime import datetime, timezone
from typing import Any

from azure.cosmos import CosmosClient, ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


load_dotenv()


class CosmosHashStore:
    """
    Persistent storage for message, attachment, and PDF-page hashes.

    Expected Cosmos container partition key:
        /id

    The SHA-256 hash is used as both:
        id
        partition key

    This allows fast point reads when checking for duplicates.
    """

    def __init__(
    self,
    client: CosmosClient,
    container: ContainerProxy,
) -> None:
    self.client = client
    self.container = container

    @classmethod
    def from_env(cls) -> "CosmosHashStore":
        endpoint = os.getenv("COSMOS_ENDPOINT")
        key = os.getenv("COSMOS_KEY")
        database_name = os.getenv(
            "COSMOS_DATABASE",
            "timesheet-processor",
        )
        container_name = os.getenv(
            "COSMOS_HASH_CONTAINER",
            "processed-hashes",
        )

        if not endpoint:
            raise ValueError(
                "COSMOS_ENDPOINT environment variable is required."
            )

        # For local development we can use an account key.
        # In Azure, DefaultAzureCredential can use Managed Identity.
        credential = (
            key
            if key
            else DefaultAzureCredential()
        )

        client = CosmosClient(
            endpoint,
            credential=credential,
        )

        database = client.get_database_client(
            database_name
        )

        container = database.get_container_client(
            container_name
        )

        return cls(
            client=client,
            container=container,
        )

    def hash_exists(
        self,
        hash_value: str,
    ) -> bool:
        """
        Return True if a successfully processed hash
        already exists in Cosmos DB.
        """

        if not hash_value:
            raise ValueError(
                "hash_value cannot be empty."
            )

        try:
            self.container.read_item(
                item=hash_value,
                partition_key=hash_value,
            )

            return True

        except CosmosResourceNotFoundError:
            return False

    def save_hash(
        self,
        hash_value: str,
        hash_type: str,
        **metadata: Any,
    ) -> dict[str, Any]:
        """
        Save a successfully processed hash.

        IMPORTANT:
        Call this only after the corresponding timesheet
        information has successfully been written to Excel.
        """

        if not hash_value:
            raise ValueError(
                "hash_value cannot be empty."
            )

        if not hash_type:
            raise ValueError(
                "hash_type cannot be empty."
            )

        item = {
            "id": hash_value,
            "hash": hash_value,
            "type": hash_type,
            "status": "excel_saved",
            "processedAt": datetime.now(
                timezone.utc
            ).isoformat(),
            **metadata,
        }

        response = self.container.upsert_item(
    item
)

return dict(response)