# DTO-centric architecture

## Goal of the document

This document describes the responsibilities and ownership of data transfer objects in a DTO-centric architecture.

## Scope

This specification applies to code in parts of a project that adopt a DTO-centric architecture.

## Dictionary

- `DTO` — Data Transfer Object — a typed object that carries structured application data or parsed intent.

## DTO behavior

DTOs SHOULD contain only behavior that is pure and local to their data.

DTOs MUST leave external I/O and process execution to surrounding code.
A configuration settings DTO MAY read configuration files when it acts as the configuration-loading boundary.

Validation that requires external I/O or process execution MUST take place outside DTO definitions.

The [programming code conventions](code.md) cover boundary typing, validation at construction, and serialization.

## Ownership and representation

Module-specific DTOs MUST belong to the module that owns the corresponding responsibility.

External-boundary transfer DTOs MUST belong to the module that owns the external boundary.
For example, provider-specific request and response DTOs belong to the module that owns the provider boundary.

Domain DTOs MUST model domain concepts independently from the concrete interface that creates or renders them.
Domain DTOs MUST NOT depend on API route names, CLI option parsing, database table shapes, or concrete configuration file syntax.

## Configuration DTOs

Configuration DTOs MAY represent parsed environment or settings data at the configuration loading boundary when their responsibility is to validate the input shape.
Configuration DTOs MUST preserve enough information to report useful configuration errors.

Configuration settings DTOs acting as the configuration-loading boundary SHOULD pass parsed file data to pure configuration or domain DTOs for validation.

Configuration DTOs MUST NOT perform side effects other than loading configuration at that boundary.

Configuration DTOs MAY reference domain DTOs when the referenced concept has already been validated as a domain concept.

## CLI command DTOs

CLI command DTOs MUST represent parsed user intent before the command is executed.
CLI command DTOs MUST model command selection and parsed options independently from rendered output.
CLI command DTOs MUST NOT contain rendered output.
CLI command DTOs MUST NOT perform command execution.
