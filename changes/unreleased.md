### Changes

- ff-664 Fixed URL helper parsing for `at://did:...` inputs by routing URL construction through `construct_f_url`.
  - Replaced direct `furl(...)` calls in `ffun.domain.urls` helper functions with `construct_f_url(...)` usage and safe fallbacks.
  - Added `at://did:...` coverage in URL domain tests for UID/source extraction and unsupported host/parent helper behavior.
  - Fixed test typing in new `at://did:...` cases to satisfy backend mypy checks.
