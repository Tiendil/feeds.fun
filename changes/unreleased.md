
No changes.

TODO:

- [ ] require categories for each tag processor
- [ ] rewrite normalization to use categories to decide what to do
- [ ] restore missed categories with migration with help of o_tags_relations
- [ ] Algorism of renomalization:
      - [ ] for each tag+processor properties
      - [ ] normalize tag according to categories in properties
      - [ ] if tag changed, migrate relations for specified processor
      - [ ] if original tag in rules, clone rules and replace original tag with normalized tag (do not create duplicates)
      - [ ] if we create new tag version for each processor and the original tag in rules, remove rule with original tag
