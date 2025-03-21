# Federated Learning Domain Entities

This directory contains the core domain entities used in the federated learning system.

## FLModel

The `FLModel` class represents a federated learning model, containing:

- Model weights (as NumPy arrays)
- Metadata about the model (architecture, training progress, etc.)

### Structure

```python
class FLModel:
    def __init__(self, name: str, weights: List[np.ndarray]):
        self.name = name           # Unique identifier for the model
        self.weights = weights     # List of weight arrays
        self.metadata = {}         # Dictionary of model metadata
```

### Metadata

The metadata dictionary typically contains:

- `architecture`: Model architecture type
- `input_shape`: Shape of the input tensor
- `output_shape`: Shape of the output tensor
- `parameters`: Total number of model parameters
- `round`: Current training round
- `aggregation_round`: Number of times the model has been aggregated
- `participating_clients`: Number of clients that contributed to this model
- `total_samples`: Total number of training samples used
- `timestamp`: When the model was created/updated

## Client

The `Client` class represents a client node in the federated learning system, containing:

- Client identification information
- Capabilities and resources
- Training history and contribution metrics 