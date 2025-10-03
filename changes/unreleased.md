
No changes.

TODO:

- [x] require categories for each tag processor
- [x] rewrite normalization to use categories to decide what to do
- [ ] restore missed categories with migration with help of o_tags_relations
- [ ] Algorism of renomalization:
      - [ ] for each tag+processor properties
      - [ ] normalize tag according to categories in properties
      - [ ] if tag changed, migrate relations for specified processor
      - [ ] if original tag in rules, clone rules and replace original tag with normalized tag (do not create duplicates)
      - [ ] if we create new tag version for each processor and the original tag in rules, remove rule with original tag
- [ ] Check tag processors on the real data
- [ ] Check tag re-normalization on the real data
