# Code organization by modules and roles

## Goal of the document

This document describes how projects organize source files and code elements by module and role.

## Scope

This specification applies to the layout and dependencies of source code in projects organized by modules and roles.
These rules apply independently of deployment layout and runtime interactions.

## Dictionary

- `code element` — a construct in source code that defines data or behavior, declares an interface, or performs work at file scope.
  - A function such as `square`.
  - A type such as a `Point` struct or an `Angle` type alias.
  - A constant such as `MAX_ATTEMPTS`.
  - An interface declaration that specifies a `draw` method.
  - A file-level statement such as `register_handler(on_resize)`.
- `module` — a declared architectural unit that owns a coherent responsibility and defines which interfaces other modules may use.
- `role` — a classification of a source file and its code elements by their purpose or exposure.

## Example project

The examples use a parcel shipping application that tracks shipments, standardizes postal addresses, and books carrier pickups.

## Roles

A project MUST define the purpose or exposure that characterizes each role.
A role MAY have nested roles that specialize it.
Each nested role MUST have exactly one parent role.

**Example:** `shipments/models.py` defines a `Shipment` in the `Shipments` module, and `addresses/models.py` defines a `PostalAddress` in the `Addresses` module.
Both files have the `Models` role because they define data types used by other code.
The `Business logic` role implements rules and workflows such as postal address normalization and pickup booking.
The `Gateways` role communicates with external systems.
Its `HTTP` and `Storage` nested roles handle direct carrier requests and database access.
The `Entry points` role adapts external inputs and outputs, with a nested `CLI` role for shipment commands.

**Terminology:** Assigning a file to the `Gateways / HTTP` nested role identifies its purpose and the placement rules that apply to it.
Projects can use roles with different architectural styles.

## Modules

A project MUST define each module's functional responsibility.
A module MAY have nested modules that own narrower parts of its responsibility.
Each nested module MUST have exactly one parent module.

**Example:** The `Shipments` module owns shipment records, tracking, and returns.
Its code spans the `Models`, `Business logic`, and `Gateways` roles.
The `Addresses` module owns postal address normalization.
The `Dispatch` module owns booking pickups with carriers.
The `Diagnostics` module provides shared technical services such as logging.
The `Command line` module owns the command interface, including command registration, argument handling, and terminal output.

## Membership and nesting

Each project MUST declare which of its source files are subject to the module and role rules.
A project MAY leave some source files outside that scope.

**Rationale:** A project may adopt the rules gradually, retain legacy files that would be too costly to restructure, or defer assignments until its structure is clear enough to define its modules and roles.

Each governed source file and each code element it contains MUST belong directly to exactly one module and have exactly one direct role.
A code element MUST have the same direct assignments as every governed file that contains its source code.
Code within an element follows the element's assignments.

A direct assignment MAY be to a module or role that has children.
Membership in a nested module or nested role implies membership in its ancestors.
Modules at the same level of the module hierarchy MUST have disjoint membership.
Roles at the same level of the role hierarchy MUST have disjoint membership.

A project MUST define which pairs of direct module and role assignments are permitted.
Each governed source file MUST use a permitted pair.
A permitted pair MAY contain zero or more files.

**Example:** `shipments/models.py` belongs directly to the `Shipments` module and has the `Models` role because its types serve the whole module.
`addresses/models.py` belongs directly to the `Addresses` module and has the same role.
The project also permits the `Models` role in the `Shipments / Tracking` nested module, where that pair has no files.
The tracking client at `shipments/tracking/http_client.py` belongs directly to the `Shipments / Tracking` nested module and has the `Gateways / HTTP` nested role.
It inherits membership in the `Shipments` module and the `Gateways` role.
Of these three modules, only the `Shipments / Tracking` nested module permits direct placement in the `Gateways / HTTP` nested role.

**Counterexample:** Assigning the tracking client to both the `Gateways / HTTP` and `Gateways / Storage` nested roles violates the role membership rule.
Assigning it to both the `Shipments / Tracking` and `Shipments / Returns` nested modules violates the module membership rule.

## Project layout specifications

A project MAY define its module and role layout in one or more specifications.
Each project layout specification MUST be named `modules_and_roles.md`.
Each layout specification MUST identify the source files it governs.
A project MAY choose how to organize and present its module and role declarations, subject to the applicable specification format rules.

**Rationale:** A common filename gives readers a single name to search for when looking for the layout of any part of a project.

Independent layout specifications MAY define separate module and role hierarchies.
Two layout specifications MUST govern disjoint source scopes unless one is an ancestor of the other through declared parent relationships.

A nested layout specification MUST identify its parent layout specification and the module it refines.
The nested scope MUST be within the source scope of that module.
A nested layout specification MAY define nested modules within the module it refines and introduce roles or nested roles in the parent layout for use within its scope.
It MAY also define dependency rules for that scope.
Code in the nested scope MUST satisfy all applicable rules from its layout specification and its ancestor layout specifications.

**Example:** In the parcel shipping project, `specs/backend/modules_and_roles.md` governs source files under `server/`, and `specs/frontend/modules_and_roles.md` governs source files under `client/`.
The backend specification declares the `Shipments` module for code under `server/shipments/`.
`specs/backend/shipments/modules_and_roles.md` names the backend specification as its parent and refines the `Shipments` module for that source scope.
The nested specification adds the `Shipments / Tracking` nested module and introduces the `Gateways / HTTP` nested role for use within it.
Together the specifications give the tracking client one direct assignment in each backend hierarchy, with `Gateways / HTTP` as its nested role and `Shipments / Tracking` as its nested module.

## File and package layout

A project MUST give each module a distinct source directory or package.
The nesting of these locations MUST follow the module hierarchy.
The innermost declared module location containing a file MUST determine its direct module assignment.
Source paths MUST be organized module first, with any role-specific part of the path inside the directory or package of the file's most specific module.

**Rationale:** Placing the module first lets readers identify the owning module from the file path before interpreting the role's placement rule.

Each role MUST have exactly one explicit placement rule for files assigned directly to it.
The rule MUST use one of the following forms.

- A **designated module** rule places the role's files in one specified module and identifies their location within that module when needed.
- A **recurring location** rule places the role's files at the same relative location or according to the same naming pattern within each participating module.

The module locations and role placement rules MUST identify a single pair of direct assignments for each governed file.

**Example:** Files in the `commands` package of the `Command line` module have the `Entry points / CLI` nested role.
The file `commands/shipments.py` has that role and provides commands that use shipment services.
`gateway.py` has the `Gateways` role in modules that assign files directly to that role.
`http_client.py` has the `Gateways / HTTP` nested role in participating modules.
This places the tracking client at `shipments/tracking/http_client.py` in the `Shipments / Tracking` nested module.

## Dependency rules and public boundaries

A project MUST define which kinds of dependencies it governs and which directions it permits between modules and between roles.
It MUST state where each rule applies, including how it applies within a module, across modules, and at nested boundaries.
Dependency rules apply to direct dependencies unless they explicitly cover transitive dependencies.
The module and role assignments of the source and target determine which dependency rules apply.
Each dependency MUST satisfy all applicable direction and access rules.

Dependencies between modules MUST form an acyclic graph.

A project MUST define which interfaces it exposes at each governed module or role boundary, which callers may use them, and how callers access them.
A project MUST define interface exposure and access using rules based on shared criteria, such as roles, visibility markers, or naming patterns.
A project MAY enumerate individual code elements only when the interface contract requires a closed set of exact members.
For a direct dependency across a governed boundary, the caller MUST use an interface exposed to it at that boundary.

**Example:** Within the `Dispatch` module, a rule permits imports from the `Business logic` role to the `Gateways` role.
`dispatch/service.py` imports `dispatch/gateway.py` under that rule to book a pickup through a carrier's API client.
A rule for dependencies between modules permits files with the `Gateways` role in the `Dispatch` module to use functions marked public in `addresses/service.py`, which has the `Business logic` role in the `Addresses` module.
`dispatch/gateway.py` imports `normalize_address` through that interface to standardize the address returned by the carrier.
These two imports point in opposite directions when grouped by role and form a one-way chain between files.

**Counterexample:** A direct import from the `Dispatch` module to the private `addresses/_postal_codes.py` file violates the rule limiting access to the public interface of the `Addresses` module.
A dependency from the `Addresses` module back to the `Dispatch` module violates the allowed direction.

**Example:** A dependency policy can permit calls between files assigned to the same role in different modules.
In the `Dispatch` module, `dispatch/gateway.py` in the `Gateways` role can return the address as reported by the carrier.
`dispatch/service.py` in the `Business logic` role can then call `normalize_address` in the same role of the `Addresses` module.

**Example:** In the `Shipments` module, `shipments/service.py` in the `Business logic` role can publicly re-export `create_shipping_label` from `shipments/gateway.py` in the `Gateways` role.
`commands/shipments.py` in the `Entry points / CLI` nested role of the `Command line` module can import the function through that public interface when the policy permits it.
The resulting dependency chain is `commands/shipments.py` → `shipments/service.py` → `shipments/gateway.py`.
