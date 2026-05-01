# Changelog

All notable changes to this project since version 2 will be documented in this file.

## [2.0.0] - 2023-03-06

### Added
- Complete docker support.
- Semantic SBERT - New similarity type that uses cosine similarity on Sentence BERT embedding.
- Explanation API - Extracts the field names and local similarity values from explanations.
- Array datatype functionality.
- JWT Token based API authentication.
- Client dashboard:
  - Login Authentication support
  - Visual case representation (Parallel Coordinates)
  - Export functionality for retrievals
  - Import CSV validation and templating
  - Add individual cases from dashboard support
  - Explanations added for similarity types
  - Manage JWT Tokens.


## [2.1.0] - 2026-05-01

### Added
- Added **CBR-RAG**, combining case retrieval with LLM-based generation through the `/rag` endpoint.
- Added configurable LLM provider support for CBR-RAG workflows.
- Added a logger system to improve traceability and debugging.
- Added case attribute descriptions to improve project metadata and provide richer context for CBR-RAG prompts.
- Added support for AnglE similarity with two new similarity types: **Semantic AnglE Matching** and **Semantic AnglE Retrieval**. See: https://aclanthology.org/2024.acl-long.101/
- Added **Suggest from Data**, an assisted dashboard workflow for generating project attribute configurations from CSV samples. The workflow profiles uploaded data, suggests CloodCBR-compatible data types, similarity measures, weights, and descriptions, and optionally enriches descriptions using a configured LLM. Suggestions remain editable and are only available before a project casebase is created.
- Added a generic dashboard RAG task that supports project-specific prompt templates and reuses the existing Revise and Retain workflow.

### Changed
- Improved README API documentation, including details and examples for the new CBR-RAG feature.
- Updated the README API endpoint table with newly added and previously undocumented routes.
- Refreshed the client dashboard styling and improved layout for project, attribute, token, and configuration workflows.

### Fixed
- Fixed deployment issues caused by outdated libraries.
- Fixed a dashboard bug where generated tokens always displayed a 1970 expiry date.
- Fixed a retain-step error that occurred when retaining cases from requests that supplied a full project object instead of `projectId`, including RAG-generated cases revised through the dashboard.


