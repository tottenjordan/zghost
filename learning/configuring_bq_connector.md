# Set up Integration Connectors

see [setup integration connectors](https://cloud.google.com/integration-connectors/docs/setup-integration-connectors) from the docs

**TODO:** configure this for an agent or tool

```python
bigquery_toolset = ApplicationIntegrationToolset(
    project="your-gcp-project-id",
    location="your-gcp-project-location",
    connection="your-connection-name",
    entity_operations=["table_name": ["LIST"]],
)

agent = LlmAgent(
  ...
  tools = bigquery_toolset.get_tools()
)
```