# timesheet-processor

AI automation for retrieving and processing consultant timesheets.

## Hashing and Pre-LLM Deduplication

The project includes a pre-LLM hashing pipeline designed to prevent duplicate
timesheets from being processed repeatedly.

### Current flow

1. Receive Microsoft Graph message and attachment data.
2. Create a deterministic hash for the email message.
3. Check whether the message hash already exists in the hash store.
4. Decode attachment Base64 content.
5. Create attachment hashes.
6. Render PDF attachments into individual PNG pages.
7. Create a hash for each PDF page.
8. Skip attachments/pages that were already processed.
9. Send only new content forward as LLM-ready Base64 data.
10. Keep hashes pending until the downstream Excel write succeeds.
11. After Excel succeeds, commit the message, attachment, and page hashes.

### Storage

`CosmosHashStore` provides the production-facing Azure Cosmos DB implementation.

Expected environment variables:

```env
COSMOS_ENDPOINT=
COSMOS_KEY=
COSMOS_DATABASE=timesheet-processor
COSMOS_HASH_CONTAINER=processed-hashes