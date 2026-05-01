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
  - Visual case representation (Parallel Cordinates)
  - Export functionality for retrievals
  - Import CSV validation and templating
  - dd single cases from dashboard support
  - Explanations added for similarity types
  - Manage JWT Tokens.



## [2.1.0] - 2026-05-01

### Added
- CBR-RAG feature that combines case retrieval with LLM-based generation.
- Logger system for traceability.
- Case attribute description field to case base improve metadata and support the CBR-RAG feature.
- Support for AnglE similarity with two new similarity types: Semantic AnglE Matching and Semantic AnglE Retrieval - https://aclanthology.org/2024.acl-long.101/

### Changed
- Improved API documentation on README including detail of newly add CBR-RAG feature
- Client dashboard: Changes to CSS and element arrangement

### Fixed
- Deployment issue due to old libraries
- Bug where generate tokens always showed 1970 expiry on the Client Dashboard