import bleach
from .csscolors import csscolors

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
    'ins',
    'mark',
    'img',
    'marquee',
    'pulsate',
    'sup','sub',
    'table','thead','tbody','tr','th','td',
    'details','summary',
    'hr'
    


]

allowed_tags += csscolors
allowed_tags += ("mark" + c for c in csscolors)

allowed_attributes = bleach.sanitizer.ALLOWED_ATTRIBUTES.copy()
allowed_attributes.update(
    img=['src','alt','title'],
    ol=['start'],
    details=['open'],
)

allowed_tags.extend(bleach.sanitizer.ALLOWED_TAGS)

cleaner = bleach.sanitizer.Cleaner(tags=allowed_tags,attributes=allowed_attributes)

import markdown
md = markdown.Markdown(extensions=[
    'pymdownx.tilde',
    'pymdownx.caret',
    'fenced_code',
    'tables',
    'pymdownx.details',
])

def render(text):
    text = md.reset().convert(text)
    text = cleaner.clean(text)
    return text
