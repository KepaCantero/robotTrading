# Requirements: app/api/logging_utils_examples.py

**Last Updated:** 2026-02-04
**Status:** Active
**Priority:** P2 (Examples/Documentation)

## Purpose

Example file demonstrating proper usage of correlation ID logging utilities in API endpoints. This is a documentation/example file, not production code.

## Base Rules Applied

From [BASE_RULES.md](../BASE_RULES.md):

- **FMT-001:** Line length <= 100 characters
- **FMT-002:** Import organization (stdlib -> third-party -> local)
- **FMT-003:** No unused imports
- **TYP-001:** Type hints on all functions
- **LOG-001:** Structured logging with correlation IDs
- **LOG-002:** Context in logs
- **LOG-003:** Appropriate log levels
- **LOG-004:** Error logging with exception details

## File-Specific Requirements

### REQ-LOG-EX-001: Example Quality
- All examples must demonstrate best practices
- Examples must be runnable and tested
- Clear comments explaining each pattern

### REQ-LOG-EX-002: Documentation
- Docstrings for all example endpoints
- Comments explaining when to use each log level
- Integration notes with existing middleware

### REQ-LOG-EX-003: Error Handling Examples
- Examples for ValueError (business logic errors)
- Examples for RuntimeError (critical errors)
- Examples for generic Exception handling

### REQ-LOG-EX-004: Correlation ID Usage
- Demonstrate get_correlation_id_from_request()
- Show correlation ID in response
- Integration with CorrelationIdMiddleware

## Implementation Notes

This file provides examples for:
- Basic endpoint logging
- Warning level usage
- Custom log levels
- Multi-step process logging
- Error scenario handling

## GAP Analysis

| Rule ID | Status | Notes |
|---------|--------|-------|
| FMT-001 | PASS | Black formatted |
| FMT-002 | PASS | Proper import order |
| TYP-001 | PASS | Type hints present |
| LOG-001 | PASS | Structured logging |
| LOG-004 | PASS | Error logging with exceptions |

## Dependencies

- `fastapi`: API framework
- `app.api.logging_utils`: Correlation ID utilities
- `pydantic`: Request/response validation

## Testing

This is an example file. Tests should verify:
- Examples run without errors
- Correlation IDs are properly propagated
- Log levels are appropriate
