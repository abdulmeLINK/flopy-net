# FL Common Models Package
__version__ = "1.0.0"

# Import common model classes for easier access
try:
    from .simple_models import SimpleCNN, SimpleMLP
    __all__ = ['SimpleCNN', 'SimpleMLP']
except ImportError:
    # If simple_models doesn't exist yet, just define the package
    __all__ = [] 