# Version Management

## Single Source of Truth

The package version is defined **only once** in `pyproject.toml`:

```toml
[project]
version = "0.2.16"
```

## How It Works

The `dom/__init__.py` file dynamically reads the version at runtime using a three-tier fallback strategy:

### 1. Installed Package (Production)
For installed packages, reads from package metadata via `importlib.metadata`:
```python
from importlib.metadata import version
__version__ = version("domjudge-cli")
```

### 2. Development/Editable Install
For editable installs (`pip install -e .`), reads directly from `pyproject.toml`:
```python
import tomllib  # Python 3.11+
pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
with pyproject_path.open("rb") as f:
    pyproject_data = tomllib.load(f)
__version__ = pyproject_data["project"]["version"]
```

### 3. Last Resort Fallback
If both methods fail, uses a development marker:
```python
__version__ = "0.0.0-dev"
```

## Updating the Version

To update the package version:

1. **Edit only** `pyproject.toml`:
   ```toml
   [project]
   version = "0.2.17"  # Update this line
   ```

2. The change is automatically reflected:
   - In development: Immediately via `pyproject.toml` reading
   - In production: After installation via package metadata

## Benefits

✅ **No Split-Brain**: Single source of truth in `pyproject.toml`  
✅ **No Manual Sync**: No need to update multiple files  
✅ **Works Everywhere**: Production installs and development mode  
✅ **PEP 621 Compliant**: Modern Python packaging standard  

## Verification

Check the current version:
```bash
python -c "import dom; print(dom.__version__)"
```

Run end-to-end tests:
```bash
pytest tests/test_e2e_*.py -v --no-cov -m "not slow"
```
