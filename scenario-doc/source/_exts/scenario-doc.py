import os
from pathlib import Path
from typing import Any

from jinja2 import Template
import yaml

from docutils.nodes import literal, literal_block, paragraph, section, title
from docutils.parsers import rst
from docutils import statemachine
from docutils.parsers.rst.states import RSTState, RSTStateMachine
from docutils.statemachine import StringList
from sphinx.addnodes import toctree

__version__ = "1.0"
version_info = (1, 0)


class HotStackDirective(rst.Directive):

    has_content = True

    def __init__(self, name: str, arguments: list[str],
                 options: dict[str, Any], content: StringList, lineno: int,
                 content_offset: int, block_text: str, state: RSTState,
                 state_machine: RSTStateMachine):
        super(HotStackDirective, self).__init__(
            name, arguments, options, content, lineno, content_offset,
            block_text, state, state_machine)

        self.scenario_name = os.environ.get('SCENARIO')
        self.scenarios_dir = os.environ.get('SCENARIOS_DIR')
        self.scenario_dir = os.path.abspath(
            os.path.join(self.scenarios_dir, self.scenario_name))
        self.scenario_path = Path(self.scenario_dir)
        self.bootstrap_vars = None
        bootstrap_vars_path = list(self.scenario_path.glob('bootstrap_vars.yml'))
        if len(bootstrap_vars_path) > 0:
            with open(bootstrap_vars_path[0], 'r') as f:
                data = f.read()
            self.bootstrap_vars = yaml.safe_load(data)
        self.heat_template = None
        heat_template_path = list(self.scenario_path.glob('heat_template.yaml'))
        if len(heat_template_path) > 0:
            with open(heat_template_path[0], 'r') as f:
                data = f.read()
            self.heat_template = data

    def add_doc(self, doc, node):
        result = statemachine.ViewList()
        for line_num, line in enumerate(doc.splitlines(), 1):
            result.append(line, source='doc', offset=line_num)
        self.state.nested_parse(block=result, input_offset=1, node=node)

    @staticmethod
    def add_cmd(cmd, node):
        node += literal(text='Run command: ')
        node += literal_block(text=cmd)

    @staticmethod
    def add_script(script, node):
        node += literal(text='Run shell script: ')
        node += literal_block(text=script)

    def add_manifest(self, automation_dir, manifest, node):
        manifest_path = os.path.join(automation_dir, manifest)
        with open(manifest_path, 'r') as f:
            content = f.read()
        manifest_basename = os.path.basename(manifest)
        node += literal(text='File: {}'.format(manifest_basename))
        node += literal_block(text=content)
        node += literal(text='Apply the manifest:')
        node += literal_block(text='oc apply -f {}'.format(manifest_basename))

    def add_j2_manifest(self, automation_dir, j2_manifest, node):
        j2_manifest_path = os.path.join(automation_dir, j2_manifest)
        j2_manifest_basename = os.path.basename(j2_manifest)
        with open(j2_manifest_path, 'r') as f:
            content = f.read()
        manifest_name, _ = os.path.splitext(j2_manifest_basename)
        j2_template = Template(content)
        rendered_content = j2_template.render(self.bootstrap_vars)
        node += literal(text='File: {}'.format(manifest_name))
        node += literal_block(text=rendered_content)
        node += literal(text='Apply the manifest:')
        node += literal_block(text='oc apply -f {}'
                              .format(manifest_name))

    @staticmethod
    def add_wait_conditions(conditions, node):
        node += paragraph(text='Check that the resources was successfully '
                          'created, and is ready.')
        node += literal(text='Run wait command(s):')
        for condition in conditions:
            node += literal_block(text=condition)

    def process_stage(self, automation_dir, stage):
        name = stage.get('name')
        documentation = stage.get('documentation')
        cmd = stage.get('cmd')
        script = stage.get('script')
        manifest = stage.get('manifest')
        j2_manifest = stage.get('j2_manifest')
        wait_conditions = stage.get('wait_conditions', [])

        _node = section(ids=[name], name=name)
        _node += title(text=name)
        _node.document = self.state.document

        if documentation:
            self.add_doc(documentation, _node)
        if cmd:
            self.add_cmd(cmd, _node)
        if script:
            self.add_script(script, _node)
        if manifest:
            self.add_manifest(automation_dir, manifest, _node)
        if j2_manifest:
            self.add_j2_manifest(automation_dir, j2_manifest, _node)
        if wait_conditions:
            self.add_wait_conditions(wait_conditions, _node)

        return _node

    def add_heat_template(self):
        if self.heat_template is not None:
            node = section(ids=['heat_template'], name='Heat Template')
            node += title(text='Openstack Heat Template')

            text=('This heat template can be used with the roles in '
                  '`HotStack <https://github.com/openstack-k8s-operators/hoststack>`_ '
                  'to set up a virtual lab for this scenario on an '
                  'Openstack cloud.')
            self.add_doc(text, node)
            node += literal_block(text=self.heat_template)
            toctree.append(self.state.document, item=node)

    def run(self):
        automation_vars_paths = list(self.scenario_path.glob('**/automation-vars.yml'))
        _node = title(text=self.scenario_name)
        toctree.append(self.state.document, item=_node)

        self.add_heat_template()

        for path in automation_vars_paths:
            with open(path, 'r') as f:
                data = f.read()
            automation_dir = os.path.dirname(path)
            automation_vars = yaml.safe_load(data)
            for stage in automation_vars['stages']:
                toctree.append(self.state.document, item=self.process_stage(automation_dir, stage))

        return []

def setup(app):
    app.add_directive('hotstack-automation', HotStackDirective)

    return {
        "parallel_read_safe": True,
        "version": __version__,
    }

