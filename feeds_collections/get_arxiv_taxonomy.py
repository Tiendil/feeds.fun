import httpx
import toml
import re
from bs4 import BeautifulSoup, NavigableString


def parse_sub_subcategories(meta_category: str, sub_category: str, root):
    categories = []

    for el in root.children:
        if isinstance(el, NavigableString):
            continue

        name = el.find('h4').text
        description = el.find('p').text

        categories.append({'meta_category': meta_category,
                           'sub_category': sub_category,
                           'name': name,
                           'description': description})

    return categories


def parse_sub_subcategories_container(meta_category: str, root):
    children = list(root.children)

    children = [child for child in children if not isinstance(child, NavigableString)]

    if len(children) == 1:
        return parse_sub_subcategories(meta_category, meta_category, children[0])

    name = children[0].find('h3').text

    return parse_sub_subcategories(meta_category, name, children[1])


def parse_subcategories(meta_category: str, root):
    categories = []

    for el in root.children:
        if isinstance(el, NavigableString):
            continue
        categories.extend(parse_sub_subcategories_container(meta_category, el))

    return categories


def parse(content: str):  # noqa

    soup = BeautifulSoup(content, 'html.parser')

    root = soup.find(id='category_taxonomy_list')

    categories = []

    meta_category = None

    state = "wait_for_title"

    for el in root.children:
        if isinstance(el, NavigableString):
            continue

        if state == "wait_for_title":
            if el.name == 'h2':
                meta_category = el.text
                state = "wait_for_subcategories"
                continue

            raise NotImplementedError()

        if state == "wait_for_subcategories":
            if el.name == 'div':
                subcategories = parse_subcategories(meta_category, el)
                categories.extend(subcategories)
                state = "wait_for_title"
                meta_category = None
                continue

            raise NotImplementedError()

        raise NotImplementedError()

    return categories


CAT_ID_AND_NAME_REGEX = re.compile(r"(.*) \((.*)\)")


def normalize(raw_categories):
    categories = []

    for raw_category in raw_categories:

        cat_id, cat_name = CAT_ID_AND_NAME_REGEX.match(raw_category['name']).groups()

        cat_name = cat_name.strip()

        meta_name = raw_category['meta_category'].strip()
        parent_name = raw_category['sub_category'].strip()

        if '(' in parent_name:
            parent_name = parent_name.split('(')[0].strip()

        title_parts = [meta_name]

        if parent_name != title_parts[-1]:
            title_parts.append(parent_name)

        if cat_name != title_parts[-1]:
            title_parts.append(cat_name)

        title = " :: ".join(title_parts)

        category = {
            'url': f"https://rss.arxiv.org/rss/{cat_id}",
            "title": title,
            "description": raw_category['description']
        }

        categories.append(category)

    return categories


def main():
    url = "https://arxiv.org/category_taxonomy"

    response = httpx.get(url)

    raw_categories = parse(response.content)

    categories = normalize(raw_categories)

    print(toml.dumps({"feeds": categories}))


if __name__ == "__main__":
    main()
