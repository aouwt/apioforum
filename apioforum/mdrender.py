import bleach

allowed_tags = [
    'p',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'pre',
    'del',
]
allowed_tags.extend(bleach.sanitizer.ALLOWED_TAGS)

cleaner = bleach.sanitizer.Cleaner(tags=allowed_tags)

import markdown
md = markdown.Markdown(extensions=['pymdownx.tilde'])

def render(text):
    text = md.reset().convert(text)
    text = cleaner.clean(text)
    return text
