
### Introducing changes

You MUST separate the stage of introducing changes ("I've introduced some changes and will introduce more later") from the stage of finalizing changes ("I've finished introducing all changes and and count them as final").

On the introducing changes stage:

- You MUST NOT run linters, formatters, or full test suites unless explicitly instructed to do so by the developer or by the project instructions.
- You MUST NOT run any polishing-related workflows unless explicitly instructed to do so by the developer or by the project instructions.
- You MAY run subsets of tests to verify that your changes are working as expected.

On the finalizing changes stage:

- You MUST not run separate linters, formatters, or full test suites unless explicitly instructed to do so by the developer or by the project instructions.
- Instead, you MUST run dedicated polishing workflow that are designed to groom the code after you've introduced changes.
