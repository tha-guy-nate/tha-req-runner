# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.3] - 2026-06-16
### Added
- Python 3.13 and 3.14 classifier and CI support.
- Dependabot for automated updates.
### Changed
- Standardized CI and publish workflows; switched to `uv publish`.
- Bumped minimum dev dependency floors (pytest ≥ 9.1.0, ruff ≥ 0.15.17, mypy ≥ 2.1.0).
### Fixed
- Replaced `# type: ignore` with `cast()` to resolve mypy `unused-ignore` on Python 3.14.

## [0.2.2] - 2026-05-17
### Added
- HTTP status code accessible alongside response body from `parse_response`.

## [0.2.1] - 2026-05-17
### Added
- `raise_for_status` support to raise on non-2xx responses.
- JSON error body parsing on failed requests.

## [0.2.0] - 2026-05-16
### Added
- `httpx` backend support via `backend="httpx"` parameter or the `[httpx]` install extra.

## [0.1.2] - 2026-05-16
### Added
- `timeout` parameter for per-request timeouts.
- Default headers configuration via constructor.
- `reset_session` and `close_session` methods.

## [0.1.1] - 2026-05-16
### Changed
- Split publish workflow into separate TestPyPI and PyPI jobs.

## [0.1.0] - 2026-05-16
### Added
- Initial release with `ThaReq` for structured HTTP requests using `requests`.
