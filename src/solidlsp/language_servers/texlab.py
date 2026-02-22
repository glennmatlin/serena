"""
Provides LaTeX specific instantiation of the LanguageServer class using texlab.
Contains various configurations and settings specific to LaTeX.
"""

import logging
import os
import pathlib

from overrides import override

from solidlsp.ls import LanguageServerDependencyProvider, LanguageServerDependencyProviderSinglePath, SolidLanguageServer
from solidlsp.ls_config import LanguageServerConfig
from solidlsp.lsp_protocol_handler.lsp_types import InitializeParams
from solidlsp.settings import SolidLSPSettings

from .common import RuntimeDependency, RuntimeDependencyCollection

log = logging.getLogger(__name__)


class Texlab(SolidLanguageServer):
    """
    Provides LaTeX specific instantiation of the LanguageServer class using texlab.
    """

    class DependencyProvider(LanguageServerDependencyProviderSinglePath):
        texlab_releases = "https://github.com/latex-lsp/texlab/releases/download/v5.25.1"
        runtime_dependencies = RuntimeDependencyCollection(
            [
                RuntimeDependency(
                    id="texlab",
                    url=f"{texlab_releases}/texlab-x86_64-linux.tar.gz",
                    platform_id="linux-x64",
                    archive_type="gztar",
                    binary_name="texlab",
                ),
                RuntimeDependency(
                    id="texlab",
                    url=f"{texlab_releases}/texlab-aarch64-linux.tar.gz",
                    platform_id="linux-arm64",
                    archive_type="gztar",
                    binary_name="texlab",
                ),
                RuntimeDependency(
                    id="texlab",
                    url=f"{texlab_releases}/texlab-x86_64-macos.tar.gz",
                    platform_id="osx-x64",
                    archive_type="gztar",
                    binary_name="texlab",
                ),
                RuntimeDependency(
                    id="texlab",
                    url=f"{texlab_releases}/texlab-aarch64-macos.tar.gz",
                    platform_id="osx-arm64",
                    archive_type="gztar",
                    binary_name="texlab",
                ),
                RuntimeDependency(
                    id="texlab",
                    url=f"{texlab_releases}/texlab-x86_64-windows.zip",
                    platform_id="win-x64",
                    archive_type="zip",
                    binary_name="texlab.exe",
                ),
            ]
        )

        def _get_or_install_core_dependency(self) -> str:
            """Setup runtime dependencies for texlab and return the path to the executable."""
            deps = self.runtime_dependencies
            dependency = deps.get_single_dep_for_current_platform()

            texlab_ls_dir = self._ls_resources_dir
            texlab_executable_path = deps.binary_path(texlab_ls_dir)
            if not os.path.exists(texlab_executable_path):
                log.info(
                    f"Downloading texlab from {dependency.url} to {texlab_ls_dir}",
                )
                deps.install(texlab_ls_dir)
            if not os.path.exists(texlab_executable_path):
                raise FileNotFoundError(f"Download failed? Could not find texlab executable at {texlab_executable_path}")
            os.chmod(texlab_executable_path, 0o755)
            return texlab_executable_path

        def _create_launch_command(self, core_path: str) -> list[str]:
            return [core_path]

    def __init__(self, config: LanguageServerConfig, repository_root_path: str, solidlsp_settings: SolidLSPSettings):
        """
        Creates a Texlab instance. This class is not meant to be instantiated directly.
        Use LanguageServer.create() instead.
        """
        super().__init__(
            config,
            repository_root_path,
            None,
            "latex",
            solidlsp_settings,
        )

    def _create_dependency_provider(self) -> LanguageServerDependencyProvider:
        return self.DependencyProvider(self._custom_settings, self._ls_resources_dir)

    @override
    def is_ignored_dirname(self, dirname: str) -> bool:
        return super().is_ignored_dirname(dirname) or dirname in ["_minted", "auto", "pythontex-files-"]

    @staticmethod
    def _get_initialize_params(repository_absolute_path: str) -> InitializeParams:
        """
        Returns the initialize params for the texlab Language Server.
        """
        root_uri = pathlib.Path(repository_absolute_path).as_uri()
        initialize_params: InitializeParams = {  # type: ignore
            "processId": os.getpid(),
            "locale": "en",
            "rootPath": repository_absolute_path,
            "rootUri": root_uri,
            "capabilities": {
                "textDocument": {
                    "synchronization": {"didSave": True, "dynamicRegistration": True},
                    "completion": {
                        "dynamicRegistration": True,
                        "completionItem": {"snippetSupport": True},
                    },
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True},
                    "documentSymbol": {
                        "dynamicRegistration": True,
                        "hierarchicalDocumentSymbolSupport": True,
                        "symbolKind": {"valueSet": list(range(1, 27))},  # type: ignore[arg-type]
                    },
                    "hover": {
                        "dynamicRegistration": True,
                        "contentFormat": ["markdown", "plaintext"],  # type: ignore[list-item]
                    },
                    "codeAction": {"dynamicRegistration": True},
                    "formatting": {"dynamicRegistration": True},
                },
                "workspace": {
                    "workspaceFolders": True,
                    "didChangeConfiguration": {"dynamicRegistration": True},
                    "symbol": {"dynamicRegistration": True},
                },
            },
            "workspaceFolders": [
                {
                    "uri": root_uri,
                    "name": os.path.basename(repository_absolute_path),
                }
            ],
        }
        return initialize_params

    def _start_server(self) -> None:
        """
        Starts the texlab Language Server and waits for it to be ready.
        """

        def register_capability_handler(_params: dict) -> None:
            return

        def window_log_message(msg: dict) -> None:
            log.info(f"LSP: window/logMessage: {msg}")

        def do_nothing(_params: dict) -> None:
            return

        self.server.on_request("client/registerCapability", register_capability_handler)
        self.server.on_notification("window/logMessage", window_log_message)
        self.server.on_notification("$/progress", do_nothing)
        self.server.on_notification("textDocument/publishDiagnostics", do_nothing)

        log.info("Starting texlab server process")
        self.server.start()
        initialize_params = self._get_initialize_params(self.repository_root_path)

        log.info("Sending initialize request from LSP client to texlab server and awaiting response")
        init_response = self.server.send.initialize(initialize_params)
        log.debug(f"Received initialize response from texlab server: {init_response}")

        # Verify server capabilities
        assert "textDocumentSync" in init_response["capabilities"]
        assert "completionProvider" in init_response["capabilities"]
        assert "definitionProvider" in init_response["capabilities"]

        self.server.notify.initialized({})

        log.info("Texlab server initialization complete")
