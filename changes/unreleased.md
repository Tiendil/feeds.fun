
- ff-493 — Stop raising exception on proxy error 400 (Bad Request).
- ff-492 — Stop raising `RemoteProtocolError` when `receive buffer too long`.
- ff-492 — Added support for HTTP2.
- ff-157 — Static files and version support:
  - All essential static files is now under correct static content versioning provided by Vite.
  - `/api/get-info` now returns current backend version and can be called without authentication.
  - Frontend now shows current backend version in the footer.
