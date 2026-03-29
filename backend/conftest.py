"""Root conftest — ensure the installed 'alembic' package is importable.

The local backend/alembic/ directory would otherwise shadow the installed
package when pytest adds '' (cwd) to sys.path.  We move '' to the end so
site-packages takes priority for top-level package names.
"""
import sys

# Move '' (current-directory entry) after site-packages so that the local
# alembic/ migration directory doesn't shadow the installed alembic package.
if "" in sys.path:
    sys.path.remove("")
    sys.path.append("")
