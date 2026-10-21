# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['run_server.py'],
    pathex=['src'],
    datas=[],
    hiddenimports=['uvicorn','uvicorn.config','uvicorn.main','uvicorn.server','uvicorn.logging','uvicorn.loops','uvicorn.loops.asyncio','uvicorn.protocols','uvicorn.protocols.http','uvicorn.protocols.http.httptools_impl','uvicorn.protocols.http.h11_impl','uvicorn.lifespan','uvicorn.lifespan.on'],
    excludes=['tkinter','setuptools','pip','wheel','test','tests','unittest','_distutils_hack'],
    noarchive=False,
)
# Do NOT strip .dist-info. An earlier version kept metadata only for fastmcp/mcp
# and deleted the rest to save size; that broke every library that resolves its
# own version or entry points through importlib.metadata. In the 2026-10-21
# build it surfaced twice: pydantic.networks probing email_validator, then
# opentelemetry's context entry-point lookup. The frozen importer turns a
# missing distribution into StopIteration rather than PackageNotFoundError, so
# the failures are opaque. A few MB of metadata is the cheaper trade.
SKIP = ['torch','playwright','bitsandbytes','llvmlite','pyarrow','pymupdf','grpc','numba','Cython','google','azure','boto3','botocore','matplotlib','PIL','pandas','scipy','sklearn','onnxruntime']
a.binaries = [b for b in a.binaries if not any(s in b[0].lower() for s in SKIP)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name='opencode-cli-mcp-backend', debug=False, strip=False, upx=False, upx_exclude=[], runtime_tmpdir=None, console=False)
