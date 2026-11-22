# Domain role

## Goal of the document

This document describes requirements for Python code with the Domain role (`domain.py`) in the Feeds Fun backend.

## Scope

This specification applies to Python files with the Domain role under `ffun/ffun`.

## Domain functions

Domain functions SHOULD hide low-level communication details from callers.
Callers should not need to know whether a workflow uses PostgreSQL, HTTP, providers, local tools, or multiple operation calls.
