
### Migration

Run migrations `ffun migrate`.

### Changes

- ff-698 (gh-225) — Collect and visualize feed activity statistics.
  - Collect daily loaded-entry counts per feed.
  - Feed view refactored to behave closely to News view.
  - Added a column with an average news/day metric to the Feed view.
  - Added a detailed 30-day feed activity chart to the feed details on the Feed view.
  - "Status" and "loaded" columns were merged into a single "last load" column with color coding and tooltips for feed status.
  - The feed website URL is now extracted, stored, and displayed on the frontend.
