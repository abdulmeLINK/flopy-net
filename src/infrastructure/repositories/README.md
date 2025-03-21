# Federated Learning Repositories

This directory contains repository implementations for storing and retrieving various entities in the federated learning system.

## Model Repository

The `FileModelRepository` implementation provides a file-based storage mechanism for federated learning models.

### Architecture

Models are stored in a structured directory hierarchy:
```
models/
├── [model_name]/
│   ├── [version]_metadata.json     # Model metadata
│   ├── [version]_weights_0.npy     # Weight array 0
│   ├── [version]_weights_1.npy     # Weight array 1
│   └── ...
```

### Model Serialization

- Metadata is stored as JSON files
- Weight arrays are stored as NumPy (.npy) binary files for efficiency
- NumPy data types are automatically converted to JSON-compatible formats

### Usage

```python
from src.infrastructure.repositories.file_model_repository import FileModelRepository
from src.domain.entities.fl_model import FLModel

# Create repository
repo = FileModelRepository(base_dir="models")

# Save model
model = FLModel(name="my_model", weights=[...])
model.metadata = {
    "architecture": "cnn",
    "accuracy": 0.95
}
repo.save_model(model, version="round_1")

# Load model
loaded_model = repo.load_model("my_model", version="round_1")

# List model versions
versions = repo.list_versions("my_model")
```

### Versioning

Models can be stored with version identifiers, which enables tracking model evolution through training rounds. When no version is specified, a timestamp-based version is automatically generated.

## Client Repository

The `InMemoryClientRepository` provides an in-memory storage for client information and their model updates during federated learning rounds. 