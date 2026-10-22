# UI click tracking

## Goal of the document

This document defines the UI controls that require click tracking and the naming convention for their tracking identifiers.

## Scope

This specification applies to click-tracking coverage and event contracts for frontend buttons and links.
Analytics processing after event collection is outside its scope.

## Identifier naming

New `button_type` identifiers MUST use `<operation>.<place>`.
Both parts MUST use lowercase `snake_case`.
The operation MUST describe the action, and the place MUST identify the logical UI location independently of the current view.
A control reused in the same logical place across different views MUST retain the same `button_type`.
The `view` field MUST identify the current view separately.

## Tracked controls

When event tracking is enabled and analytics consent is granted, the following controls MUST emit exactly one event per user activation with the listed event name and `button_type`.

| Control | Place | Event name | `button_type` |
| --- | --- | --- | --- |
| Register | Public collection toolbar | `auth_button_clicked` | `register.toolbar` |
| Register to create scoring rules | Tag filters | `auth_button_clicked` | `register.tags_filter` |
| Add feed | Shared toolbar | `button_clicked` | `add_feed.toolbar` |
| Import OPML | Feeds toolbar | `button_clicked` | `import_opml.toolbar` |
| Export OPML | Feeds toolbar | `button_clicked` | `export_opml.toolbar` |
| Subscribe | Public collection toolbar | `button_clicked` | `subscribe.toolbar` |
| Subscribe to a collection's feeds | Collection details | `button_clicked` | `subscribe.collection_details` |
| Subscribe to selected collections | Collection suggestions | `button_clicked` | `subscribe.collection_suggestions` |
| Refresh | Shared sidebar | `button_clicked` | `refresh.sidebar` |
| Search | Feed discovery form | `button_clicked` | `search_feeds.discovery_form` |
| Add | Feed discovery results | `button_clicked` | `add_feed.discovery_results` |
| Submit | OPML import form | `button_clicked` | `import_opml.form` |
| Next | Entries pagination | `button_clicked` | `show_more.entries_pagination` |
| Hide | Entries pagination | `button_clicked` | `collapse.entries_pagination` |
| Next | Tags pagination | `button_clicked` | `show_more.tags_pagination` |
| Hide | Tags pagination | `button_clicked` | `collapse.tags_pagination` |

The `button_clicked` event MUST contain `view` and `button_type` in addition to its event name.

## New clickable elements

When adding a new clickable UI element, an agent MUST ask the developer whether that element should be added to the tracked-controls list.
