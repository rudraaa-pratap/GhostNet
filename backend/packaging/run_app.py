"""Package-aware entry point for the PyInstaller bundle.

``app/main.py`` cannot be the entry script — it uses relative imports,
which only resolve when executed *inside* the ``app`` package. Pointing
PyInstaller at this file (with ``pathex`` set to the backend root) keeps
``app`` importable as a normal package.
"""

from app.main import main

if __name__ == "__main__":
    main()
