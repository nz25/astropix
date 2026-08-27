# ZWO ASI SDK — vendored

`ASICamera2.dll`, the native library `zwoasi` binds to. Vendored so that the camera
driver (D12, build step 6) has a path that lives with the repo instead of an absolute
one under `~/Documents`, and so `import zwoasi` stops warning
`ASI SDK library not found`.

| | |
|---|---|
| file | `ASICamera2.dll` |
| version | 1.41.0.0 |
| architecture | x64 |
| size | 2,852,352 bytes |
| sha256 | `0c8778c3cce2012961b079e3c7d0d8348a8b3823939335d9e98148cb5d5dc34a` |
| source | ZWO ASI SDK, `lib/x64/`, installed 2026-08-25 |
| licence | MIT — `LICENSE.txt`, redistribution permitted with the notice |

Only the DLL is vendored. `ASICamera2.lib` (the MSVC import library), the C/C# headers
and the OpenCV demos are build-time artifacts for compiled languages; `zwoasi` loads the
DLL through `ctypes` and needs none of them. The full SDK stays at
`C:\Users\denis\Documents\ASI SDK`.

Usage:

```python
import zwoasi
zwoasi.init(str(pathlib.Path(__file__).parent / "vendor/zwo-asi-sdk/ASICamera2.dll"))
```

**Not a dependency of build steps 1–5.** Indexing, statistics, the PTC re-analysis and the
PixInsight contracts all run on frames that already exist. This is here for step 6.
