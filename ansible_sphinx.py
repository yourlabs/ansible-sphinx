import docutils
import functools
import json
import subprocess
import shutil
import textwrap
import yaml

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util import parsing
from sphinx.util.nodes import make_refnode


class AnsibleObject(ObjectDescription):
    """
    A directive to describe a ansibleramming object (like a role or plugin).
    """

    def rst_nodes(self, rst):
        return parsing.nested_parse_to_nodes(
            self.state,
            textwrap.dedent(rst).strip(),
        )

    def add_target_and_index(self, name, sig, signode):
        """
        Define a cross-reference target and add it to the index.
        """
        target_name = f'{self.name.replace(":", ".")}.{name}'
        if target_name not in self.env.domaindata['ansible']['objects']:
            self.env.domaindata['ansible']['objects'][target_name] = self.env.docname
            signode['ids'].append(target_name)

        self.indexnode['entries'].append(
            ('single', name, target_name, '', None)
        )

    def handle_signature(self, sig, signode):
        """
        Parse the object signature.
        - `sig`: The raw signature string.
        - `signode`: The node for rendering the signature.
        """
        name = sig.strip()
        signode += addnodes.desc_name(name, name)
        return name  # This name is used as a reference ID


class PluginMixin:
    @functools.cached_property
    def json(self):
        output = subprocess.check_output(
            f'ansible-doc -j {self.plugin_name}',
            shell=True,
        )
        return json.loads(output)[self.plugin_name]

    @functools.cached_property
    def plugin_name(self):
        return '.'.join(self.arguments[0].split('.')[:3]).split(' ')[0]

    @functools.cached_property
    def object_name(self):
        return self.arguments[0].split('.')[-1]


class AnsiblePluginDirective(PluginMixin, AnsibleObject):
    def run(self):
        nodes = super().run()
        rst = []
        for key, value in self.json.get('doc', {}).items():
            if key == 'examples':
                continue
            if isinstance(value, dict):
                continue
            if isinstance(value, list):
                value = ', '.join(value)
            rst.append(f'- **{key}**: {value}')
        nodes[1][1] += self.rst_nodes('\n'.join(rst))

        def _section_node(name):
            section_node = docutils.nodes.section()
            section_node['ids'].append(docutils.nodes.make_id(f'{self.arguments[0]}-{name.lower()}'))
            title_node = docutils.nodes.title(text=name)
            section_node += title_node
            return section_node

        if self.json.get('doc', {}).get('options', False):
            section_node = _section_node('Options')
            section_node += self.rst_nodes(f'.. ansible:options:: {self.arguments[0]}')
            nodes += section_node

        if 'examples' in self.json:
            section_node = _section_node('Examples')
            section_node += self.rst_nodes(f'.. ansible:examples:: {self.arguments[0]}')
            nodes += section_node

        if 'return' in self.json:
            section_node = _section_node('Return')
            section_node += self.rst_nodes(f'.. ansible:returns:: {self.arguments[0]}')
            nodes += section_node
        return nodes


class AnsiblePluginObjectsDirective(PluginMixin, AnsibleObject):
    def run(self):
        nodes = super().run()
        for name in self.object.keys():
            nodes[1][0] += self.rst_nodes(f'.. ansible:{self.typ}:: {self.plugin_name}.{name}\n')
        return nodes

    def handle_signature(self, sig, signode):
        return sig.strip()


class AnsiblePluginObjectDirective(PluginMixin, AnsibleObject):
    @functools.cached_property
    def object_name(self):
        return self.arguments[0].split('.')[-1]

    def run(self):
        nodes = super().run()
        data = self.object.copy()
        description = data.pop('description')
        if description:
            if isinstance(description, list):
                description = '\n\n'.join(description)
            nodes[1][1] += self.rst_nodes('\n' + description)
        rst = [
            f'- **{name}**: {" ".join(data) if isinstance(data, list) else data}'
            for name, data in data.items()
        ]
        nodes[1][1] += self.rst_nodes('\n'.join(rst))
        return nodes

    def handle_signature(self, sig, signode):
        name = sig.strip()
        signode += addnodes.desc_name(name, self.object_name)
        return name


class AnsiblePluginReturnsDirective(AnsiblePluginObjectsDirective):
    typ = 'return'

    @functools.cached_property
    def object(self):
        return self.json.get('return', None)


class AnsiblePluginReturnDirective(AnsiblePluginObjectDirective):
    @functools.cached_property
    def object(self):
        return self.json.get('return', {}).get(self.object_name)


class AnsiblePluginOptionsDirective(AnsiblePluginObjectsDirective):
    typ = 'option'

    @functools.cached_property
    def object(self):
        return self.json.get('doc', {}).get('options', {})


class AnsiblePluginOptionDirective(AnsiblePluginObjectDirective):
    @functools.cached_property
    def object(self):
        return self.json.get('doc', {}).get('options', {}).get(self.object_name)


class AnsiblePluginExamplesDirective(PluginMixin, AnsibleObject):
    @functools.cached_property
    def object(self):
        return self.json.get('examples', False)

    def run(self):
        nodes = super().run()
        wrapped = '\n  '.join(self.object.split('\n'))
        nodes[1][1] += self.rst_nodes(f'.. code:: yaml\n{wrapped}\n')
        return nodes

    def handle_signature(self, sig, signode):
        return sig.strip()


class AnsibleDomain(Domain):
    """
    A custom domain for ansibleramming-related constructs.
    """

    name = 'ansible'  # Domain name
    label = 'Ansible'  # Human-readable name
    object_types = {
        'role': ObjType('role', 'role'),
        'plugin': ObjType('plugin', 'plugin'),
        'option': ObjType('option', 'option'),
        'options': ObjType('options', 'options'),
        'return': ObjType('return', 'return'),
        'returns': ObjType('returns', 'returns'),
        'examples': ObjType('examples', 'examples'),
    }

    directives = {
        'plugin': AnsiblePluginDirective,
        'return': AnsiblePluginReturnDirective,
        'returns': AnsiblePluginReturnsDirective,
        'option': AnsiblePluginOptionDirective,
        'options': AnsiblePluginOptionsDirective,
        'examples': AnsiblePluginExamplesDirective,
    }

    roles = {
        'plugin': XRefRole(),
        'options': XRefRole(),
        'option': XRefRole(),
        'return': XRefRole(),
        'returns': XRefRole(),
        'examples': XRefRole(),
    }

    initial_data = {
        'objects': {},
    }

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        """
        Resolve a cross-reference.
        """
        target_name = f"ansible.{typ}.{target}"
        if target_name in self.data['objects']:
            return make_refnode(
                builder, fromdocname, self.data['objects'][target_name], target_name, contnode, target
            )


def setup(app):
    app.add_domain(AnsibleDomain)
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def collection_prefix(collection_path):
    with (collection_path / 'galaxy.yml').open('r') as f:
        data = yaml.safe_load(f.read())
    return '.'.join([data['namespace'], data['name']])


def generate_roles(collection_path, docs_path):
    source_path = collection_path / 'roles'
    docs_path = docs_path / 'roles'

    role_names = []
    docs_path.mkdir(exist_ok=True)
    for role_path in source_path.iterdir():
        readme = role_path / 'README.md'
        if not readme.exists():
            continue
        dest_path = docs_path / (role_path.name + '.md')
        role_names.append(role_path.name)
        shutil.copyfile(readme, dest_path)

    HEADER = '''Role documentation
==================

.. _Roles_list:

.. toctree::
   :maxdepth: 1
   :caption: Roles:
'''

    with (docs_path / 'index.rst').open('w+') as f:
        f.write(HEADER)
        for role_name in role_names:
            f.write('\n   ' + role_name)


def generate_modules(collection_path, docs_path):
    prefix = collection_prefix(collection_path)
    source_path = collection_path / 'plugins/modules'
    docs_path = docs_path / 'modules'

    module_names = []
    docs_path.mkdir(exist_ok=True)

    for module_path in source_path.iterdir():
        if module_path.name == '__init__.py':
            continue

        module_name = module_path.name[:-3]  # strip .py
        dest_path = docs_path / (module_name + '.rst')
        module_names.append(module_name)
        with dest_path.open('w') as f:
            f.write(
                textwrap.dedent(f'''
                {prefix}.{module_name}
                ===========================

                .. ansible:plugin:: {prefix}.{module_name}
                ''')
            )

    HEADER = '''Module documentation
====================

.. _modules_list:

.. toctree::
   :maxdepth: 1
   :caption: modules:
'''

    with (docs_path / 'index.rst').open('w+') as f:
        f.write(HEADER)
        for module_name in module_names:
            f.write('\n   ' + module_name)


def generate(collection_path, docs_path):
    generate_roles(collection_path, docs_path)
    generate_modules(collection_path, docs_path)
