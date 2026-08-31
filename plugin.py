from __future__ import annotations

import sublime
from LSP.plugin import (
    LspPlugin,
    OnPreStartContext,
    PluginStartError,
)

from .updater import Updater


class LspSystemdPlugin(LspPlugin):

    @classmethod
    def on_pre_start_async(cls, context: OnPreStartContext) -> None:
        desired_version = context.configuration.server_version 
        if desired_version is None or desired_version == "":
            desired_version = "latest"

        updater = Updater(cls.plugin_storage_path, sublime.platform(), sublime.arch())
        context.variables["server_file"] = str(updater.server_file())
        if updater.needs_update(desired_version):
            updater.download_binary(desired_version)
            if not updater.server_file().is_file():
                raise PluginStartError("Server binary missing after installation attempt")


def plugin_loaded() -> None:
    LspSystemdPlugin.register()


def plugin_unloaded() -> None:
    LspSystemdPlugin.unregister()
