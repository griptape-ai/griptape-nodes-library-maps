# Changelog

All notable changes to the Griptape Nodes Google Maps Library will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/), and each version is
the `library_version` in `google-maps/griptape_nodes_library.json`.
**Breaking** marks a change that can stop a saved workflow from working without edits.

## [Unreleased]

<!-- Entries go in changelog.d/, one file each. See changelog.d/README.md. -->

## [0.3.0] - 2026-11-06

### Changed

- Google Street View shows its own error message when a run fails, with the HTTP status and Google's
  response under More info. A missing `GOOGLE_MAPS_API_KEY` is reported first, with links to Settings
  and Google's key page, and a refused key links to Settings. Messages no longer start with
  "Failed to fetch Street View image:".
  [#6](https://github.com/griptape-ai/griptape-nodes-library-maps/issues/6)

[Unreleased]: https://github.com/griptape-ai/griptape-nodes-library-maps/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/griptape-ai/griptape-nodes-library-maps/compare/37779236fe1fa8c84d12edbbbce025cee10a8b9c...v0.3.0
