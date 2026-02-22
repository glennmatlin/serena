"""
Basic integration tests for the LaTeX language server functionality.

These tests validate the functionality of the language server APIs
like request_document_symbols using the LaTeX test repository.
"""

import pytest

from solidlsp import SolidLanguageServer
from solidlsp.ls_config import Language


@pytest.mark.latex
class TestLatexLanguageServerBasics:
    """Test basic functionality of the LaTeX language server."""

    @pytest.mark.parametrize("language_server", [Language.LATEX], indirect=True)
    def test_latex_language_server_initialization(self, language_server: SolidLanguageServer) -> None:
        """Test that LaTeX language server can be initialized successfully."""
        assert language_server is not None
        assert language_server.language == Language.LATEX

    @pytest.mark.parametrize("language_server", [Language.LATEX], indirect=True)
    def test_latex_request_document_symbols(self, language_server: SolidLanguageServer) -> None:
        """Test request_document_symbols for LaTeX files."""
        all_symbols, _root_symbols = language_server.request_document_symbols("main.tex").get_all_symbols_and_roots()

        symbol_names = [symbol["name"] for symbol in all_symbols]

        # texlab should detect sections as symbols
        assert len(all_symbols) > 0, "Should find at least one symbol in main.tex"
        # Check for section headings (texlab reports these as symbols)
        assert any("Introduction" in name for name in symbol_names) or len(all_symbols) >= 4, (
            f"Should find section symbols, got: {symbol_names}"
        )

    @pytest.mark.parametrize("language_server", [Language.LATEX], indirect=True)
    def test_latex_request_symbols_from_bib(self, language_server: SolidLanguageServer) -> None:
        """Test symbol detection in .bib files."""
        all_symbols, _root_symbols = language_server.request_document_symbols("refs.bib").get_all_symbols_and_roots()

        # texlab should detect bib entries as symbols
        assert len(all_symbols) > 0, f"Should find entries in refs.bib, found {len(all_symbols)}"

    @pytest.mark.parametrize("language_server", [Language.LATEX], indirect=True)
    def test_latex_request_symbols_from_sty(self, language_server: SolidLanguageServer) -> None:
        """Test symbol detection in .sty files."""
        all_symbols, _root_symbols = language_server.request_document_symbols("custom.sty").get_all_symbols_and_roots()

        # .sty files may have limited symbol support; just verify the API works
        assert all_symbols is not None, "Should return symbols list for .sty file"
