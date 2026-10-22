import {createApp, reactive, withModifiers} from "vue";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

const trackingState = vi.hoisted(() => ({
  enabled: true,
  analyticsAllowed: true,
  loggedIn: true
}));

vi.mock("@/logic/settings", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/logic/settings")>()),
  get trackEvents() {
    return trackingState.enabled;
  }
}));

vi.mock("@/plugins/CookieConsent", () => ({
  isAnalyticsAllowed: () => trackingState.analyticsAllowed
}));

vi.mock("@/stores/globalState", () => ({
  useGlobalState: () => ({loginConfirmed: trackingState.loggedIn})
}));

import * as events from "@/logic/events";

const sendBeacon = vi.fn(() => true);
const fetchEvent = vi.fn().mockResolvedValue({});

beforeEach(() => {
  vi.clearAllMocks();
  trackingState.enabled = true;
  trackingState.analyticsAllowed = true;
  trackingState.loggedIn = true;
  vi.stubGlobal("navigator", {sendBeacon});
  vi.stubGlobal("fetch", fetchEvent);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useEventsView", () => {
  it("uses the same button identifier with the view provided by each caller", () => {
    for (const view of ["news", "feeds"] as const) {
      const app = createApp({});
      app.provide("eventsViewName", view);
      app.runWithContext(() => {
        events.buttonClicked({buttonType: "add_feed.toolbar", view: events.useEventsView()});
      });

      expect(sendBeacon).toHaveBeenLastCalledWith(
        "/spa/api/private/track-event",
        JSON.stringify({event: {name: "button_clicked", view, button_type: "add_feed.toolbar"}})
      );
    }

    expect(sendBeacon).toHaveBeenCalledTimes(2);
  });

  it("rejects an absent view before an event can be sent", () => {
    const app = createApp({});
    app.provide("eventsViewName", undefined);

    expect(() => app.runWithContext(() => events.useEventsView())).toThrow("eventsViewName is null or undefined");
    expect(sendBeacon).not.toHaveBeenCalled();
    expect(fetchEvent).not.toHaveBeenCalled();
  });
});

describe("useButtonClickTracking", () => {
  it.each(["news", "feeds"] as const)("uses the default event name and the provided %s view", (view) => {
    const app = createApp({});
    app.provide("eventsViewName", view);
    const onClick = vi.fn();
    const click = app.runWithContext(() =>
      events.useButtonClickTracking({clickEventButtonType: "add_feed.toolbar"}, onClick)
    );
    const event = new MouseEvent("click", {cancelable: true});

    click(event);

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(sendBeacon).toHaveBeenCalledWith(
      "/spa/api/private/track-event",
      JSON.stringify({event: {name: "button_clicked", view, button_type: "add_feed.toolbar"}})
    );
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(event);
    expect(event.defaultPrevented).toBe(false);
  });

  it("supports the authentication event name override", () => {
    trackingState.loggedIn = false;
    const app = createApp({});
    app.provide("eventsViewName", "public_collections");
    const click = app.runWithContext(() =>
      events.useButtonClickTracking(
        {clickEventName: "auth_button_clicked", clickEventButtonType: "register.toolbar"},
        vi.fn()
      )
    );

    click(new MouseEvent("click"));

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(sendBeacon).toHaveBeenCalledWith(
      "/spa/api/public/track-event",
      JSON.stringify({
        event: {name: "auth_button_clicked", view: "public_collections", button_type: "register.toolbar"}
      })
    );
  });

  it.each<events.ClickEventProps>([{}, {clickEventName: "auth_button_clicked"}])(
    "forwards untracked clicks without requiring a view for %j",
    (properties) => {
      const app = createApp({});
      const onClick = vi.fn();
      const click = app.runWithContext(() => events.useButtonClickTracking(properties, onClick));
      const event = new MouseEvent("click");

      click(event);

      expect(onClick).toHaveBeenCalledTimes(1);
      expect(onClick).toHaveBeenCalledWith(event);
      expect(sendBeacon).not.toHaveBeenCalled();
      expect(fetchEvent).not.toHaveBeenCalled();
    }
  );

  it("tracks before forwarding the original event once and preserves the caller's prevent modifier", () => {
    const app = createApp({});
    app.provide("eventsViewName", "news");
    const onClick = vi.fn((event: Event) => {
      expect(sendBeacon).toHaveBeenCalledTimes(1);
      expect(event.defaultPrevented).toBe(true);
    });
    const click = app.runWithContext(() =>
      events.useButtonClickTracking(
        {clickEventButtonType: "show_more.entries_pagination"},
        withModifiers(onClick, ["prevent"])
      )
    );
    const event = new MouseEvent("click", {cancelable: true});

    click(event);

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(event);
    expect(event.defaultPrevented).toBe(true);
    expect(fetchEvent).not.toHaveBeenCalled();
  });

  it("tracks clicks whose default action was already prevented", () => {
    const app = createApp({});
    app.provide("eventsViewName", "feeds");
    const onClick = vi.fn();
    const click = app.runWithContext(() =>
      events.useButtonClickTracking({clickEventButtonType: "export_opml.toolbar"}, onClick)
    );
    const event = new MouseEvent("click", {cancelable: true});
    event.preventDefault();

    click(event);

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(event);
  });

  it("uses updated tracking props on later clicks", () => {
    const app = createApp({});
    app.provide("eventsViewName", "public_collections");
    const properties = reactive<events.ClickEventProps>({});
    const onClick = vi.fn();
    const click = app.runWithContext(() => events.useButtonClickTracking(properties, onClick));

    click(new MouseEvent("click"));
    expect(sendBeacon).not.toHaveBeenCalled();

    properties.clickEventButtonType = "show_more.entries_pagination";
    click(new MouseEvent("click"));
    expect(sendBeacon).toHaveBeenLastCalledWith(
      "/spa/api/private/track-event",
      JSON.stringify({
        event: {name: "button_clicked", view: "public_collections", button_type: "show_more.entries_pagination"}
      })
    );

    properties.clickEventName = "auth_button_clicked";
    properties.clickEventButtonType = "register.tags_filter";
    click(new MouseEvent("click"));
    expect(sendBeacon).toHaveBeenLastCalledWith(
      "/spa/api/private/track-event",
      JSON.stringify({
        event: {name: "auth_button_clicked", view: "public_collections", button_type: "register.tags_filter"}
      })
    );
    expect(sendBeacon).toHaveBeenCalledTimes(2);
    expect(onClick).toHaveBeenCalledTimes(3);
  });

  it.each(["enabled", "analyticsAllowed"] as const)("still forwards clicks when %s is false", (flag) => {
    trackingState[flag] = false;
    const app = createApp({});
    app.provide("eventsViewName", "news");
    const onClick = vi.fn();
    const click = app.runWithContext(() =>
      events.useButtonClickTracking({clickEventButtonType: "add_feed.toolbar"}, onClick)
    );
    const event = new MouseEvent("click");

    click(event);

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(event);
    expect(sendBeacon).not.toHaveBeenCalled();
    expect(fetchEvent).not.toHaveBeenCalled();
  });

  it("forwards clicks synchronously while the fallback request is still pending", () => {
    vi.stubGlobal("navigator", {});
    fetchEvent.mockReturnValueOnce(new Promise(() => {}));
    const app = createApp({});
    app.provide("eventsViewName", "news");
    const onClick = vi.fn();
    const click = app.runWithContext(() =>
      events.useButtonClickTracking({clickEventButtonType: "add_feed.toolbar"}, onClick)
    );
    const event = new MouseEvent("click");

    expect(click(event)).toBeUndefined();

    expect(fetchEvent).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(event);
  });

  it("requires a view for tracked clicks", () => {
    const app = createApp({});
    const onClick = vi.fn();
    const click = app.runWithContext(() =>
      events.useButtonClickTracking({clickEventButtonType: "add_feed.toolbar"}, onClick)
    );

    expect(() => click(new MouseEvent("click"))).toThrow("eventsViewName is null or undefined");
    expect(sendBeacon).not.toHaveBeenCalled();
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("buttonClicked", () => {
  it.each<events.ButtonType>([
    "add_feed.toolbar",
    "import_opml.toolbar",
    "export_opml.toolbar",
    "subscribe.toolbar",
    "subscribe.collection_details",
    "subscribe.collection_suggestions",
    "refresh.sidebar",
    "search_feeds.discovery_form",
    "add_feed.discovery_results",
    "import_opml.form",
    "show_more.entries_pagination",
    "collapse.entries_pagination",
    "show_more.tags_pagination",
    "collapse.tags_pagination"
  ])("sends one authenticated event for %s", (buttonType) => {
    events.buttonClicked({buttonType, view: "feeds"});

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(sendBeacon).toHaveBeenCalledWith(
      "/spa/api/private/track-event",
      JSON.stringify({event: {name: "button_clicked", view: "feeds", button_type: buttonType}})
    );
    expect(fetchEvent).not.toHaveBeenCalled();
  });

  it("sends logged-out interactions to the public endpoint", () => {
    trackingState.loggedIn = false;

    events.buttonClicked({buttonType: "show_more.entries_pagination", view: "public_collections"});

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(sendBeacon).toHaveBeenCalledWith(
      "/spa/api/public/track-event",
      JSON.stringify({
        event: {
          name: "button_clicked",
          view: "public_collections",
          button_type: "show_more.entries_pagination"
        }
      })
    );
    expect(fetchEvent).not.toHaveBeenCalled();
  });

  it("does not send events when tracking is disabled", () => {
    trackingState.enabled = false;

    events.buttonClicked({buttonType: "add_feed.toolbar", view: "news"});

    expect(sendBeacon).not.toHaveBeenCalled();
    expect(fetchEvent).not.toHaveBeenCalled();
  });

  it("does not send events without analytics consent", () => {
    trackingState.analyticsAllowed = false;

    events.buttonClicked({buttonType: "add_feed.toolbar", view: "news"});

    expect(sendBeacon).not.toHaveBeenCalled();
    expect(fetchEvent).not.toHaveBeenCalled();
  });

  it("uses the existing fetch fallback when sendBeacon is unavailable", () => {
    vi.stubGlobal("navigator", {});

    events.buttonClicked({buttonType: "import_opml.form", view: "discovery"});

    expect(sendBeacon).not.toHaveBeenCalled();
    expect(fetchEvent).toHaveBeenCalledTimes(1);
    expect(fetchEvent).toHaveBeenCalledWith("/spa/api/private/track-event", {
      method: "POST",
      keepalive: true,
      mode: "no-cors",
      headers: {"Content-Type": "text/plain;charset=UTF-8"},
      body: JSON.stringify({
        event: {name: "button_clicked", view: "discovery", button_type: "import_opml.form"}
      })
    });
  });
});

describe("authButtonClicked", () => {
  it.each<events.AuthButtonType>(["register.toolbar", "register.tags_filter", "login", "join", "go_to_feeds"])(
    "sends the distinct registration or existing authentication identifier %s",
    (buttonType) => {
      trackingState.loggedIn = false;

      events.authButtonClicked({buttonType, view: "public_collections"});

      expect(sendBeacon).toHaveBeenCalledTimes(1);
      expect(sendBeacon).toHaveBeenCalledWith(
        "/spa/api/public/track-event",
        JSON.stringify({event: {name: "auth_button_clicked", view: "public_collections", button_type: buttonType}})
      );
      expect(fetchEvent).not.toHaveBeenCalled();
    }
  );
});
