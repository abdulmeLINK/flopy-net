# License Management for FLOPY-NET

This document describes the license management system for FLOPY-NET.

## Overview

FLOPY-NET is licensed under the Apache License 2.0. All source code files contain standardized license headers to ensure proper attribution and license compliance.

## License Files

- **LICENSE**: Main Apache License 2.0 text
- **NOTICE**: Copyright notices and third-party attributions

## License Headers

All source code files (`.py`, `.js`, `.ts`) include standardized license headers:

### Python Files
```python
#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
```

### JavaScript/TypeScript Files
```javascript
/**
 * Copyright (c) 2025 Abdulmelik Saylan
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
```

## Automation Scripts

### Adding License Headers

Use `scripts/add_license_headers.py` to automatically add license headers to all source files:

```bash
python scripts/add_license_headers.py
```

This script:
- Finds all `.py`, `.js`, and `.ts` files
- Excludes third-party directories (node_modules, .venv, etc.)
- Adds appropriate license headers if not already present
- Preserves existing docstrings and functionality

### Removing License Headers

Use `scripts/remove_license_headers.py` to remove license headers (if needed):

```bash
python scripts/remove_license_headers.py
```

⚠️ **Warning**: This will remove license headers from all files. Use with caution.

## Excluded Directories

The following directories are excluded from license header processing:
- `__pycache__`
- `.git`
- `node_modules`
- `.venv` / `venv`
- `.docusaurus`
- `docs/build`
- `dashboard/frontend/dist`

## Third-Party Dependencies

All third-party dependencies and their licenses are listed in the NOTICE file. Major dependencies include:

- **Flower**: Apache License 2.0 (Federated Learning Framework)
- **GNS3**: GPL v3 (Network Emulation Platform)
- **Flask**: BSD License (Web Framework)
- **React**: MIT License (Frontend Framework)
- **Docker**: Apache License 2.0 (Containerization)

## Citation

When using FLOPY-NET in research or projects, please include proper citation as specified in README.md.

## Fork Badge

Repositories forked from FLOPY-NET should include the "Powered by FLOPY-NET" badge:

```markdown
[![Powered by FLOPY-NET](https://img.shields.io/badge/Powered%20by-FLOPY--NET-orange?style=for-the-badge&logo=github)](https://github.com/abdulmelink/flopy-net)
```

## Compliance

This license management system ensures:
- ✅ Apache License 2.0 compliance
- ✅ Proper copyright attribution
- ✅ Third-party license acknowledgment
- ✅ Automated header management
- ✅ Research citation support