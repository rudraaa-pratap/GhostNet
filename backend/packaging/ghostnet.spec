# GhostNet PyInstaller spec — one app folder: interpreter, backend, and
# the built dashboard (bundled as data, served by the backend at runtime).
#
# Build:  cd backend && uv run pyinstaller --noconfirm packaging/ghostnet.spec
# Run:    ./dist/GhostNet/GhostNet            (add --demo / --port flags as usual)
#
# The same spec works on macOS, Windows and Linux; the output targets the
# OS that builds it.

from pathlib import Path

spec_dir = Path(SPECPATH).resolve()  # backend/packaging
backend = spec_dir.parent
repo = backend.parent

dist_dir = repo / "frontend" / "dist"
if not (dist_dir / "index.html").is_file():
    raise SystemExit(
        f"dashboard build missing at {dist_dir} — run: cd frontend && npm run build"
    )

# uvicorn resolves its loop/protocol implementations dynamically,
# so the modulegraph would otherwise miss them entirely.
hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.off",
    "uvicorn.lifespan.on",
]

a = Analysis(
    [str(spec_dir / "run_app.py")],
    pathex=[str(backend)],
    binaries=[],
    datas=[(str(dist_dir), "frontend_dist")],
    hiddenimports=hiddenimports,
    excludes=["tkinter"],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="GhostNet",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="GhostNet",
)
