from mcp_langfuse.openapi import load_api_spec


def test_load_api_spec_has_expected_operation_count() -> None:
    spec = load_api_spec()

    assert len(spec.operations) == 87
    assert "langfuse_projects_create" in spec.by_tool_name
    assert "langfuse_trace_delete_multiple" in spec.by_tool_name
    assert "langfuse_annotation_queues_delete_queue_assignment" in spec.by_tool_name


def test_operation_input_schema_captures_path_and_body() -> None:
    spec = load_api_spec()
    operation = spec.by_tool_name["langfuse_annotation_queues_delete_queue_assignment"]
    schema = operation.input_schema

    assert schema["type"] == "object"
    assert "queueId" in schema["properties"]
    assert "body" in schema["properties"]
    assert "queueId" in schema["required"]
    assert "body" in schema["required"]


def test_operation_input_schema_captures_query_parameters() -> None:
    spec = load_api_spec()
    operation = spec.by_tool_name["langfuse_trace_list"]
    schema = operation.input_schema

    assert "page" in schema["properties"]
    assert "limit" in schema["properties"]
    assert schema["additionalProperties"] is False
