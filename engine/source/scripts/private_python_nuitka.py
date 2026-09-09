import sys

from nuitka.plugins.PluginBase import NuitkaPluginBase


class PrivatePythonRuntime(NuitkaPluginBase):
    plugin_name = "private-python-runtime"
    plugin_desc = "Package the pinned Python runtime and its subprocess entry points."

    def decideAllowOutsideDependencies(self, module_name):
        if sys.platform == "darwin" and module_name.asString() in {"_ssl", "_hashlib", "_curses", "_curses_panel", "_tkinter"}:
            return True
        return None

    def onModuleSourceCode(self, module_name, source_filename, source_code):
        if module_name.asString() != "multiprocessing.resource_tracker":
            return source_code
        current = "'-c',\n                f'from multiprocessing.resource_tracker import main;main({r})'"
        if current in source_code:
            return source_code.replace(current, "'--multiprocessing-resource-tracker', str(r)")
        return source_code
