# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-05-07

### Added

- Added federated Oracle source aggregation behind `search_documentation`.
- Added Oracle Learn source handling with the `learn` source role.
- Added Oracle PaaS documentation handling with the `paas_docs` source role.
- Added Architecture Center supplemental search using Oracle Solutions assets.
- Added Oracle Blogs supplemental search for latest announcements and recent context.
- Added intent-aware source ranking across reference, how-to, architecture, comparison, latest, and example queries.
- Added `answer_question` support for reading and citing Oracle Blog evidence for latest/news answers.
- Added tests for source-role detection, source aggregation, intent ranking, and blog evidence.
- Added implementation plan `docs/superpowers/plans/2026-05-07-combine-oracle-source-pipeline.md`.

### Changed

- Expanded supported Oracle documentation roots to include `docs.oracle.com/en/learn/`,
  `docs.oracle.com/en/paas/`, `docs.oracle.com/en/solutions/`, and
  `docs.oracle.com/solutions/`.
- Classified Oracle Solutions URLs as `architecture_center` evidence.
- Updated README documentation for supported roots and source roles.
- Bumped package version metadata to `1.1.0`.

## [1.0.0] - 2026-05-06

### Added

- Initial OCI Documentation MCP Server release from commit `ceffa78`.
- Added MCP tools for searching OCI documentation, reading documentation pages,
  extracting page sections, and answering questions with citations.
- Added Oracle Architecture Center and Oracle Blogs helper modules.
- Added local `oci-docs` CLI wrapper.
- Added repo-scoped `/oci-docs` Codex skill.
- Added tests, Docker support, project documentation, and OCI documentation design notes.
