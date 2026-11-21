# Code organization by layers and vertical slices

## Goal of the document

This document describes how projects organize source files and code elements by layer and slice.

## Scope

This specification applies to the layout and dependencies of source code in projects that adopt layers and slices.
These rules apply independently of deployment layout and runtime interactions.

## Dictionary

- `code element` — a construct in source code that defines data or behavior, declares an interface, or performs work at file scope.
  - A function such as `square`.
  - A type such as a `Point` struct or an `Angle` type alias.
  - A constant such as `MAX_ATTEMPTS`.
  - An interface declaration that specifies a `draw` method.
  - A file-level statement such as `register_handler(on_resize)`.
- `layer` — a group of code elements that serve a common architectural role at a given level of abstraction and follow a policy for dependencies between layers.
- `vertical slice` — a group of code elements that together serve a coherent functional responsibility and follow a policy for dependencies between slices.
  This document uses `slice` as the short form.

## Example project

The examples use a parcel shipping application that tracks shipments, standardizes postal addresses, and books carrier pickups.

## Layers

A project MUST define each layer's architectural role and level of abstraction.
A layer MAY have sublayers that specialize its role.
Each sublayer MUST have exactly one parent layer.

**Example:** `shipments/models.py` defines a `Shipment` in the `Shipments` slice, and `addresses/models.py` defines a `PostalAddress` in the `Addresses` slice.
Both files belong to the `Models` layer because they define data types used by other code.
The `Business logic` layer implements rules and workflows such as postal address normalization and pickup booking.
The `Gateways` layer communicates with external systems.
Its `HTTP` and `Storage` sublayers handle direct carrier requests and database access.
The `Entry points` layer adapts external inputs and outputs, with a `CLI` sublayer for shipment commands.

**Terminology:** In this specification, layers classify source code by architectural role.
For example, assigning a file to the `Gateways / HTTP` sublayer identifies its role and the placement rules that apply to it.
This classification can be used with different architectural styles.

## Slices

A project MUST define each slice's functional responsibility.
A slice MAY have sub-slices that own narrower parts of its responsibility.
Each sub-slice MUST have exactly one parent slice.

**Example:** The `Shipments` slice owns shipment records, tracking, and returns.
Its code spans the `Models`, `Business logic`, and `Gateways` layers.
The `Addresses` slice owns postal address normalization.
The `Dispatch` slice owns booking pickups with carriers.
The `Diagnostics` slice provides shared technical services such as logging.
The `Command line` slice owns the command interface, including command registration, argument handling, and terminal output.

## Membership and nesting

Each project MUST declare which of its source files are subject to the layer and slice rules.
A project MAY leave some source files outside that scope.

**Rationale:** A project may adopt the rules gradually, retain legacy files that would be too costly to restructure, or defer assignments until its structure is clear enough to define layer and slice boundaries.

Each governed source file and each code element it contains MUST belong directly to exactly one layer and exactly one slice.
A code element MUST have the same direct assignments as every governed file that contains its source code.
Code within an element follows the element's assignments.

A direct assignment MAY be to a layer or slice that has children.
Membership in a sublayer or sub-slice implies membership in its ancestors.
Layers at the same level of the layer hierarchy MUST have disjoint membership.
Slices at the same level of the slice hierarchy MUST have disjoint membership.

A project MUST define which pairs of direct layer and slice assignments are permitted.
Each governed source file MUST use a permitted pair.
A permitted pair MAY contain zero or more files.

**Example:** `shipments/models.py` belongs directly to the `Models` layer and the `Shipments` slice because its types serve the whole slice.
`addresses/models.py` belongs directly to the same layer and the `Addresses` slice.
The project also permits the `Models` layer in the `Shipments / Tracking` sub-slice, where that pair has no files.
The tracking client at `shipments/tracking/http_client.py` belongs directly to the `Gateways / HTTP` sublayer and the `Shipments / Tracking` sub-slice.
It inherits membership in the `Gateways` layer and the `Shipments` slice.
Of these three slices, only the `Shipments / Tracking` sub-slice permits direct placement in the `Gateways / HTTP` sublayer.

**Counterexample:** Assigning the tracking client to both the `Gateways / HTTP` and `Gateways / Storage` sublayers violates the layer membership rule.
Assigning it to both the `Shipments / Tracking` and `Shipments / Returns` sub-slices violates the slice membership rule.

## Project layout specifications

A project MAY define its layer and slice layout in one or more specifications.
Each project layout specification MUST be named `layers_and_slices.md`.
Each layout specification MUST identify the source files it governs.
A project MAY choose how to organize and present its layer and slice declarations, subject to the applicable specification format rules.

**Rationale:** A common filename gives readers a single name to search for when looking for the layout of any part of a project.

Independent layout specifications MAY define separate layer and slice hierarchies.
Two layout specifications MUST govern disjoint source scopes unless one is an ancestor of the other through declared parent relationships.

A nested layout specification MUST identify its parent layout specification and the slice it refines.
The nested scope MUST be within the source scope of that slice.
A nested layout specification MAY define sub-slices of the slice it refines and introduce layers or sublayers in the parent layout for use within its scope.
It MAY also define dependency rules for that scope.
Code in the nested scope MUST satisfy all applicable rules from its layout specification and its ancestor layout specifications.

**Example:** In the parcel shipping project, `specs/backend/layers_and_slices.md` governs source files under `server/`, and `specs/frontend/layers_and_slices.md` governs source files under `client/`.
The backend specification declares the `Shipments` slice for code under `server/shipments/`.
`specs/backend/shipments/layers_and_slices.md` names the backend specification as its parent and refines the `Shipments` slice for that source scope.
The nested specification adds the `Shipments / Tracking` sub-slice and introduces the `Gateways / HTTP` sublayer for use within it.
Together the specifications give the tracking client one direct assignment in each backend hierarchy, with `Gateways / HTTP` as its sublayer and `Shipments / Tracking` as its sub-slice.

## File and package layout

A project MUST give each slice a distinct source directory or package.
The nesting of these locations MUST follow the slice hierarchy.
The innermost declared slice location containing a file MUST determine its direct slice assignment.
Source paths MUST be organized slice first, with any layer-specific part of the path inside the directory or package of the file's most specific slice.

**Rationale:** Placing the slice first lets readers identify the owning slice from the file path before interpreting the layer's placement rule.

Each layer MUST have exactly one explicit placement rule for files assigned directly to it.
The rule MUST use one of the following forms.

- A **designated slice** rule places the layer's files in one specified slice and identifies their location within that slice when needed.
- A **recurring location** rule places the layer's files at the same relative location or according to the same naming pattern within each participating slice.

The slice locations and layer placement rules MUST identify a single pair of direct assignments for each governed file.

**Example:** The `Entry points / CLI` sublayer uses the `commands` package of the `Command line` slice as its designated location.
The file `commands/shipments.py` belongs to that sublayer and slice and provides commands that use shipment services.
The `Gateways` layer uses `gateway.py` as a recurring location in slices that assign files directly to that layer.
The `Gateways / HTTP` sublayer uses `http_client.py` in participating slices.
This places the tracking client at `shipments/tracking/http_client.py` in the `Shipments / Tracking` sub-slice.

## Dependency rules and public boundaries

A project MUST define which kinds of dependencies it governs and which directions it permits between layers and between slices.
It MUST state where each rule applies, including how it applies within a slice, across slices, and at nested boundaries.
Dependency rules apply to direct dependencies unless they explicitly cover transitive dependencies.
The layer and slice assignments of the source and target determine which dependency rules apply.
Each dependency MUST satisfy all applicable direction and access rules.

Dependencies between slices MUST form an acyclic graph.

A project MUST define which interfaces it exposes at each governed layer or slice boundary, which callers may use them, and how callers access them.
A project MUST define interface exposure and access using rules based on shared criteria, such as module roles, visibility markers, or naming patterns.
A project MAY enumerate individual code elements only when the interface contract requires a closed set of exact members.
For a direct dependency across a governed boundary, the caller MUST use an interface exposed to it at that boundary.

**Example:** Within the `Dispatch` slice, a rule permits imports from the `Business logic` layer to the `Gateways` layer.
`dispatch/service.py` imports `dispatch/gateway.py` under that rule to book a pickup through a carrier's API client.
A cross-slice rule permits the `Gateways` layer of the `Dispatch` slice to use functions marked public in `addresses/service.py`, which belongs to the `Business logic` layer of the `Addresses` slice.
`dispatch/gateway.py` imports `normalize_address` through that interface to standardize the address returned by the carrier.
These two imports point in opposite directions when grouped by layer and form a one-way chain between files.

**Counterexample:** A direct import from the `Dispatch` slice to the private `addresses/_postal_codes.py` file violates the rule limiting access to the public interface of the `Addresses` slice.
A dependency from the `Addresses` slice back to the `Dispatch` slice violates the allowed direction.

**Example:** A uniform layer order can permit calls between peers in the `Business logic` layer.
In the `Dispatch` slice, `dispatch/gateway.py` in the `Gateways` layer can return the address as reported by the carrier.
`dispatch/service.py` in the `Business logic` layer can then call `normalize_address` in the same layer of the `Addresses` slice.

**Example:** In the `Shipments` slice, `shipments/service.py` in the `Business logic` layer can publicly re-export `create_shipping_label` from `shipments/gateway.py` in the `Gateways` layer.
`commands/shipments.py` in the `Entry points / CLI` sublayer of the `Command line` slice can import the function through that public interface when the policy permits it.
The resulting dependency chain is `commands/shipments.py` → `shipments/service.py` → `shipments/gateway.py`.
