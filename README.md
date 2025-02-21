# Ansible-Sphinx

Classic Sphinx extension for documenting your Ansible collection, alternative
to antsibull-doc which I find a bit invasive and doesn't define a Sphinx
domain which I like to cross-reference stuff, even in-between repositories
using Sphinx inventories.

## Quickstart

Install the package:

```
pip install ansible-sphinx
```

Add to ``extensions`` in your ``docs/conf.py``:

```python
extensions = ['ansible_sphinx', 'myst_parser']
```

Then, add to ``conf.py``:

```python
import ansible_sphinx
from pathlib import Path

ansible_sphinx.generate(
    # path to your collection
    Path(__file__).parent.parent / 'your_namespace/your_collection',
    # path to docs
    Path(__file__).parent,
)
```

This will document everything, also, you can cross-reference in the ``ansible``
domain created by this extension:

```
- :ansible:plugin:`your_namespace.your_collection.example`
- :ansible:options:`your_namespace.your_collection.example`
- :ansible:option:`your_namespace.your_collection.example.new`
- :ansible:return:`your_namespace.your_collection.example.message`
- :doc:`roles/lol`
- :doc:`modules/example`
```
