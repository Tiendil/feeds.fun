
I develop a next-gen news reader.

The main feature of the news reader:

- It marks each news items with tags.
- Users can create rules, that score news by tags.
- Interface show news ordered by score: more score — more important news — higher in the list.

The "critical problem" is:

- In a classical news reader, the read/old news are always at the bottom of the list (because news are sorted by date) and do not interfere with reading new news.
- In my news reader, after loading new news item, new news items will intersect with the already read news, because score of read news can be higher than score of new news. It is very unconvenient for the user.

So, I need a convinient way to hide read news from the list of news items.

There are next orthogonal aspects of such a feature:

1. How/when to mark news as read.
2. How/when to hide/show read news.
3. How to undo hiding of news if the user hide (in any manner) news by mistake.

# How/when to mark news as read

My variants are (can be combined):

- when the user opens news item body
- when the user clicks on button (near the item caption) "mark as read"
- when the user clicks on button (near the item caption) "mark all (top) as read" — mark all news items above this item as read and this item too
- when the user scrolls the news list and the news item is out of the screen
- when the user clicks "show more" in the news list, mark all displayed news items as read

Additional possible logic:

- Soft/hard read state with different behaviour. Soft read is turned automatically, hard read is turned manually by user or by timer after soft read. Soft read news are always shown in the list, hard read news are hidden by default.
- More "classical/enterprise" way of working with news. Allow select/deselct them and introduce operations for selected news items (mark as read, hide, etc).

# How/when to hide/show read news

My variants are:

- Do not hide read news. Just mark them as read (with some visual indication) and show them in the same places in the list.
- "Checkbox" with logic "auto hide". Instantly hide read news items if the checkbox is checked.
- Button "hide read news". Hide read news items when the user clicks on the button.
- Separate news into read/unread tabs with functionality of moving news between them.
- Tab/panel for "resently hidden/read news" with functionality of moving news back to the main list.
- Instead of hiding news, change their priority to always go to the bottom of the list.

# How to undo hiding of news

Regardless of the method of hiding news, the user should have the ability to undo hiding of news.

My variants are:

- Button "undo last mark as read" — undo the last action of marking news as read. The drawback is that undone item will not visually differ from other unread items => difficult to find it for the user.
- Logic of hiding "hide read news mark as read before the timestamp" and button "move timestamp back one item". So, the item will not change its state.

# Additional restrictions

- I want minimal dynamic reordering of news list while the user is reading news / working with this list. Reordering will distract the user and break their reading flow.

# Additional ideas

- Visualize read news by shifting their caption to the right of main vertical line of the unread news items. Or align it to the right side of the list.

# Your task

Based on the information I provided, propose more variants for "How to undo hiding of news"

--------

Reformulate/formalize initial "critial problem" to allow seeking for a creative or non-standard solution.

Based on the information I provided, propose alternative ways to solve the "critical problem"

Based on the information I provided, propose more variants for "How/when to mark news as read"

Based on the information I provided, propose more variants for "How/when to hide/show read news"
