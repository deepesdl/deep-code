# Python API

`deep_code.tools.publish.Publisher` is the main entry point.

```python
from deep_code.tools.publish import Publisher

publisher = Publisher(
    dataset_config_path="dataset.yaml",
    workflow_config_path="workflow.yaml",
    environment="staging",
)

# Generate files locally (no PR)
publisher.publish(write_to_file=True, mode="all")

# Or open a PR directly
publisher.publish(write_to_file=False, mode="dataset")
```

