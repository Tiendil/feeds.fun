# Module boundary problems

This inventory tracks known violations and open questions about module and role rules. [Backend rules](../specs/backend_architecture/modules_and_roles.md) · [Frontend rules](../specs/frontend_architecture/modules_and_roles.md)

## Core migration dependencies

TODO Resolve how the foundational module dependency rule applies to `ffun.core.migrations`.
The [Tach configuration](../ffun/tach.toml) permits `ffun.core.migrations` to depend on `ffun.application`.

## Current boundary problems that should be fixed

- Break the API–Application module cycle.
  Application imports API’s private root route handlers to register routes, and the root handlers import Application’s private settings to get the site domain. [Application wiring](../ffun/ffun/application/application.py#L9) · [Root handlers](../ffun/ffun/api/root/http_handlers.py#L8)

- CLI queue and metrics tests and Librarian’s background processor tests use Queues’ private `operations.py` to prepare or inspect queues.
  The CLI queue test also imports the private `FakeQueueItem` test type. [CLI queue tests](../ffun/ffun/cli/commands/tests/test_queues.py) · [CLI metrics tests](../ffun/ffun/cli/commands/tests/test_metrics.py) · [Librarian background processor tests](../ffun/ffun/librarian/tests/test_background_processors.py)

  ```python
  from ffun.queues import operations as q_operations
  from ffun.queues.tests.entities import FakeQueueItem
  ```

- Feed Discovery’s `domain.py` imports Integrations’ private `settings.py` to look up a plugin for the source URL.
  Integrations tests import Feed Discovery’s `entities.py`, forming a module dependency cycle. [Feed Discovery Domain](../ffun/ffun/feeds_discoverer/domain.py) · [Integrations plugin test](../ffun/ffun/integrations/tests/test_plugin.py)

  ```python
  # ffun.feeds_discoverer.domain
  from ffun.integrations.settings import settings as i_settings

  # ffun.integrations.tests.test_plugin
  from ffun.feeds_discoverer import entities as fd_entities
  ```

  Loader and Parsers are also part of this cyclic group. Feed Discovery imports Loader’s Errors and Parsers’ Entities, and Loader imports Parsers’ Entities. The two test imports below also form a direct cycle between Integrations and Parsers. [Feed Discovery Domain](../ffun/ffun/feeds_discoverer/domain.py) · [Loader Domain](../ffun/ffun/loader/domain.py) · [Integrations plugin test](../ffun/ffun/integrations/tests/test_plugin.py) · [Parser tests](../ffun/ffun/parsers/tests/test_feed.py)

  ```python
  # ffun.integrations.tests.test_plugin
  from ffun.parsers import entities as p_entities

  # ffun.parsers.tests.test_feed
  from ffun.integrations.tests.helpers import FakeIntegration
  ```

- Meta’s `domain.py` imports Ontology’s private `cache.py` to look up tag IDs and UIDs during tag renormalization. [Meta Domain](../ffun/ffun/meta/domain.py)

  ```python
  from ffun.ontology import cache as o_cache
  ```

- Tags and Ontology form a module dependency cycle. Tag normalization uses Ontology’s tag types, and those types use Tags’ category type. [Tags Domain](../ffun/ffun/tags/domain.py) · [Ontology Entities](../ffun/ffun/ontology/entities.py)

  ```python
  # ffun.tags.domain
  from ffun.ontology.entities import NormalizedTag, RawTag

  # ffun.ontology.entities
  from ffun.tags.entities import TagCategories
  ```

- Ontology’s `domain.py` imports Tags’ private `converters.py` to turn tag UIDs into display names. [Ontology Domain](../ffun/ffun/ontology/domain.py)

  ```python
  from ffun.tags import converters
  ```

- Users test fixtures, factories, and Domain and Operations tests import `primary_oidc_service_id` from Auth’s private `settings.py` for test user mappings.
  The Operations tests also import `single_user_service_id` to test mappings across providers. [Fixtures](../ffun/ffun/users/tests/fixtures.py) · [Factories](../ffun/ffun/users/tests/make.py) · [Domain tests](../ffun/ffun/users/tests/test_domains.py) · [Operations tests](../ffun/ffun/users/tests/test_operations.py)

  Auth’s `domain.py` imports Users’ `domain.py`, so these test imports form a module dependency cycle. [Auth Domain](../ffun/ffun/auth/domain.py)

  ```python
  # ffun.users.tests.test_operations
  from ffun.auth.settings import primary_oidc_service_id, single_user_service_id

  # ffun.auth.domain
  from ffun.users import domain as u_domain
  ```

- Google’s `entities.py` imports its chat request and response base classes through LLM Framework’s private `provider_interface.py`. Both classes are defined in LLM Framework’s public `entities.py`. [Google Entities](../ffun/ffun/google/entities.py) · [LLM Framework Entities](../ffun/ffun/llms_framework/entities.py)

  ```python
  from ffun.llms_framework.provider_interface import ChatRequest, ChatResponse
  ```

- Librarian’s processor tests import `ChatResponseTest` from LLM Framework’s private `provider_interface.py` to build fake responses for a tag deduplication test. [Librarian processor tests](../ffun/ffun/librarian/processors/tests/test_llm_general.py)

  ```python
  from ffun.llms_framework.provider_interface import ChatResponseTest
  ```

- Dispatcher’s cache tests import LLM Framework’s private provider registry to set API key statuses.
  Google and OpenAI’s provider tests import the private `Statuses` class in their key-status tests. [Dispatcher cache tests](../ffun/ffun/dispatcher/tests/test_entries_cache.py) · [Google provider tests](../ffun/ffun/google/tests/test_provider_interface.py) · [OpenAI provider tests](../ffun/ffun/openai/tests/test_provider_interface.py)

  ```python
  from ffun.llms_framework.providers import llm_providers
  from ffun.llms_framework.keys_statuses import Statuses
  ```

- Processor Quality’s `domain.py` imports Librarian’s private processor registry and context class to run a configured processor on its quality route. [Processor Quality Domain](../ffun/ffun/processors_quality/domain.py)

  ```python
  from ffun.librarian.background_processors import processors as ln_processors
  from ffun.librarian.processors.base import ProcessorContext
  ```

- Core and Domain form a module dependency cycle. Core’s test helpers import Domain’s `UserId` for log assertions, and Domain’s entities use Core’s base types. [Core test helpers](../ffun/ffun/core/tests/helpers.py) · [Domain Entities](../ffun/ffun/domain/entities.py)

  ```python
  # ffun.core.tests.helpers
  from ffun.domain.entities import UserId

  # ffun.domain.entities
  from ffun.core.entities import BaseEntity, NonEmptyString
  ```

- Feeds Links Operations and Loader Domain import Feed Collections’ private `collections` singleton to check membership or read collection metadata. [Feeds Links Operations](../ffun/ffun/feeds_links/operations.py) · [Loader Domain](../ffun/ffun/loader/domain.py)

  Dispatcher, Feeds Links, LLM Framework, and Loader tests import the same singleton to add feeds to test collections. Loader tests also read collection metadata through it. [Dispatcher tests](../ffun/ffun/dispatcher/tests/test_domain.py) · [Feeds Links tests](../ffun/ffun/feeds_links/tests/test_operations.py) · [LLM Framework tests](../ffun/ffun/llms_framework/tests/test_keys_rotator.py) · [Loader tests](../ffun/ffun/loader/tests/test_domain.py)

  ```python
  from ffun.feeds_collections.collections import collections
  ```

- Several Python modules use shared types through incidental imports in another Python module. The types are defined in `ffun.domain.entities`. The following files expose the names as a side effect of importing them for local use.

  - Feeds Entities exposes `FeedId`, which Loader Domain imports directly and SPA Entities accesses through Feeds’ `entities.py`. [Loader Domain](../ffun/ffun/loader/domain.py) · [SPA Entities](../ffun/ffun/api/spa/entities.py)
  - Feed Collections Entities exposes `CollectionId`, which Loader tests import and SPA Entities accesses through Feed Collections’ `entities.py`. [Loader tests](../ffun/ffun/loader/tests/test_domain.py) · [SPA Entities](../ffun/ffun/api/spa/entities.py)
  - LLM Framework Entities exposes `LLMTokens` and `USDCost`, which LLM Framework Domain and tests import. Google, OpenAI, and Librarian tests also import `LLMTokens` through that `entities.py` file. [LLM Framework Domain](../ffun/ffun/llms_framework/domain.py) · [Google provider tests](../ffun/ffun/google/tests/test_provider_interface.py) · [OpenAI provider tests](../ffun/ffun/openai/tests/test_provider_interface.py) · [Librarian processor tests](../ffun/ffun/librarian/processors/tests/test_llm_general.py)
  - Tags Entities exposes `TagUidPart`, which Tags’ utilities tests import. [Tags utilities tests](../ffun/ffun/tags/tests/test_utils.py)
  - Users Entities exposes `UserId`, which Auth Domain uses as `u_entities.UserId`. [Auth Domain](../ffun/ffun/auth/domain.py)

  ```python
  # ffun.loader.domain
  from ffun.feeds.entities import Feed, FeedId, FeedState
  ```

- Queues’ package initializer declares a public import path for five names already defined in its public `entities.py` file. The initializer has the Private role. [Queues initializer](../ffun/ffun/queues/__init__.py)

  ```python
  __all__ = ("BaseQueueItem", "DEFAULT_SECONDARY_ID", "QueueKind", "QueueRecord", "QueueRecordId")
  ```

- Several public functions wrap private definitions by forwarding the same arguments and results. The direct re-export rule applies to these functions.

  - Parsers Domain’s `parse_opml` forwards to `opml.extract_feeds`. [Parsers Domain](../ffun/ffun/parsers/domain.py)
  - Feed Collections Domain’s `collection`, `collection_by_slug`, `all_collections`, and `collections_for_feed` forward to the `collections` singleton. [Feed Collections Domain](../ffun/ffun/feeds_collections/domain.py)
  - Ontology Domain’s `get_ids_by_uids` and `get_tags_by_ids` forward to methods on `_tags_cache`. [Ontology Domain](../ffun/ffun/ontology/domain.py)
  - LLM Framework Domain’s `cost_points_to_usd_cost` forwards to `_cost_points.to_cost`. [LLM Framework Domain](../ffun/ffun/llms_framework/domain.py)
  - Feed Collections’ `add_feed_to_collection` and Entitlements’ `load_source_entitlement` forward to private implementations through public test helpers. [Feed Collections test helpers](../ffun/ffun/feeds_collections/tests/helpers.py) · [Entitlements test helpers](../ffun/ffun/entitlements/tests/helpers.py)

  ```python
  # ffun.parsers.domain
  def parse_opml(data: str) -> list[FeedInfo]:
      return opml.extract_feeds(data)
  ```

- Break the frontend `components` and `components/tags` module dependency cycle.
  `RuleForList.vue` in `components` renders `<rule-tag>` from `components/tags`, and `TagsFilter.vue` in `components/tags` renders `<rule-constructor>` from `components`. [Rule list item](../site/src/components/RuleForList.vue) · [Tags filter](../site/src/components/tags/TagsFilter.vue)
