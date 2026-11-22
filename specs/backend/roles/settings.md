# Settings role

## Goal of the document

This document describes requirements for Python code with the Settings role (`settings.py`) and for configuration entities and settings objects elsewhere in the Feeds Fun backend.

## Scope

This specification applies to Python files with the Settings role and to configuration entities and settings objects under `ffun/ffun`.

## Runtime side effects

Files with the Settings role MUST NOT perform business operations, database queries, provider calls, or other runtime side effects.

## Configuration validation and loading

The following rules apply to configuration entities and settings objects throughout `ffun/ffun`.

Configuration entities SHOULD use Pydantic to reject malformed data before it reaches code that consumes the configuration.

Settings classes that load configuration from environment variables or `.env` files SHOULD inherit from `ffun.core.settings.BaseSettings` to keep environment loading consistent across modules.

A settings object acting as the configuration-loading boundary MAY read configuration files from explicitly configured or declared paths.
It MUST limit its filesystem access to reading those files.
