# TOOLS

Generated from `src/mcp_langfuse/specs/langfuse-openapi.yml`.

## How To Use These Tools

- Every tool is a 1:1 MCP wrapper around a Langfuse public API operation.
- Path and query parameters are passed as top-level MCP arguments.
- JSON request bodies are passed in a top-level `body` argument.
- Successful calls return structured content shaped like `{ok, tool_name, status_code, content_type, data}`.
- Failed calls return `isError: true` with structured content containing `error`, `message`, and any available Langfuse API details.
- Tool discovery is filtered before `tools/list` is returned, using profiles, family overrides, and explicit tool overrides.

Total tools: 87

## Tool Loading Profiles

- Default profiles: `minimal`
- Safety gates are off by default: write, destructive, admin, and legacy tools must be explicitly enabled.
- Override knobs: `LANGFUSE_TOOL_PROFILES`, `LANGFUSE_TOOL_FAMILIES_ENABLE`, `LANGFUSE_TOOL_FAMILIES_DISABLE`, `LANGFUSE_TOOLS_ENABLE`, and `LANGFUSE_TOOLS_DISABLE`.
- Safety gates: `LANGFUSE_ENABLE_WRITE_TOOLS`, `LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS`, `LANGFUSE_ENABLE_ADMIN_TOOLS`, and `LANGFUSE_ENABLE_LEGACY_TOOLS`.

### `minimal`

- Intent: Small default read-only observability set.
- Families: `Health`, `Trace`, `Observations`, `Sessions`, `Scores`
- Total matching tools: 10

### `observe_read`

- Intent: Broader read-only observability and metrics profile.
- Families: `Health`, `Trace`, `Observations`, `Sessions`, `Scores`, `Metrics`, `Models`
- Total matching tools: 15

### `ingest`

- Intent: Tracing and media ingestion profile.
- Families: `Ingestion`, `Opentelemetry`, `Media`
- Total matching tools: 5

### `evals`

- Intent: Evaluation, annotation, scoring, and prompt review profile.
- Families: `AnnotationQueues`, `Comments`, `ScoreConfigs`, `Scores`, `Prompts`, `PromptVersion`
- Total matching tools: 24

### `datasets`

- Intent: Dataset and run management profile.
- Families: `Datasets`, `DatasetItems`, `DatasetRunItems`
- Total matching tools: 12

### `prompts`

- Intent: Prompt management profile.
- Families: `Prompts`, `PromptVersion`
- Total matching tools: 5

### `project_admin`

- Intent: Project-scoped administration profile.
- Families: `Projects`, `BlobStorageIntegrations`, `LlmConnections`
- Total matching tools: 13

### `org_admin`

- Intent: Organization and SCIM administration profile.
- Families: `Organizations`, `Scim`
- Total matching tools: 15

### `admin`

- Intent: Combined project and organization administration profile.
- Families: `Projects`, `BlobStorageIntegrations`, `LlmConnections`, `Organizations`, `Scim`
- Total matching tools: 28

### `legacy`

- Intent: Legacy Langfuse API compatibility profile.
- Families: `LegacyMetricsV1`, `LegacyObservationsV1`, `LegacyScoreV1`
- Total matching tools: 5

### `full`

- Intent: All current Langfuse public API families.
- Families: `AnnotationQueues`, `BlobStorageIntegrations`, `Comments`, `DatasetItems`, `DatasetRunItems`, `Datasets`, `Health`, `Ingestion`, `LegacyMetricsV1`, `LegacyObservationsV1`, `LegacyScoreV1`, `LlmConnections`, `Media`, `Metrics`, `Models`, `Observations`, `Opentelemetry`, `Organizations`, `Projects`, `PromptVersion`, `Prompts`, `Scim`, `ScoreConfigs`, `Scores`, `Sessions`, `Trace`
- Total matching tools: 87

## Tool Index

### AnnotationQueues
- `langfuse_annotation_queues_create_queue` -> `POST /api/public/annotation-queues`
- `langfuse_annotation_queues_create_queue_assignment` -> `POST /api/public/annotation-queues/{queueId}/assignments`
- `langfuse_annotation_queues_create_queue_item` -> `POST /api/public/annotation-queues/{queueId}/items`
- `langfuse_annotation_queues_delete_queue_assignment` -> `DELETE /api/public/annotation-queues/{queueId}/assignments`
- `langfuse_annotation_queues_delete_queue_item` -> `DELETE /api/public/annotation-queues/{queueId}/items/{itemId}`
- `langfuse_annotation_queues_get_queue` -> `GET /api/public/annotation-queues/{queueId}`
- `langfuse_annotation_queues_get_queue_item` -> `GET /api/public/annotation-queues/{queueId}/items/{itemId}`
- `langfuse_annotation_queues_list_queue_items` -> `GET /api/public/annotation-queues/{queueId}/items`
- `langfuse_annotation_queues_list_queues` -> `GET /api/public/annotation-queues`
- `langfuse_annotation_queues_update_queue_item` -> `PATCH /api/public/annotation-queues/{queueId}/items/{itemId}`

### BlobStorageIntegrations
- `langfuse_blob_storage_integrations_delete_blob_storage_integration` -> `DELETE /api/public/integrations/blob-storage/{id}`
- `langfuse_blob_storage_integrations_get_blob_storage_integration_status` -> `GET /api/public/integrations/blob-storage/{id}`
- `langfuse_blob_storage_integrations_get_blob_storage_integrations` -> `GET /api/public/integrations/blob-storage`
- `langfuse_blob_storage_integrations_upsert_blob_storage_integration` -> `PUT /api/public/integrations/blob-storage`

### Comments
- `langfuse_comments_create` -> `POST /api/public/comments`
- `langfuse_comments_get` -> `GET /api/public/comments`
- `langfuse_comments_get_by_id` -> `GET /api/public/comments/{commentId}`

### DatasetItems
- `langfuse_dataset_items_create` -> `POST /api/public/dataset-items`
- `langfuse_dataset_items_delete` -> `DELETE /api/public/dataset-items/{id}`
- `langfuse_dataset_items_get` -> `GET /api/public/dataset-items/{id}`
- `langfuse_dataset_items_list` -> `GET /api/public/dataset-items`

### DatasetRunItems
- `langfuse_dataset_run_items_create` -> `POST /api/public/dataset-run-items`
- `langfuse_dataset_run_items_list` -> `GET /api/public/dataset-run-items`

### Datasets
- `langfuse_datasets_create` -> `POST /api/public/v2/datasets`
- `langfuse_datasets_delete_run` -> `DELETE /api/public/datasets/{datasetName}/runs/{runName}`
- `langfuse_datasets_get` -> `GET /api/public/v2/datasets/{datasetName}`
- `langfuse_datasets_get_run` -> `GET /api/public/datasets/{datasetName}/runs/{runName}`
- `langfuse_datasets_get_runs` -> `GET /api/public/datasets/{datasetName}/runs`
- `langfuse_datasets_list` -> `GET /api/public/v2/datasets`

### Health
- `langfuse_health_health` -> `GET /api/public/health`

### Ingestion
- `langfuse_ingestion_batch` -> `POST /api/public/ingestion`

### LegacyMetricsV1
- `langfuse_legacy_metrics_v1_metrics` -> `GET /api/public/metrics`

### LegacyObservationsV1
- `langfuse_legacy_observations_v1_get` -> `GET /api/public/observations/{observationId}`
- `langfuse_legacy_observations_v1_get_many` -> `GET /api/public/observations`

### LegacyScoreV1
- `langfuse_legacy_score_v1_create` -> `POST /api/public/scores`
- `langfuse_legacy_score_v1_delete` -> `DELETE /api/public/scores/{scoreId}`

### LlmConnections
- `langfuse_llm_connections_list` -> `GET /api/public/llm-connections`
- `langfuse_llm_connections_upsert` -> `PUT /api/public/llm-connections`

### Media
- `langfuse_media_get` -> `GET /api/public/media/{mediaId}`
- `langfuse_media_get_upload_url` -> `POST /api/public/media`
- `langfuse_media_patch` -> `PATCH /api/public/media/{mediaId}`

### Metrics
- `langfuse_metrics_metrics` -> `GET /api/public/v2/metrics`

### Models
- `langfuse_models_create` -> `POST /api/public/models`
- `langfuse_models_delete` -> `DELETE /api/public/models/{id}`
- `langfuse_models_get` -> `GET /api/public/models/{id}`
- `langfuse_models_list` -> `GET /api/public/models`

### Observations
- `langfuse_observations_get_many` -> `GET /api/public/v2/observations`

### Opentelemetry
- `langfuse_opentelemetry_export_traces` -> `POST /api/public/otel/v1/traces`

### Organizations
- `langfuse_organizations_delete_organization_membership` -> `DELETE /api/public/organizations/memberships`
- `langfuse_organizations_delete_project_membership` -> `DELETE /api/public/projects/{projectId}/memberships`
- `langfuse_organizations_get_organization_api_keys` -> `GET /api/public/organizations/apiKeys`
- `langfuse_organizations_get_organization_memberships` -> `GET /api/public/organizations/memberships`
- `langfuse_organizations_get_organization_projects` -> `GET /api/public/organizations/projects`
- `langfuse_organizations_get_project_memberships` -> `GET /api/public/projects/{projectId}/memberships`
- `langfuse_organizations_update_organization_membership` -> `PUT /api/public/organizations/memberships`
- `langfuse_organizations_update_project_membership` -> `PUT /api/public/projects/{projectId}/memberships`

### Projects
- `langfuse_projects_create` -> `POST /api/public/projects`
- `langfuse_projects_create_api_key` -> `POST /api/public/projects/{projectId}/apiKeys`
- `langfuse_projects_delete` -> `DELETE /api/public/projects/{projectId}`
- `langfuse_projects_delete_api_key` -> `DELETE /api/public/projects/{projectId}/apiKeys/{apiKeyId}`
- `langfuse_projects_get` -> `GET /api/public/projects`
- `langfuse_projects_get_api_keys` -> `GET /api/public/projects/{projectId}/apiKeys`
- `langfuse_projects_update` -> `PUT /api/public/projects/{projectId}`

### PromptVersion
- `langfuse_prompt_version_update` -> `PATCH /api/public/v2/prompts/{name}/versions/{version}`

### Prompts
- `langfuse_prompts_create` -> `POST /api/public/v2/prompts`
- `langfuse_prompts_delete` -> `DELETE /api/public/v2/prompts/{promptName}`
- `langfuse_prompts_get` -> `GET /api/public/v2/prompts/{promptName}`
- `langfuse_prompts_list` -> `GET /api/public/v2/prompts`

### Scim
- `langfuse_scim_create_user` -> `POST /api/public/scim/Users`
- `langfuse_scim_delete_user` -> `DELETE /api/public/scim/Users/{userId}`
- `langfuse_scim_get_resource_types` -> `GET /api/public/scim/ResourceTypes`
- `langfuse_scim_get_schemas` -> `GET /api/public/scim/Schemas`
- `langfuse_scim_get_service_provider_config` -> `GET /api/public/scim/ServiceProviderConfig`
- `langfuse_scim_get_user` -> `GET /api/public/scim/Users/{userId}`
- `langfuse_scim_list_users` -> `GET /api/public/scim/Users`

### ScoreConfigs
- `langfuse_score_configs_create` -> `POST /api/public/score-configs`
- `langfuse_score_configs_get` -> `GET /api/public/score-configs`
- `langfuse_score_configs_get_by_id` -> `GET /api/public/score-configs/{configId}`
- `langfuse_score_configs_update` -> `PATCH /api/public/score-configs/{configId}`

### Scores
- `langfuse_scores_get_by_id` -> `GET /api/public/v2/scores/{scoreId}`
- `langfuse_scores_get_many` -> `GET /api/public/v2/scores`

### Sessions
- `langfuse_sessions_get` -> `GET /api/public/sessions/{sessionId}`
- `langfuse_sessions_list` -> `GET /api/public/sessions`

### Trace
- `langfuse_trace_delete` -> `DELETE /api/public/traces/{traceId}`
- `langfuse_trace_delete_multiple` -> `DELETE /api/public/traces`
- `langfuse_trace_get` -> `GET /api/public/traces/{traceId}`
- `langfuse_trace_list` -> `GET /api/public/traces`

## Tool Details

### AnnotationQueues

#### `langfuse_annotation_queues_create_queue`

- Intent: Create an annotation queue
- Langfuse operation: `annotationQueues_createQueue`
- HTTP: `POST /api/public/annotation-queues`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={name*:string, description:string | null, scoreConfigIds*:array}. No description provided.
- Usage example:
```json
{
  "body": {
    "name": "string",
    "scoreConfigIds": [
      "<value>"
    ]
  }
}
```

#### `langfuse_annotation_queues_create_queue_assignment`

- Intent: Create an assignment for a user to an annotation queue
- Langfuse operation: `annotationQueues_createQueueAssignment`
- HTTP: `POST /api/public/annotation-queues/{queueId}/assignments`
- Parameters:
- `queueId`: required; source=`path`; schema=string. The unique identifier of the annotation queue
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={userId*:string}. No description provided.
- Usage example:
```json
{
  "body": {
    "userId": "string"
  },
  "queueId": "string"
}
```

#### `langfuse_annotation_queues_create_queue_item`

- Intent: Add an item to an annotation queue
- Langfuse operation: `annotationQueues_createQueueItem`
- HTTP: `POST /api/public/annotation-queues/{queueId}/items`
- Parameters:
- `queueId`: required; source=`path`; schema=string. The unique identifier of the annotation queue
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={objectId*:string, objectType*:string, status:string | null}. No description provided.
- Usage example:
```json
{
  "body": {
    "objectId": "string",
    "objectType": "TRACE"
  },
  "queueId": "string"
}
```

#### `langfuse_annotation_queues_delete_queue_assignment`

- Intent: Delete an assignment for a user to an annotation queue
- Langfuse operation: `annotationQueues_deleteQueueAssignment`
- HTTP: `DELETE /api/public/annotation-queues/{queueId}/assignments`
- Parameters:
- `queueId`: required; source=`path`; schema=string. The unique identifier of the annotation queue
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={userId*:string}. No description provided.
- Usage example:
```json
{
  "body": {
    "userId": "string"
  },
  "queueId": "string"
}
```

#### `langfuse_annotation_queues_delete_queue_item`

- Intent: Remove an item from an annotation queue
- Langfuse operation: `annotationQueues_deleteQueueItem`
- HTTP: `DELETE /api/public/annotation-queues/{queueId}/items/{itemId}`
- Parameters:
- `queueId`: required; source=`path`; schema=string. The unique identifier of the annotation queue
- `itemId`: required; source=`path`; schema=string. The unique identifier of the annotation queue item
- Usage example:
```json
{
  "itemId": "string",
  "queueId": "string"
}
```

#### `langfuse_annotation_queues_get_queue`

- Intent: Get an annotation queue by ID
- Langfuse operation: `annotationQueues_getQueue`
- HTTP: `GET /api/public/annotation-queues/{queueId}`
- Parameters:
- `queueId`: required; source=`path`; schema=string. The unique identifier of the annotation queue
- Usage example:
```json
{
  "queueId": "string"
}
```

#### `langfuse_annotation_queues_get_queue_item`

- Intent: Get a specific item from an annotation queue
- Langfuse operation: `annotationQueues_getQueueItem`
- HTTP: `GET /api/public/annotation-queues/{queueId}/items/{itemId}`
- Parameters:
- `queueId`: required; source=`path`; schema=string. The unique identifier of the annotation queue
- `itemId`: required; source=`path`; schema=string. The unique identifier of the annotation queue item
- Usage example:
```json
{
  "itemId": "string",
  "queueId": "string"
}
```

#### `langfuse_annotation_queues_list_queue_items`

- Intent: Get items for a specific annotation queue
- Langfuse operation: `annotationQueues_listQueueItems`
- HTTP: `GET /api/public/annotation-queues/{queueId}/items`
- Parameters:
- `queueId`: required; source=`path`; schema=string. The unique identifier of the annotation queue
- `status`: optional; source=`query`; schema=string | null, enum=["PENDING", "COMPLETED", null]. Filter by status
- `page`: optional; source=`query`; schema=integer | null. page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. limit of items per page
- Usage example:
```json
{
  "queueId": "string"
}
```

#### `langfuse_annotation_queues_list_queues`

- Intent: Get all annotation queues
- Langfuse operation: `annotationQueues_listQueues`
- HTTP: `GET /api/public/annotation-queues`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. limit of items per page
- Usage example:
```json
{}
```

#### `langfuse_annotation_queues_update_queue_item`

- Intent: Update an annotation queue item
- Langfuse operation: `annotationQueues_updateQueueItem`
- HTTP: `PATCH /api/public/annotation-queues/{queueId}/items/{itemId}`
- Parameters:
- `queueId`: required; source=`path`; schema=string. The unique identifier of the annotation queue
- `itemId`: required; source=`path`; schema=string. The unique identifier of the annotation queue item
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={status:string | null}. No description provided.
- Usage example:
```json
{
  "body": {},
  "itemId": "string",
  "queueId": "string"
}
```

### BlobStorageIntegrations

#### `langfuse_blob_storage_integrations_delete_blob_storage_integration`

- Intent: Delete a blob storage integration by ID (requires organization-scoped API key)
- Langfuse operation: `blobStorageIntegrations_deleteBlobStorageIntegration`
- HTTP: `DELETE /api/public/integrations/blob-storage/{id}`
- Parameters:
- `id`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "id": "string"
}
```

#### `langfuse_blob_storage_integrations_get_blob_storage_integration_status`

- Intent: Get the sync status of a blob storage integration by integration ID (requires organization-scoped API key)
- Langfuse operation: `blobStorageIntegrations_getBlobStorageIntegrationStatus`
- HTTP: `GET /api/public/integrations/blob-storage/{id}`
- Parameters:
- `id`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "id": "string"
}
```

#### `langfuse_blob_storage_integrations_get_blob_storage_integrations`

- Intent: Get all blob storage integrations for the organization (requires organization-scoped API key)
- Langfuse operation: `blobStorageIntegrations_getBlobStorageIntegrations`
- HTTP: `GET /api/public/integrations/blob-storage`
- Parameters:
- None.
- Usage example:
```json
{}
```

#### `langfuse_blob_storage_integrations_upsert_blob_storage_integration`

- Intent: Create or update a blob storage integration for a specific project (requires organization-scoped API key). The configuration is validated by performing a test upload to the bucket.
- Langfuse operation: `blobStorageIntegrations_upsertBlobStorageIntegration`
- HTTP: `PUT /api/public/integrations/blob-storage`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={projectId*:string, type*:string, bucketName*:string, endpoint:string | null, region*:string, accessKeyId:string | null, ...}. No description provided.
- Usage example:
```json
{
  "body": {
    "bucketName": "string",
    "enabled": false,
    "exportFrequency": "hourly",
    "exportMode": "FULL_HISTORY",
    "fileType": "JSON",
    "forcePathStyle": false,
    "projectId": "string",
    "region": "string",
    "type": "S3"
  }
}
```

### Comments

#### `langfuse_comments_create`

- Intent: Create a comment. Comments may be attached to different object types (trace, observation, session, prompt).
- Langfuse operation: `comments_create`
- HTTP: `POST /api/public/comments`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={projectId*:string, objectType*:string, objectId*:string, content*:string, authorUserId:string | null}. No description provided.
- Usage example:
```json
{
  "body": {
    "content": "string",
    "objectId": "string",
    "objectType": "string",
    "projectId": "string"
  }
}
```

#### `langfuse_comments_get`

- Intent: Get all comments
- Langfuse operation: `comments_get`
- HTTP: `GET /api/public/comments`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. Page number, starts at 1.
- `limit`: optional; source=`query`; schema=integer | null. Limit of items per page. If you encounter api issues due to too large page sizes, try to reduce the limit
- `objectType`: optional; source=`query`; schema=string | null. Filter comments by object type (trace, observation, session, prompt).
- `objectId`: optional; source=`query`; schema=string | null. Filter comments by object id. If objectType is not provided, an error will be thrown.
- `authorUserId`: optional; source=`query`; schema=string | null. Filter comments by author user id.
- Usage example:
```json
{}
```

#### `langfuse_comments_get_by_id`

- Intent: Get a comment by id
- Langfuse operation: `comments_get-by-id`
- HTTP: `GET /api/public/comments/{commentId}`
- Parameters:
- `commentId`: required; source=`path`; schema=string. The unique langfuse identifier of a comment
- Usage example:
```json
{
  "commentId": "string"
}
```

### DatasetItems

#### `langfuse_dataset_items_create`

- Intent: Create a dataset item
- Langfuse operation: `datasetItems_create`
- HTTP: `POST /api/public/dataset-items`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={datasetName*:string, input:object | null, expectedOutput:object | null, metadata:object | null, sourceTraceId:string | null, sourceObservationId:string | null, ...}. No description provided.
- Usage example:
```json
{
  "body": {
    "datasetName": "string"
  }
}
```

#### `langfuse_dataset_items_delete`

- Intent: Delete a dataset item and all its run items. This action is irreversible.
- Langfuse operation: `datasetItems_delete`
- HTTP: `DELETE /api/public/dataset-items/{id}`
- Parameters:
- `id`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "id": "string"
}
```

#### `langfuse_dataset_items_get`

- Intent: Get a dataset item
- Langfuse operation: `datasetItems_get`
- HTTP: `GET /api/public/dataset-items/{id}`
- Parameters:
- `id`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "id": "string"
}
```

#### `langfuse_dataset_items_list`

- Intent: Get dataset items. Optionally specify a version to get the items as they existed at that point in time.
Note: If version parameter is provided, datasetName must also be provided.
- Langfuse operation: `datasetItems_list`
- HTTP: `GET /api/public/dataset-items`
- Parameters:
- `datasetName`: optional; source=`query`; schema=string | null. No description provided.
- `sourceTraceId`: optional; source=`query`; schema=string | null. No description provided.
- `sourceObservationId`: optional; source=`query`; schema=string | null. No description provided.
- `version`: optional; source=`query`; schema=string | null, format=date-time. ISO 8601 timestamp (RFC 3339, Section 5.6) in UTC (e.g., "2026-01-21T14:35:42Z").
If provided, returns state of dataset at this timestamp.
If not provided, returns the latest version. Requires datasetName to be specified.
- `page`: optional; source=`query`; schema=integer | null. page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. limit of items per page
- Usage example:
```json
{}
```

### DatasetRunItems

#### `langfuse_dataset_run_items_create`

- Intent: Create a dataset run item
- Langfuse operation: `datasetRunItems_create`
- HTTP: `POST /api/public/dataset-run-items`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={runName*:string, runDescription:string | null, metadata:anyOf, datasetItemId*:string, observationId:string | null, traceId:string | null, ...}. No description provided.
- Usage example:
```json
{
  "body": {
    "datasetItemId": "string",
    "runName": "string"
  }
}
```

#### `langfuse_dataset_run_items_list`

- Intent: List dataset run items
- Langfuse operation: `datasetRunItems_list`
- HTTP: `GET /api/public/dataset-run-items`
- Parameters:
- `datasetId`: required; source=`query`; schema=string. No description provided.
- `runName`: required; source=`query`; schema=string. No description provided.
- `page`: optional; source=`query`; schema=integer | null. page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. limit of items per page
- Usage example:
```json
{
  "datasetId": "string",
  "runName": "string"
}
```

### Datasets

#### `langfuse_datasets_create`

- Intent: Create a dataset
- Langfuse operation: `datasets_create`
- HTTP: `POST /api/public/v2/datasets`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={name*:string, description:string | null, metadata:object | null, inputSchema:anyOf, expectedOutputSchema:anyOf}. No description provided.
- Usage example:
```json
{
  "body": {
    "name": "string"
  }
}
```

#### `langfuse_datasets_delete_run`

- Intent: Delete a dataset run and all its run items. This action is irreversible.
- Langfuse operation: `datasets_deleteRun`
- HTTP: `DELETE /api/public/datasets/{datasetName}/runs/{runName}`
- Parameters:
- `datasetName`: required; source=`path`; schema=string. No description provided.
- `runName`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "datasetName": "string",
  "runName": "string"
}
```

#### `langfuse_datasets_get`

- Intent: Get a dataset
- Langfuse operation: `datasets_get`
- HTTP: `GET /api/public/v2/datasets/{datasetName}`
- Parameters:
- `datasetName`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "datasetName": "string"
}
```

#### `langfuse_datasets_get_run`

- Intent: Get a dataset run and its items
- Langfuse operation: `datasets_getRun`
- HTTP: `GET /api/public/datasets/{datasetName}/runs/{runName}`
- Parameters:
- `datasetName`: required; source=`path`; schema=string. No description provided.
- `runName`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "datasetName": "string",
  "runName": "string"
}
```

#### `langfuse_datasets_get_runs`

- Intent: Get dataset runs
- Langfuse operation: `datasets_getRuns`
- HTTP: `GET /api/public/datasets/{datasetName}/runs`
- Parameters:
- `datasetName`: required; source=`path`; schema=string. No description provided.
- `page`: optional; source=`query`; schema=integer | null. page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. limit of items per page
- Usage example:
```json
{
  "datasetName": "string"
}
```

#### `langfuse_datasets_list`

- Intent: Get all datasets
- Langfuse operation: `datasets_list`
- HTTP: `GET /api/public/v2/datasets`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. limit of items per page
- Usage example:
```json
{}
```

### Health

#### `langfuse_health_health`

- Intent: Check health of API and database
- Langfuse operation: `health_health`
- HTTP: `GET /api/public/health`
- Parameters:
- None.
- Usage example:
```json
{}
```

### Ingestion

#### `langfuse_ingestion_batch`

- Intent: **Legacy endpoint for batch ingestion for Langfuse Observability.**

-> Please use the OpenTelemetry endpoint (`/api/public/otel/v1/traces`). Learn more: https://langfuse.com/integrations/native/opentelemetry

Within each batch, there can be multiple events.
Each event has a type, an id, a timestamp, metadata and a body.
Internally, we refer to this as the "event envelope" as it tells us something about the event but not the trace.
We use the event id within this envelope to deduplicate messages to avoid processing the same event twice, i.e. the event id should be unique per request.
The event.body.id is the ID of the actual trace and will be used for updates and will be visible within the Langfuse App.
I.e. if you want to update a trace, you'd use the same body id, but separate event IDs.

Notes:
- Introduction to data model: https://langfuse.com/docs/observability/data-model
- Batch sizes are limited to 3.5 MB in total. You need to adjust the number of events per batch accordingly.
- The API does not return a 4xx status code for input errors. Instead, it responds with a 207 status code, which includes a list of the encountered errors.
- Langfuse operation: `ingestion_batch`
- HTTP: `POST /api/public/ingestion`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={batch*:array, metadata:anyOf}. No description provided.
- Usage example:
```json
{
  "body": {
    "batch": [
      "<value>"
    ]
  }
}
```

### LegacyMetricsV1

#### `langfuse_legacy_metrics_v1_metrics`

- Intent: Get metrics from the Langfuse project using a query object.

Consider using the [v2 metrics endpoint](/api-reference#tag/metricsv2/GET/api/public/v2/metrics) for better performance.

For more details, see the [Metrics API documentation](https://langfuse.com/docs/metrics/features/metrics-api).
- Langfuse operation: `legacy_metricsV1_metrics`
- HTTP: `GET /api/public/metrics`
- Parameters:
- `query`: required; source=`query`; schema=string. JSON string containing the query parameters with the following structure:
```json
{
  "view": string,           // Required. One of "traces", "observations", "scores-numeric", "scores-categorical"
  "dimensions": [           // Optional. Default: []
    {
      "field": string       // Field to group by, e.g. "name", "userId", "sessionId"
    }
  ],
  "metrics": [              // Required. At least one metric must be provided
    {
      "measure": string,    // What to measure, e.g. "count", "latency", "value"
      "aggregation": string // How to aggregate, e.g. "count", "sum", "avg", "p95", "histogram"
    }
  ],
  "filters": [              // Optional. Default: []
    {
      "column": string,     // Column to filter on
      "operator": string,   // Operator, e.g. "=", ">", "<", "contains"
      "value": any,         // Value to compare against
      "type": string,       // Data type, e.g. "string", "number", "stringObject"
      "key": string         // Required only when filtering on metadata
    }
  ],
  "timeDimension": {        // Optional. Default: null. If provided, results will be grouped by time
    "granularity": string   // One of "minute", "hour", "day", "week", "month", "auto"
  },
  "fromTimestamp": string,  // Required. ISO datetime string for start of time range
  "toTimestamp": string,    // Required. ISO datetime string for end of time range
  "orderBy": [              // Optional. Default: null
    {
      "field": string,      // Field to order by
      "direction": string   // "asc" or "desc"
    }
  ],
  "config": {               // Optional. Query-specific configuration
    "bins": number,         // Optional. Number of bins for histogram (1-100), default: 10
    "row_limit": number     // Optional. Row limit for results (1-1000)
  }
}
```
- Usage example:
```json
{
  "query": "string"
}
```

### LegacyObservationsV1

#### `langfuse_legacy_observations_v1_get`

- Intent: Get a observation
- Langfuse operation: `legacy_observationsV1_get`
- HTTP: `GET /api/public/observations/{observationId}`
- Parameters:
- `observationId`: required; source=`path`; schema=string. The unique langfuse identifier of an observation, can be an event, span or generation
- Usage example:
```json
{
  "observationId": "string"
}
```

#### `langfuse_legacy_observations_v1_get_many`

- Intent: Get a list of observations.

Consider using the [v2 observations endpoint](/api-reference#tag/observationsv2/GET/api/public/v2/observations) for cursor-based pagination and field selection.
- Langfuse operation: `legacy_observationsV1_getMany`
- HTTP: `GET /api/public/observations`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. Page number, starts at 1.
- `limit`: optional; source=`query`; schema=integer | null. Limit of items per page. If you encounter api issues due to too large page sizes, try to reduce the limit.
- `name`: optional; source=`query`; schema=string | null. No description provided.
- `userId`: optional; source=`query`; schema=string | null. No description provided.
- `type`: optional; source=`query`; schema=string | null. No description provided.
- `traceId`: optional; source=`query`; schema=string | null. No description provided.
- `level`: optional; source=`query`; schema=string | null, enum=["DEBUG", "DEFAULT", "WARNING", "ERROR", null]. Optional filter for observations with a specific level (e.g. "DEBUG", "DEFAULT", "WARNING", "ERROR").
- `parentObservationId`: optional; source=`query`; schema=string | null. No description provided.
- `environment`: optional; source=`query`; schema=array, items=string | null. Optional filter for observations where the environment is one of the provided values.
- `fromStartTime`: optional; source=`query`; schema=string | null, format=date-time. Retrieve only observations with a start_time on or after this datetime (ISO 8601).
- `toStartTime`: optional; source=`query`; schema=string | null, format=date-time. Retrieve only observations with a start_time before this datetime (ISO 8601).
- `version`: optional; source=`query`; schema=string | null. Optional filter to only include observations with a certain version.
- `filter`: optional; source=`query`; schema=string | null. JSON string containing an array of filter conditions. When provided, this takes precedence over query parameter filters (userId, name, type, level, environment, fromStartTime, ...).

## Filter Structure
Each filter condition has the following structure:
```json
[
  {
    "type": string,           // Required. One of: "datetime", "string", "number", "stringOptions", "categoryOptions", "arrayOptions", "stringObject", "numberObject", "boolean", "null"
    "column": string,         // Required. Column to filter on (see available columns below)
    "operator": string,       // Required. Operator based on type:
                              // - datetime: ">", "<", ">=", "<="
                              // - string: "=", "contains", "does not contain", "starts with", "ends with"
                              // - stringOptions: "any of", "none of"
                              // - categoryOptions: "any of", "none of"
                              // - arrayOptions: "any of", "none of", "all of"
                              // - number: "=", ">", "<", ">=", "<="
                              // - stringObject: "=", "contains", "does not contain", "starts with", "ends with"
                              // - numberObject: "=", ">", "<", ">=", "<="
                              // - boolean: "=", "<>"
                              // - null: "is null", "is not null"
    "value": any,             // Required (except for null type). Value to compare against. Type depends on filter type
    "key": string             // Required only for stringObject, numberObject, and categoryOptions types when filtering on nested fields like metadata
  }
]
```

## Available Columns

### Core Observation Fields
- `id` (string) - Observation ID
- `type` (string) - Observation type (SPAN, GENERATION, EVENT)
- `name` (string) - Observation name
- `traceId` (string) - Associated trace ID
- `startTime` (datetime) - Observation start time
- `endTime` (datetime) - Observation end time
- `environment` (string) - Environment tag
- `level` (string) - Log level (DEBUG, DEFAULT, WARNING, ERROR)
- `statusMessage` (string) - Status message
- `version` (string) - Version tag

### Performance Metrics
- `latency` (number) - Latency in seconds (calculated: end_time - start_time)
- `timeToFirstToken` (number) - Time to first token in seconds
- `tokensPerSecond` (number) - Output tokens per second

### Token Usage
- `inputTokens` (number) - Number of input tokens
- `outputTokens` (number) - Number of output tokens
- `totalTokens` (number) - Total tokens (alias: `tokens`)

### Cost Metrics
- `inputCost` (number) - Input cost in USD
- `outputCost` (number) - Output cost in USD
- `totalCost` (number) - Total cost in USD

### Model Information
- `model` (string) - Provided model name
- `promptName` (string) - Associated prompt name
- `promptVersion` (number) - Associated prompt version

### Structured Data
- `metadata` (stringObject/numberObject/categoryOptions) - Metadata key-value pairs. Use `key` parameter to filter on specific metadata keys.

### Associated Trace Fields (requires join with traces table)
- `userId` (string) - User ID from associated trace
- `traceName` (string) - Name from associated trace
- `traceEnvironment` (string) - Environment from associated trace
- `traceTags` (arrayOptions) - Tags from associated trace

## Filter Examples
```json
[
  {
    "type": "string",
    "column": "type",
    "operator": "=",
    "value": "GENERATION"
  },
  {
    "type": "number",
    "column": "latency",
    "operator": ">=",
    "value": 2.5
  },
  {
    "type": "stringObject",
    "column": "metadata",
    "key": "environment",
    "operator": "=",
    "value": "production"
  }
]
```
- Usage example:
```json
{}
```

### LegacyScoreV1

#### `langfuse_legacy_score_v1_create`

- Intent: Create a score (supports both trace and session scores)
- Langfuse operation: `legacy_scoreV1_create`
- HTTP: `POST /api/public/scores`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={id:string | null, traceId:string | null, sessionId:string | null, observationId:string | null, datasetRunId:string | null, name*:string, ...}. No description provided.
- Usage example:
```json
{
  "body": {
    "name": "string",
    "value": "<value>"
  }
}
```

#### `langfuse_legacy_score_v1_delete`

- Intent: Delete a score (supports both trace and session scores)
- Langfuse operation: `legacy_scoreV1_delete`
- HTTP: `DELETE /api/public/scores/{scoreId}`
- Parameters:
- `scoreId`: required; source=`path`; schema=string. The unique langfuse identifier of a score
- Usage example:
```json
{
  "scoreId": "string"
}
```

### LlmConnections

#### `langfuse_llm_connections_list`

- Intent: Get all LLM connections in a project
- Langfuse operation: `llmConnections_list`
- HTTP: `GET /api/public/llm-connections`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. limit of items per page
- Usage example:
```json
{}
```

#### `langfuse_llm_connections_upsert`

- Intent: Create or update an LLM connection. The connection is upserted on provider.
- Langfuse operation: `llmConnections_upsert`
- HTTP: `PUT /api/public/llm-connections`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={provider*:string, adapter*:string, secretKey*:string, baseURL:string | null, customModels:array | null, withDefaultModels:boolean | null, ...}. No description provided.
- Usage example:
```json
{
  "body": {
    "adapter": "anthropic",
    "provider": "string",
    "secretKey": "string"
  }
}
```

### Media

#### `langfuse_media_get`

- Intent: Get a media record
- Langfuse operation: `media_get`
- HTTP: `GET /api/public/media/{mediaId}`
- Parameters:
- `mediaId`: required; source=`path`; schema=string. The unique langfuse identifier of a media record
- Usage example:
```json
{
  "mediaId": "string"
}
```

#### `langfuse_media_get_upload_url`

- Intent: Get a presigned upload URL for a media record
- Langfuse operation: `media_getUploadUrl`
- HTTP: `POST /api/public/media`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={traceId*:string, observationId:string | null, contentType*:string, contentLength*:integer, sha256Hash*:string, field*:string}. No description provided.
- Usage example:
```json
{
  "body": {
    "contentLength": 0,
    "contentType": "image/png",
    "field": "string",
    "sha256Hash": "string",
    "traceId": "string"
  }
}
```

#### `langfuse_media_patch`

- Intent: Patch a media record
- Langfuse operation: `media_patch`
- HTTP: `PATCH /api/public/media/{mediaId}`
- Parameters:
- `mediaId`: required; source=`path`; schema=string. The unique langfuse identifier of a media record
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={uploadedAt*:string, uploadHttpStatus*:integer, uploadHttpError:string | null, uploadTimeMs:integer | null}. No description provided.
- Usage example:
```json
{
  "body": {
    "uploadHttpStatus": 0,
    "uploadedAt": "date-time"
  },
  "mediaId": "string"
}
```

### Metrics

#### `langfuse_metrics_metrics`

- Intent: Get metrics from the Langfuse project using a query object. V2 endpoint with optimized performance.

## V2 Differences
- Supports `observations`, `scores-numeric`, and `scores-categorical` views only (traces view not supported)
- Direct access to tags and release fields on observations
- Backwards-compatible: traceName, traceRelease, traceVersion dimensions are still available on observations view
- High cardinality dimensions are not supported and will return a 400 error (see below)

For more details, see the [Metrics API documentation](https://langfuse.com/docs/metrics/features/metrics-api).

## Available Views

### observations
Query observation-level data (spans, generations, events).

**Dimensions:**
- `environment` - Deployment environment (e.g., production, staging)
- `type` - Type of observation (SPAN, GENERATION, EVENT)
- `name` - Name of the observation
- `level` - Logging level of the observation
- `version` - Version of the observation
- `tags` - User-defined tags
- `release` - Release version
- `traceName` - Name of the parent trace (backwards-compatible)
- `traceRelease` - Release version of the parent trace (backwards-compatible, maps to release)
- `traceVersion` - Version of the parent trace (backwards-compatible, maps to version)
- `providedModelName` - Name of the model used
- `promptName` - Name of the prompt used
- `promptVersion` - Version of the prompt used
- `startTimeMonth` - Month of start_time in YYYY-MM format

**Measures:**
- `count` - Total number of observations
- `latency` - Observation latency (milliseconds)
- `streamingLatency` - Generation latency from completion start to end (milliseconds)
- `inputTokens` - Sum of input tokens consumed
- `outputTokens` - Sum of output tokens produced
- `totalTokens` - Sum of all tokens consumed
- `outputTokensPerSecond` - Output tokens per second
- `tokensPerSecond` - Total tokens per second
- `inputCost` - Input cost (USD)
- `outputCost` - Output cost (USD)
- `totalCost` - Total cost (USD)
- `timeToFirstToken` - Time to first token (milliseconds)
- `countScores` - Number of scores attached to the observation

### scores-numeric
Query numeric and boolean score data.

**Dimensions:**
- `environment` - Deployment environment
- `name` - Name of the score (e.g., accuracy, toxicity)
- `source` - Origin of the score (API, ANNOTATION, EVAL)
- `dataType` - Data type (NUMERIC, BOOLEAN)
- `configId` - Identifier of the score config
- `timestampMonth` - Month in YYYY-MM format
- `timestampDay` - Day in YYYY-MM-DD format
- `value` - Numeric value of the score
- `traceName` - Name of the parent trace
- `tags` - Tags
- `traceRelease` - Release version
- `traceVersion` - Version
- `observationName` - Name of the associated observation
- `observationModelName` - Model name of the associated observation
- `observationPromptName` - Prompt name of the associated observation
- `observationPromptVersion` - Prompt version of the associated observation

**Measures:**
- `count` - Total number of scores
- `value` - Score value (for aggregations)

### scores-categorical
Query categorical score data. Same dimensions as scores-numeric except uses `stringValue` instead of `value`.

**Measures:**
- `count` - Total number of scores

## High Cardinality Dimensions
The following dimensions cannot be used as grouping dimensions in v2 metrics API as they can cause performance issues.
Use them in filters instead.

**observations view:**
- `id` - Use traceId filter to narrow down results
- `traceId` - Use traceId filter instead
- `userId` - Use userId filter instead
- `sessionId` - Use sessionId filter instead
- `parentObservationId` - Use parentObservationId filter instead

**scores-numeric / scores-categorical views:**
- `id` - Use specific filters to narrow down results
- `traceId` - Use traceId filter instead
- `userId` - Use userId filter instead
- `sessionId` - Use sessionId filter instead
- `observationId` - Use observationId filter instead

## Aggregations
Available aggregation functions: `sum`, `avg`, `count`, `max`, `min`, `p50`, `p75`, `p90`, `p95`, `p99`, `histogram`

## Time Granularities
Available granularities for timeDimension: `auto`, `minute`, `hour`, `day`, `week`, `month`
- `auto` bins the data into approximately 50 buckets based on the time range
- Langfuse operation: `metrics_metrics`
- HTTP: `GET /api/public/v2/metrics`
- Parameters:
- `query`: required; source=`query`; schema=string. JSON string containing the query parameters with the following structure:
```json
{
  "view": string,           // Required. One of "observations", "scores-numeric", "scores-categorical"
  "dimensions": [           // Optional. Default: []
    {
      "field": string       // Field to group by (see available dimensions above)
    }
  ],
  "metrics": [              // Required. At least one metric must be provided
    {
      "measure": string,    // What to measure (see available measures above)
      "aggregation": string // How to aggregate: "sum", "avg", "count", "max", "min", "p50", "p75", "p90", "p95", "p99", "histogram"
    }
  ],
  "filters": [              // Optional. Default: []
    {
      "column": string,     // Column to filter on (any dimension field)
      "operator": string,   // Operator based on type:
                            // - datetime: ">", "<", ">=", "<="
                            // - string: "=", "contains", "does not contain", "starts with", "ends with"
                            // - stringOptions: "any of", "none of"
                            // - arrayOptions: "any of", "none of", "all of"
                            // - number: "=", ">", "<", ">=", "<="
                            // - stringObject/numberObject: same as string/number with required "key"
                            // - boolean: "=", "<>"
                            // - null: "is null", "is not null"
      "value": any,         // Value to compare against
      "type": string,       // Data type: "datetime", "string", "number", "stringOptions", "categoryOptions", "arrayOptions", "stringObject", "numberObject", "boolean", "null"
      "key": string         // Required only for stringObject/numberObject types (e.g., metadata filtering)
    }
  ],
  "timeDimension": {        // Optional. Default: null. If provided, results will be grouped by time
    "granularity": string   // One of "auto", "minute", "hour", "day", "week", "month"
  },
  "fromTimestamp": string,  // Required. ISO datetime string for start of time range
  "toTimestamp": string,    // Required. ISO datetime string for end of time range (must be after fromTimestamp)
  "orderBy": [              // Optional. Default: null
    {
      "field": string,      // Field to order by (dimension or metric alias)
      "direction": string   // "asc" or "desc"
    }
  ],
  "config": {               // Optional. Query-specific configuration
    "bins": number,         // Optional. Number of bins for histogram aggregation (1-100), default: 10
    "row_limit": number     // Optional. Maximum number of rows to return (1-1000), default: 100
  }
}
```
- Usage example:
```json
{
  "query": "string"
}
```

### Models

#### `langfuse_models_create`

- Intent: Create a model
- Langfuse operation: `models_create`
- HTTP: `POST /api/public/models`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={modelName*:string, matchPattern*:string, startDate:string | null, unit:string | null, inputPrice:number | null, outputPrice:number | null, ...}. No description provided.
- Usage example:
```json
{
  "body": {
    "matchPattern": "string",
    "modelName": "string"
  }
}
```

#### `langfuse_models_delete`

- Intent: Delete a model. Cannot delete models managed by Langfuse. You can create your own definition with the same modelName to override the definition though.
- Langfuse operation: `models_delete`
- HTTP: `DELETE /api/public/models/{id}`
- Parameters:
- `id`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "id": "string"
}
```

#### `langfuse_models_get`

- Intent: Get a model
- Langfuse operation: `models_get`
- HTTP: `GET /api/public/models/{id}`
- Parameters:
- `id`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "id": "string"
}
```

#### `langfuse_models_list`

- Intent: Get all models
- Langfuse operation: `models_list`
- HTTP: `GET /api/public/models`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. limit of items per page
- Usage example:
```json
{}
```

### Observations

#### `langfuse_observations_get_many`

- Intent: Get a list of observations with cursor-based pagination and flexible field selection.

## Cursor-based Pagination
This endpoint uses cursor-based pagination for efficient traversal of large datasets.
The cursor is returned in the response metadata and should be passed in subsequent requests
to retrieve the next page of results.

## Field Selection
Use the `fields` parameter to control which observation fields are returned:
- `core` - Always included: id, traceId, startTime, endTime, projectId, parentObservationId, type
- `basic` - name, level, statusMessage, version, environment, bookmarked, public, userId, sessionId
- `time` - completionStartTime, createdAt, updatedAt
- `io` - input, output
- `metadata` - metadata (truncated to 200 chars by default, use `expandMetadata` to get full values)
- `model` - providedModelName, internalModelId, modelParameters
- `usage` - usageDetails, costDetails, totalCost
- `prompt` - promptId, promptName, promptVersion
- `metrics` - latency, timeToFirstToken

If not specified, `core` and `basic` field groups are returned.

## Filters
Multiple filtering options are available via query parameters or the structured `filter` parameter.
When using the `filter` parameter, it takes precedence over individual query parameter filters.
- Langfuse operation: `observations_getMany`
- HTTP: `GET /api/public/v2/observations`
- Parameters:
- `fields`: optional; source=`query`; schema=string | null. Comma-separated list of field groups to include in the response.
Available groups: core, basic, time, io, metadata, model, usage, prompt, metrics.
If not specified, `core` and `basic` field groups are returned.
Example: "basic,usage,model"
- `expandMetadata`: optional; source=`query`; schema=string | null. Comma-separated list of metadata keys to return non-truncated.
By default, metadata values over 200 characters are truncated.
Use this parameter to retrieve full values for specific keys.
Example: "key1,key2"
- `limit`: optional; source=`query`; schema=integer | null. Number of items to return per page. Maximum 1000, default 50.
- `cursor`: optional; source=`query`; schema=string | null. Base64-encoded cursor for pagination. Use the cursor from the previous response to get the next page.
- `parseIoAsJson`: optional; source=`query`; schema=boolean | null. **Deprecated.** Setting this to `true` will return a 400 error.
Input/output fields are always returned as raw strings.
Remove this parameter or set it to `false`.
- `name`: optional; source=`query`; schema=string | null. No description provided.
- `userId`: optional; source=`query`; schema=string | null. No description provided.
- `type`: optional; source=`query`; schema=string | null. Filter by observation type (e.g., "GENERATION", "SPAN", "EVENT", "AGENT", "TOOL", "CHAIN", "RETRIEVER", "EVALUATOR", "EMBEDDING", "GUARDRAIL")
- `traceId`: optional; source=`query`; schema=string | null. No description provided.
- `level`: optional; source=`query`; schema=string | null, enum=["DEBUG", "DEFAULT", "WARNING", "ERROR", null]. Optional filter for observations with a specific level (e.g. "DEBUG", "DEFAULT", "WARNING", "ERROR").
- `parentObservationId`: optional; source=`query`; schema=string | null. No description provided.
- `environment`: optional; source=`query`; schema=array, items=string | null. Optional filter for observations where the environment is one of the provided values.
- `fromStartTime`: optional; source=`query`; schema=string | null, format=date-time. Retrieve only observations with a start_time on or after this datetime (ISO 8601).
- `toStartTime`: optional; source=`query`; schema=string | null, format=date-time. Retrieve only observations with a start_time before this datetime (ISO 8601).
- `version`: optional; source=`query`; schema=string | null. Optional filter to only include observations with a certain version.
- `filter`: optional; source=`query`; schema=string | null. JSON string containing an array of filter conditions. When provided, this takes precedence over query parameter filters (userId, name, type, level, environment, fromStartTime, ...).

## Filter Structure
Each filter condition has the following structure:
```json
[
  {
    "type": string,           // Required. One of: "datetime", "string", "number", "stringOptions", "categoryOptions", "arrayOptions", "stringObject", "numberObject", "boolean", "null"
    "column": string,         // Required. Column to filter on (see available columns below)
    "operator": string,       // Required. Operator based on type:
                              // - datetime: ">", "<", ">=", "<="
                              // - string: "=", "contains", "does not contain", "starts with", "ends with"
                              // - stringOptions: "any of", "none of"
                              // - categoryOptions: "any of", "none of"
                              // - arrayOptions: "any of", "none of", "all of"
                              // - number: "=", ">", "<", ">=", "<="
                              // - stringObject: "=", "contains", "does not contain", "starts with", "ends with"
                              // - numberObject: "=", ">", "<", ">=", "<="
                              // - boolean: "=", "<>"
                              // - null: "is null", "is not null"
    "value": any,             // Required (except for null type). Value to compare against. Type depends on filter type
    "key": string             // Required only for stringObject, numberObject, and categoryOptions types when filtering on nested fields like metadata
  }
]
```

## Available Columns

### Core Observation Fields
- `id` (string) - Observation ID
- `type` (string) - Observation type (SPAN, GENERATION, EVENT)
- `name` (string) - Observation name
- `traceId` (string) - Associated trace ID
- `startTime` (datetime) - Observation start time
- `endTime` (datetime) - Observation end time
- `environment` (string) - Environment tag
- `level` (string) - Log level (DEBUG, DEFAULT, WARNING, ERROR)
- `statusMessage` (string) - Status message
- `version` (string) - Version tag
- `userId` (string) - User ID
- `sessionId` (string) - Session ID

### Trace-Related Fields
- `traceName` (string) - Name of the parent trace
- `traceTags` (arrayOptions) - Tags from the parent trace
- `tags` (arrayOptions) - Alias for traceTags

### Performance Metrics
- `latency` (number) - Latency in seconds (calculated: end_time - start_time)
- `timeToFirstToken` (number) - Time to first token in seconds
- `tokensPerSecond` (number) - Output tokens per second

### Token Usage
- `inputTokens` (number) - Number of input tokens
- `outputTokens` (number) - Number of output tokens
- `totalTokens` (number) - Total tokens (alias: `tokens`)

### Cost Metrics
- `inputCost` (number) - Input cost in USD
- `outputCost` (number) - Output cost in USD
- `totalCost` (number) - Total cost in USD

### Model Information
- `model` (string) - Provided model name (alias: `providedModelName`)
- `promptName` (string) - Associated prompt name
- `promptVersion` (number) - Associated prompt version

### Structured Data
- `metadata` (stringObject/numberObject/categoryOptions) - Metadata key-value pairs. Use `key` parameter to filter on specific metadata keys.

## Filter Examples
```json
[
  {
    "type": "string",
    "column": "type",
    "operator": "=",
    "value": "GENERATION"
  },
  {
    "type": "number",
    "column": "latency",
    "operator": ">=",
    "value": 2.5
  },
  {
    "type": "stringObject",
    "column": "metadata",
    "key": "environment",
    "operator": "=",
    "value": "production"
  }
]
```
- Usage example:
```json
{}
```

### Opentelemetry

#### `langfuse_opentelemetry_export_traces`

- Intent: **OpenTelemetry Traces Ingestion Endpoint**

This endpoint implements the OTLP/HTTP specification for trace ingestion, providing native OpenTelemetry integration for Langfuse Observability.

**Supported Formats:**
- Binary Protobuf: `Content-Type: application/x-protobuf`
- JSON Protobuf: `Content-Type: application/json`
- Supports gzip compression via `Content-Encoding: gzip` header

**Specification Compliance:**
- Conforms to [OTLP/HTTP Trace Export](https://opentelemetry.io/docs/specs/otlp/#otlphttp)
- Implements `ExportTraceServiceRequest` message format

**Documentation:**
- Integration guide: https://langfuse.com/integrations/native/opentelemetry
- Data model: https://langfuse.com/docs/observability/data-model
- Langfuse operation: `opentelemetry_exportTraces`
- HTTP: `POST /api/public/otel/v1/traces`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={resourceSpans*:array}. No description provided.
- Usage example:
```json
{
  "body": {
    "resourceSpans": [
      "<value>"
    ]
  }
}
```

### Organizations

#### `langfuse_organizations_delete_organization_membership`

- Intent: Delete a membership from the organization associated with the API key (requires organization-scoped API key)
- Langfuse operation: `organizations_deleteOrganizationMembership`
- HTTP: `DELETE /api/public/organizations/memberships`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={userId*:string}. No description provided.
- Usage example:
```json
{
  "body": {
    "userId": "string"
  }
}
```

#### `langfuse_organizations_delete_project_membership`

- Intent: Delete a membership from a specific project (requires organization-scoped API key). The user must be a member of the organization.
- Langfuse operation: `organizations_deleteProjectMembership`
- HTTP: `DELETE /api/public/projects/{projectId}/memberships`
- Parameters:
- `projectId`: required; source=`path`; schema=string. No description provided.
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={userId*:string}. No description provided.
- Usage example:
```json
{
  "body": {
    "userId": "string"
  },
  "projectId": "string"
}
```

#### `langfuse_organizations_get_organization_api_keys`

- Intent: Get all API keys for the organization associated with the API key (requires organization-scoped API key)
- Langfuse operation: `organizations_getOrganizationApiKeys`
- HTTP: `GET /api/public/organizations/apiKeys`
- Parameters:
- None.
- Usage example:
```json
{}
```

#### `langfuse_organizations_get_organization_memberships`

- Intent: Get all memberships for the organization associated with the API key (requires organization-scoped API key)
- Langfuse operation: `organizations_getOrganizationMemberships`
- HTTP: `GET /api/public/organizations/memberships`
- Parameters:
- None.
- Usage example:
```json
{}
```

#### `langfuse_organizations_get_organization_projects`

- Intent: Get all projects for the organization associated with the API key (requires organization-scoped API key)
- Langfuse operation: `organizations_getOrganizationProjects`
- HTTP: `GET /api/public/organizations/projects`
- Parameters:
- None.
- Usage example:
```json
{}
```

#### `langfuse_organizations_get_project_memberships`

- Intent: Get all memberships for a specific project (requires organization-scoped API key)
- Langfuse operation: `organizations_getProjectMemberships`
- HTTP: `GET /api/public/projects/{projectId}/memberships`
- Parameters:
- `projectId`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "projectId": "string"
}
```

#### `langfuse_organizations_update_organization_membership`

- Intent: Create or update a membership for the organization associated with the API key (requires organization-scoped API key)
- Langfuse operation: `organizations_updateOrganizationMembership`
- HTTP: `PUT /api/public/organizations/memberships`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={userId*:string, role*:string}. No description provided.
- Usage example:
```json
{
  "body": {
    "role": "OWNER",
    "userId": "string"
  }
}
```

#### `langfuse_organizations_update_project_membership`

- Intent: Create or update a membership for a specific project (requires organization-scoped API key). The user must already be a member of the organization.
- Langfuse operation: `organizations_updateProjectMembership`
- HTTP: `PUT /api/public/projects/{projectId}/memberships`
- Parameters:
- `projectId`: required; source=`path`; schema=string. No description provided.
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={userId*:string, role*:string}. No description provided.
- Usage example:
```json
{
  "body": {
    "role": "OWNER",
    "userId": "string"
  },
  "projectId": "string"
}
```

### Projects

#### `langfuse_projects_create`

- Intent: Create a new project (requires organization-scoped API key)
- Langfuse operation: `projects_create`
- HTTP: `POST /api/public/projects`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={name*:string, metadata:object | null, retention*:integer}. No description provided.
- Usage example:
```json
{
  "body": {
    "name": "string",
    "retention": 0
  }
}
```

#### `langfuse_projects_create_api_key`

- Intent: Create a new API key for a project (requires organization-scoped API key)
- Langfuse operation: `projects_createApiKey`
- HTTP: `POST /api/public/projects/{projectId}/apiKeys`
- Parameters:
- `projectId`: required; source=`path`; schema=string. No description provided.
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={note:string | null, publicKey:string | null, secretKey:string | null}. No description provided.
- Usage example:
```json
{
  "body": {},
  "projectId": "string"
}
```

#### `langfuse_projects_delete`

- Intent: Delete a project by ID (requires organization-scoped API key). Project deletion is processed asynchronously.
- Langfuse operation: `projects_delete`
- HTTP: `DELETE /api/public/projects/{projectId}`
- Parameters:
- `projectId`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "projectId": "string"
}
```

#### `langfuse_projects_delete_api_key`

- Intent: Delete an API key for a project (requires organization-scoped API key)
- Langfuse operation: `projects_deleteApiKey`
- HTTP: `DELETE /api/public/projects/{projectId}/apiKeys/{apiKeyId}`
- Parameters:
- `projectId`: required; source=`path`; schema=string. No description provided.
- `apiKeyId`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "apiKeyId": "string",
  "projectId": "string"
}
```

#### `langfuse_projects_get`

- Intent: Get Project associated with API key (requires project-scoped API key). You can use GET /api/public/organizations/projects to get all projects with an organization-scoped key.
- Langfuse operation: `projects_get`
- HTTP: `GET /api/public/projects`
- Parameters:
- None.
- Usage example:
```json
{}
```

#### `langfuse_projects_get_api_keys`

- Intent: Get all API keys for a project (requires organization-scoped API key)
- Langfuse operation: `projects_getApiKeys`
- HTTP: `GET /api/public/projects/{projectId}/apiKeys`
- Parameters:
- `projectId`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "projectId": "string"
}
```

#### `langfuse_projects_update`

- Intent: Update a project by ID (requires organization-scoped API key).
- Langfuse operation: `projects_update`
- HTTP: `PUT /api/public/projects/{projectId}`
- Parameters:
- `projectId`: required; source=`path`; schema=string. No description provided.
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={name*:string, metadata:object | null, retention:integer | null}. No description provided.
- Usage example:
```json
{
  "body": {
    "name": "string"
  },
  "projectId": "string"
}
```

### PromptVersion

#### `langfuse_prompt_version_update`

- Intent: Update labels for a specific prompt version
- Langfuse operation: `promptVersion_update`
- HTTP: `PATCH /api/public/v2/prompts/{name}/versions/{version}`
- Parameters:
- `name`: required; source=`path`; schema=string. The name of the prompt. If the prompt is in a folder (e.g., "folder/subfolder/prompt-name"),
the folder path must be URL encoded.
- `version`: required; source=`path`; schema=integer. Version of the prompt to update
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={newLabels*:array}. No description provided.
- Usage example:
```json
{
  "body": {
    "newLabels": [
      "<value>"
    ]
  },
  "name": "string",
  "version": 0
}
```

### Prompts

#### `langfuse_prompts_create`

- Intent: Create a new version for the prompt with the given `name`
- Langfuse operation: `prompts_create`
- HTTP: `POST /api/public/v2/prompts`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=oneOf. No description provided.
- Usage example:
```json
{
  "body": {
    "name": "<value>",
    "prompt": "<value>",
    "type": "<value>"
  }
}
```

#### `langfuse_prompts_delete`

- Intent: Delete prompt versions. If neither version nor label is specified, all versions of the prompt are deleted.
- Langfuse operation: `prompts_delete`
- HTTP: `DELETE /api/public/v2/prompts/{promptName}`
- Parameters:
- `promptName`: required; source=`path`; schema=string. The name of the prompt
- `label`: optional; source=`query`; schema=string | null. Optional label to filter deletion. If specified, deletes all prompt versions that have this label.
- `version`: optional; source=`query`; schema=integer | null. Optional version to filter deletion. If specified, deletes only this specific version of the prompt.
- Usage example:
```json
{
  "promptName": "string"
}
```

#### `langfuse_prompts_get`

- Intent: Get a prompt
- Langfuse operation: `prompts_get`
- HTTP: `GET /api/public/v2/prompts/{promptName}`
- Parameters:
- `promptName`: required; source=`path`; schema=string. The name of the prompt. If the prompt is in a folder (e.g., "folder/subfolder/prompt-name"),
the folder path must be URL encoded.
- `version`: optional; source=`query`; schema=integer | null. Version of the prompt to be retrieved.
- `label`: optional; source=`query`; schema=string | null. Label of the prompt to be retrieved. Defaults to "production" if no label or version is set.
- `resolve`: optional; source=`query`; schema=boolean | null. Resolve prompt dependencies before returning the prompt. Defaults to `true`. Set to `false` to return the raw stored prompt with dependency tags intact. This bypasses prompt caching and is intended for debugging or one-off jobs, not production runtime fetches.
- Usage example:
```json
{
  "promptName": "string"
}
```

#### `langfuse_prompts_list`

- Intent: Get a list of prompt names with versions and labels
- Langfuse operation: `prompts_list`
- HTTP: `GET /api/public/v2/prompts`
- Parameters:
- `name`: optional; source=`query`; schema=string | null. No description provided.
- `label`: optional; source=`query`; schema=string | null. No description provided.
- `tag`: optional; source=`query`; schema=string | null. No description provided.
- `page`: optional; source=`query`; schema=integer | null. page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. limit of items per page
- `fromUpdatedAt`: optional; source=`query`; schema=string | null, format=date-time. Optional filter to only include prompt versions created/updated on or after a certain datetime (ISO 8601)
- `toUpdatedAt`: optional; source=`query`; schema=string | null, format=date-time. Optional filter to only include prompt versions created/updated before a certain datetime (ISO 8601)
- Usage example:
```json
{}
```

### Scim

#### `langfuse_scim_create_user`

- Intent: Create a new user in the organization (requires organization-scoped API key)
- Langfuse operation: `scim_createUser`
- HTTP: `POST /api/public/scim/Users`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={userName*:string, name*:object, emails:array | null, active:boolean | null, password:string | null}. No description provided.
- Usage example:
```json
{
  "body": {
    "name": {},
    "userName": "string"
  }
}
```

#### `langfuse_scim_delete_user`

- Intent: Remove a user from the organization (requires organization-scoped API key). Note that this only removes the user from the organization but does not delete the user entity itself.
- Langfuse operation: `scim_deleteUser`
- HTTP: `DELETE /api/public/scim/Users/{userId}`
- Parameters:
- `userId`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "userId": "string"
}
```

#### `langfuse_scim_get_resource_types`

- Intent: Get SCIM Resource Types (requires organization-scoped API key)
- Langfuse operation: `scim_getResourceTypes`
- HTTP: `GET /api/public/scim/ResourceTypes`
- Parameters:
- None.
- Usage example:
```json
{}
```

#### `langfuse_scim_get_schemas`

- Intent: Get SCIM Schemas (requires organization-scoped API key)
- Langfuse operation: `scim_getSchemas`
- HTTP: `GET /api/public/scim/Schemas`
- Parameters:
- None.
- Usage example:
```json
{}
```

#### `langfuse_scim_get_service_provider_config`

- Intent: Get SCIM Service Provider Configuration (requires organization-scoped API key)
- Langfuse operation: `scim_getServiceProviderConfig`
- HTTP: `GET /api/public/scim/ServiceProviderConfig`
- Parameters:
- None.
- Usage example:
```json
{}
```

#### `langfuse_scim_get_user`

- Intent: Get a specific user by ID (requires organization-scoped API key)
- Langfuse operation: `scim_getUser`
- HTTP: `GET /api/public/scim/Users/{userId}`
- Parameters:
- `userId`: required; source=`path`; schema=string. No description provided.
- Usage example:
```json
{
  "userId": "string"
}
```

#### `langfuse_scim_list_users`

- Intent: List users in the organization (requires organization-scoped API key)
- Langfuse operation: `scim_listUsers`
- HTTP: `GET /api/public/scim/Users`
- Parameters:
- `filter`: optional; source=`query`; schema=string | null. Filter expression (e.g. userName eq "value")
- `startIndex`: optional; source=`query`; schema=integer | null. 1-based index of the first result to return (default 1)
- `count`: optional; source=`query`; schema=integer | null. Maximum number of results to return (default 100)
- Usage example:
```json
{}
```

### ScoreConfigs

#### `langfuse_score_configs_create`

- Intent: Create a score configuration (config). Score configs are used to define the structure of scores
- Langfuse operation: `scoreConfigs_create`
- HTTP: `POST /api/public/score-configs`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={name*:string, dataType*:string, categories:array | null, minValue:number | null, maxValue:number | null, description:string | null}. No description provided.
- Usage example:
```json
{
  "body": {
    "dataType": "NUMERIC",
    "name": "string"
  }
}
```

#### `langfuse_score_configs_get`

- Intent: Get all score configs
- Langfuse operation: `scoreConfigs_get`
- HTTP: `GET /api/public/score-configs`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. Page number, starts at 1.
- `limit`: optional; source=`query`; schema=integer | null. Limit of items per page. If you encounter api issues due to too large page sizes, try to reduce the limit
- Usage example:
```json
{}
```

#### `langfuse_score_configs_get_by_id`

- Intent: Get a score config
- Langfuse operation: `scoreConfigs_get-by-id`
- HTTP: `GET /api/public/score-configs/{configId}`
- Parameters:
- `configId`: required; source=`path`; schema=string. The unique langfuse identifier of a score config
- Usage example:
```json
{
  "configId": "string"
}
```

#### `langfuse_score_configs_update`

- Intent: Update a score config
- Langfuse operation: `scoreConfigs_update`
- HTTP: `PATCH /api/public/score-configs/{configId}`
- Parameters:
- `configId`: required; source=`path`; schema=string. The unique langfuse identifier of a score config
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={isArchived:boolean | null, name:string | null, categories:array | null, minValue:number | null, maxValue:number | null, description:string | null}. No description provided.
- Usage example:
```json
{
  "body": {},
  "configId": "string"
}
```

### Scores

#### `langfuse_scores_get_by_id`

- Intent: Get a score (supports both trace and session scores)
- Langfuse operation: `scores_get-by-id`
- HTTP: `GET /api/public/v2/scores/{scoreId}`
- Parameters:
- `scoreId`: required; source=`path`; schema=string. The unique langfuse identifier of a score
- Usage example:
```json
{
  "scoreId": "string"
}
```

#### `langfuse_scores_get_many`

- Intent: Get a list of scores (supports both trace and session scores)
- Langfuse operation: `scores_get-many`
- HTTP: `GET /api/public/v2/scores`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. Page number, starts at 1.
- `limit`: optional; source=`query`; schema=integer | null. Limit of items per page. If you encounter api issues due to too large page sizes, try to reduce the limit.
- `userId`: optional; source=`query`; schema=string | null. Retrieve only scores with this userId associated to the trace.
- `name`: optional; source=`query`; schema=string | null. Retrieve only scores with this name.
- `fromTimestamp`: optional; source=`query`; schema=string | null, format=date-time. Optional filter to only include scores created on or after a certain datetime (ISO 8601)
- `toTimestamp`: optional; source=`query`; schema=string | null, format=date-time. Optional filter to only include scores created before a certain datetime (ISO 8601)
- `environment`: optional; source=`query`; schema=array, items=string | null. Optional filter for scores where the environment is one of the provided values.
- `source`: optional; source=`query`; schema=string | null, enum=["ANNOTATION", "API", "EVAL", null]. Retrieve only scores from a specific source.
- `operator`: optional; source=`query`; schema=string | null. Retrieve only scores with <operator> value.
- `value`: optional; source=`query`; schema=number | null, format=double. Retrieve only scores with <operator> value.
- `scoreIds`: optional; source=`query`; schema=string | null. Comma-separated list of score IDs to limit the results to.
- `configId`: optional; source=`query`; schema=string | null. Retrieve only scores with a specific configId.
- `sessionId`: optional; source=`query`; schema=string | null. Retrieve only scores with a specific sessionId.
- `datasetRunId`: optional; source=`query`; schema=string | null. Retrieve only scores with a specific datasetRunId.
- `traceId`: optional; source=`query`; schema=string | null. Retrieve only scores with a specific traceId.
- `observationId`: optional; source=`query`; schema=string | null. Comma-separated list of observation IDs to filter scores by.
- `queueId`: optional; source=`query`; schema=string | null. Retrieve only scores with a specific annotation queueId.
- `dataType`: optional; source=`query`; schema=string | null, enum=["NUMERIC", "BOOLEAN", "CATEGORICAL", "CORRECTION", "TEXT", ...]. Retrieve only scores with a specific dataType.
- `traceTags`: optional; source=`query`; schema=array, items=string | null. Only scores linked to traces that include all of these tags will be returned.
- `fields`: optional; source=`query`; schema=string | null. Comma-separated list of field groups to include in the response. Available field groups: 'score' (core score fields), 'trace' (trace properties: userId, tags, environment, sessionId). If not specified, both 'score' and 'trace' are returned by default. Example: 'score' to exclude trace data, 'score,trace' to include both. Note: When filtering by trace properties (using userId or traceTags parameters), the 'trace' field group must be included, otherwise a 400 error will be returned.
- `filter`: optional; source=`query`; schema=string | null. A JSON stringified array of filter objects. Each object requires type, column, operator, and value. Supports filtering by score metadata using the stringObject type. Example: [{"type":"stringObject","column":"metadata","key":"user_id","operator":"=","value":"abc123"}]. Supported types: stringObject (metadata key-value filtering), string, number, datetime, stringOptions, arrayOptions. Supported operators for stringObject: =, contains, does not contain, starts with, ends with.
- Usage example:
```json
{}
```

### Sessions

#### `langfuse_sessions_get`

- Intent: Get a session. Please note that `traces` on this endpoint are not paginated, if you plan to fetch large sessions, consider `GET /api/public/traces?sessionId=<sessionId>`
- Langfuse operation: `sessions_get`
- HTTP: `GET /api/public/sessions/{sessionId}`
- Parameters:
- `sessionId`: required; source=`path`; schema=string. The unique id of a session
- Usage example:
```json
{
  "sessionId": "string"
}
```

#### `langfuse_sessions_list`

- Intent: Get sessions
- Langfuse operation: `sessions_list`
- HTTP: `GET /api/public/sessions`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. Page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. Limit of items per page. If you encounter api issues due to too large page sizes, try to reduce the limit.
- `fromTimestamp`: optional; source=`query`; schema=string | null, format=date-time. Optional filter to only include sessions created on or after a certain datetime (ISO 8601)
- `toTimestamp`: optional; source=`query`; schema=string | null, format=date-time. Optional filter to only include sessions created before a certain datetime (ISO 8601)
- `environment`: optional; source=`query`; schema=array, items=string | null. Optional filter for sessions where the environment is one of the provided values.
- Usage example:
```json
{}
```

### Trace

#### `langfuse_trace_delete`

- Intent: Delete a specific trace
- Langfuse operation: `trace_delete`
- HTTP: `DELETE /api/public/traces/{traceId}`
- Parameters:
- `traceId`: required; source=`path`; schema=string. The unique langfuse identifier of the trace to delete
- Usage example:
```json
{
  "traceId": "string"
}
```

#### `langfuse_trace_delete_multiple`

- Intent: Delete multiple traces
- Langfuse operation: `trace_deleteMultiple`
- HTTP: `DELETE /api/public/traces`
- Parameters:
- `body`: required; source=`request body`; content-type=`application/json`; schema=object, fields={traceIds*:array}. No description provided.
- Usage example:
```json
{
  "body": {
    "traceIds": [
      "<value>"
    ]
  }
}
```

#### `langfuse_trace_get`

- Intent: Get a specific trace
- Langfuse operation: `trace_get`
- HTTP: `GET /api/public/traces/{traceId}`
- Parameters:
- `traceId`: required; source=`path`; schema=string. The unique langfuse identifier of a trace
- `fields`: optional; source=`query`; schema=string | null. Comma-separated list of fields to include in the response. Available field groups: 'core' (always included), 'io' (input, output, metadata), 'scores', 'observations', 'metrics'. If not specified, all fields are returned. Example: 'core,scores,metrics'. Note: Excluded 'observations' or 'scores' fields return empty arrays; excluded 'metrics' returns -1 for 'totalCost' and 'latency'.
- Usage example:
```json
{
  "traceId": "string"
}
```

#### `langfuse_trace_list`

- Intent: Get list of traces
- Langfuse operation: `trace_list`
- HTTP: `GET /api/public/traces`
- Parameters:
- `page`: optional; source=`query`; schema=integer | null. Page number, starts at 1
- `limit`: optional; source=`query`; schema=integer | null. Limit of items per page. If you encounter api issues due to too large page sizes, try to reduce the limit.
- `userId`: optional; source=`query`; schema=string | null. No description provided.
- `name`: optional; source=`query`; schema=string | null. No description provided.
- `sessionId`: optional; source=`query`; schema=string | null. No description provided.
- `fromTimestamp`: optional; source=`query`; schema=string | null, format=date-time. Optional filter to only include traces with a trace.timestamp on or after a certain datetime (ISO 8601)
- `toTimestamp`: optional; source=`query`; schema=string | null, format=date-time. Optional filter to only include traces with a trace.timestamp before a certain datetime (ISO 8601)
- `orderBy`: optional; source=`query`; schema=string | null. Format of the string [field].[asc/desc]. Fields: id, timestamp, name, userId, release, version, public, bookmarked, sessionId. Example: timestamp.asc
- `tags`: optional; source=`query`; schema=array, items=string | null. Only traces that include all of these tags will be returned.
- `version`: optional; source=`query`; schema=string | null. Optional filter to only include traces with a certain version.
- `release`: optional; source=`query`; schema=string | null. Optional filter to only include traces with a certain release.
- `environment`: optional; source=`query`; schema=array, items=string | null. Optional filter for traces where the environment is one of the provided values.
- `fields`: optional; source=`query`; schema=string | null. Comma-separated list of fields to include in the response. Available field groups: 'core' (always included), 'io' (input, output, metadata), 'scores', 'observations', 'metrics'. If not specified, all fields are returned. Example: 'core,scores,metrics'. Note: Excluded 'observations' or 'scores' fields return empty arrays; excluded 'metrics' returns -1 for 'totalCost' and 'latency'.
- `filter`: optional; source=`query`; schema=string | null. JSON string containing an array of filter conditions. When provided, this takes precedence over query parameter filters (userId, name, sessionId, tags, version, release, environment, fromTimestamp, toTimestamp).

## Filter Structure
Each filter condition has the following structure:
```json
[
  {
    "type": string,           // Required. One of: "datetime", "string", "number", "stringOptions", "categoryOptions", "arrayOptions", "stringObject", "numberObject", "boolean", "null"
    "column": string,         // Required. Column to filter on (see available columns below)
    "operator": string,       // Required. Operator based on type:
                              // - datetime: ">", "<", ">=", "<="
                              // - string: "=", "contains", "does not contain", "starts with", "ends with"
                              // - stringOptions: "any of", "none of"
                              // - categoryOptions: "any of", "none of"
                              // - arrayOptions: "any of", "none of", "all of"
                              // - number: "=", ">", "<", ">=", "<="
                              // - stringObject: "=", "contains", "does not contain", "starts with", "ends with"
                              // - numberObject: "=", ">", "<", ">=", "<="
                              // - boolean: "=", "<>"
                              // - null: "is null", "is not null"
    "value": any,             // Required (except for null type). Value to compare against. Type depends on filter type
    "key": string             // Required only for stringObject, numberObject, and categoryOptions types when filtering on nested fields like metadata
  }
]
```

## Available Columns

### Core Trace Fields
- `id` (string) - Trace ID
- `name` (string) - Trace name
- `timestamp` (datetime) - Trace timestamp
- `userId` (string) - User ID
- `sessionId` (string) - Session ID
- `environment` (string) - Environment tag
- `version` (string) - Version tag
- `release` (string) - Release tag
- `tags` (arrayOptions) - Array of tags
- `bookmarked` (boolean) - Bookmark status

### Structured Data
- `metadata` (stringObject/numberObject/categoryOptions) - Metadata key-value pairs. Use `key` parameter to filter on specific metadata keys.

### Aggregated Metrics (from observations)
These metrics are aggregated from all observations within the trace:
- `latency` (number) - Latency in seconds (time from first observation start to last observation end)
- `inputTokens` (number) - Total input tokens across all observations
- `outputTokens` (number) - Total output tokens across all observations
- `totalTokens` (number) - Total tokens (alias: `tokens`)
- `inputCost` (number) - Total input cost in USD
- `outputCost` (number) - Total output cost in USD
- `totalCost` (number) - Total cost in USD

### Observation Level Aggregations
These fields aggregate observation levels within the trace:
- `level` (string) - Highest severity level (ERROR > WARNING > DEFAULT > DEBUG)
- `warningCount` (number) - Count of WARNING level observations
- `errorCount` (number) - Count of ERROR level observations
- `defaultCount` (number) - Count of DEFAULT level observations
- `debugCount` (number) - Count of DEBUG level observations

### Scores (requires join with scores table)
- `scores_avg` (number) - Average of numeric scores (alias: `scores`)
- `score_categories` (categoryOptions) - Categorical score values

## Filter Examples
```json
[
  {
    "type": "datetime",
    "column": "timestamp",
    "operator": ">=",
    "value": "2024-01-01T00:00:00Z"
  },
  {
    "type": "string",
    "column": "userId",
    "operator": "=",
    "value": "user-123"
  },
  {
    "type": "number",
    "column": "totalCost",
    "operator": ">=",
    "value": 0.01
  },
  {
    "type": "arrayOptions",
    "column": "tags",
    "operator": "all of",
    "value": ["production", "critical"]
  },
  {
    "type": "stringObject",
    "column": "metadata",
    "key": "customer_tier",
    "operator": "=",
    "value": "enterprise"
  }
]
```

## Performance Notes
- Filtering on `userId`, `sessionId`, or `metadata` may enable skip indexes for better query performance
- Score filters require a join with the scores table and may impact query performance
- Usage example:
```json
{}
```
