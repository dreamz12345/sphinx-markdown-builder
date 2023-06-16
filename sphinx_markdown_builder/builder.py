"""
docutils XML to markdown translator.
"""
import os
from typing import Set

from docutils import nodes
from docutils.io import StringOutput
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.environment import BuildEnvironment
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.osutil import ensuredir, os_path

from sphinx_markdown_builder.translator import MarkdownTranslator
from sphinx_markdown_builder.writer import MarkdownWriter

logger = logging.getLogger(__name__)


def get_mod_time_if_exists(file_path):
    try:
        return os.path.getmtime(file_path)
    except OSError:
        return 0


class MarkdownBuilder(Builder):
    name = "markdown"
    format = "markdown"
    epilog = __("The markdown files are in %(outdir)s.")

    allow_parallel = True
    default_translator_class = MarkdownTranslator

    out_suffix = ".md"

    def __init__(self, app: Sphinx, env: BuildEnvironment = None):
        super().__init__(app, env)
        self.writer = None
        self.sec_numbers = None
        self.current_doc_name = None
        self.insert_anchors_for_signatures = False

    def init(self):
        self.sec_numbers = {}

    def get_outdated_docs(self):
        for doc_name in self.env.found_docs:
            if doc_name not in self.env.all_docs:
                yield doc_name
                continue
            target_name = os.path.join(self.outdir, doc_name + self.out_suffix)
            target_mtime = get_mod_time_if_exists(target_name)
            try:
                src_mtime = get_mod_time_if_exists(self.env.doc2path(doc_name))
                if src_mtime > target_mtime:
                    yield doc_name
            except EnvironmentError:
                pass

    def get_target_uri(self, docname: str, typ: str = None):
        """
        Returns the target file name.
        By default, we link to the currently generated markdown files.
        But, we also support linking to external document (e.g., an html web page).
        """
        return f"{docname}{self.config.markdown_uri_doc_suffix}"

    def prepare_writing(self, docnames: Set[str]):
        self.writer = MarkdownWriter(self)

    def write_doc(self, docname: str, doctree: nodes.document):
        self.current_doc_name = docname
        self.sec_numbers = self.env.toc_secnumbers.get(docname, {})
        destination = StringOutput(encoding="utf-8")
        self.writer.write(doctree, destination)
        out_filename = os.path.join(self.outdir, os_path(docname) + self.out_suffix)
        ensuredir(os.path.dirname(out_filename))

        try:
            with open(out_filename, "w", encoding="utf-8") as file:
                file.write(self.writer.output)
        except (IOError, OSError) as err:
            logger.warning(__("error writing file %s: %s"), out_filename, err)
