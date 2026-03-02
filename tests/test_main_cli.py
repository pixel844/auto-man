from pathlib import Path
from unittest.mock import Mock, patch

from auto_man import main


class TestMain:
    """Test the main CLI entry point."""

    def test_run_reset_mode(self):
        """Test reset mode functionality."""
        with (
            patch("auto_man.cli.Rag") as mock_rag_class,
            patch("auto_man.cli.get_models_dir") as mock_get_models,
        ):

            mock_rag_instance = Mock()
            mock_rag_class.return_value = mock_rag_instance
            mock_models_dir = Mock()
            mock_models_dir.exists.return_value = False  # Skip the directory iteration
            mock_get_models.return_value = mock_models_dir

            with patch("sys.exit") as mock_exit:
                main.run_reset_mode()

            mock_rag_instance.cleanup.assert_called_once()
            mock_exit.assert_called_once_with(0)

    @patch("auto_man.main.get_models_dir")
    @patch("auto_man.main.select_model")
    @patch("auto_man.main.LlmEngine", new_callable=Mock)
    @patch("auto_man.main.Rag", new_callable=Mock)
    @patch("auto_man.main.run_mcp_mode")
    def test_main_mcp_mode(
        self, mock_run_mcp, mock_rag_class, mock_llm_class, mock_select, mock_models_dir
    ):
        """Test main with --mcp flag."""
        mock_models_dir.return_value = Path("/models")
        mock_select.return_value = Path("/models/test")

        # Configure mock rag instance to have cleanup method
        mock_rag_instance = Mock()
        mock_rag_class.return_value = mock_rag_instance

        # Configure mock llm instance to have model_name
        mock_llm_instance = Mock()
        mock_llm_instance.model_name = "test-model"
        mock_llm_class.return_value = mock_llm_instance

        with patch("sys.argv", ["main.py", "--mcp"]), patch("sys.stdin") as mock_stdin:
            # Mock stdin.readline to return empty string to exit the loop
            mock_stdin.readline.return_value = ""
            main.main()

        mock_run_mcp.assert_called_once()
        mock_rag_instance.cleanup.assert_called_once()

    @patch("auto_man.main.get_models_dir")
    @patch("auto_man.main.select_model")
    @patch("auto_man.main.LlmEngine", new_callable=Mock)
    @patch("auto_man.main.Rag", new_callable=Mock)
    @patch("auto_man.main.run_single_prompt")
    def test_main_single_prompt(
        self,
        mock_run_prompt,
        mock_rag_class,
        mock_llm_class,
        mock_select,
        mock_models_dir,
    ):
        """Test main with --prompt flag."""
        mock_models_dir.return_value = Path("/models")
        mock_select.return_value = Path("/models/test")

        # Configure mock rag instance to have cleanup method
        mock_rag_instance = Mock()
        mock_rag_class.return_value = mock_rag_instance

        # Configure mock llm instance to have model_name
        mock_llm_instance = Mock()
        mock_llm_instance.model_name = "test-model"
        mock_llm_class.return_value = mock_llm_instance

        with patch("sys.argv", ["main.py", "--prompt", "test prompt"]):
            main.main()

        mock_run_prompt.assert_called_once()
        mock_rag_instance.cleanup.assert_called_once()

    @patch("auto_man.main.get_models_dir")
    @patch("auto_man.main.select_model")
    @patch("auto_man.main.LlmEngine", new_callable=Mock)
    @patch("auto_man.main.Rag", new_callable=Mock)
    @patch("auto_man.main.run_repo_manual_flow")
    @patch("builtins.input", return_value="https://github.com/user/repo")
    def test_main_default_flow(
        self,
        mock_input,
        mock_run_flow,
        mock_rag_class,
        mock_llm_class,
        mock_select,
        mock_models_dir,
    ):
        """Test main default flow with repo URL."""
        mock_models_dir.return_value = Path("/models")
        mock_select.return_value = Path("/models/test")

        # Configure mock rag instance to have cleanup method
        mock_rag_instance = Mock()
        mock_rag_class.return_value = mock_rag_instance

        # Configure mock llm instance to have model_name
        mock_llm_instance = Mock()
        mock_llm_instance.model_name = "test-model"
        mock_llm_class.return_value = mock_llm_instance

        with patch("sys.argv", ["main.py"]):
            main.main()

        mock_run_flow.assert_called_once()
        mock_rag_instance.cleanup.assert_called_once()

    @patch("auto_man.main.get_models_dir")
    @patch("auto_man.main.select_model")
    @patch("auto_man.main.LlmEngine", new_callable=lambda: Mock)
    @patch("auto_man.main.Rag")
    @patch("builtins.input", return_value="")
    def test_main_default_flow_empty_repo(
        self, mock_input, mock_rag_class, mock_llm_class, mock_select, mock_models_dir
    ):
        """Test main default flow with empty repo URL."""
        mock_models_dir.return_value = Path("/models")
        mock_select.return_value = Path("/models/test")

        with patch("sys.argv", ["main.py"]):
            main.main()

        # Should not initialize engines with empty repo
        mock_llm_class.assert_not_called()
        mock_rag_class.assert_not_called()

    @patch("sys.exit")
    @patch.object(main, "run_reset_mode")
    @patch("auto_man.main.LlmEngine", new_callable=Mock)
    @patch("auto_man.main.Rag", new_callable=Mock)
    @patch("builtins.input", return_value="")
    def test_reset_exits_early(
        self, mock_input, mock_rag_class, mock_llm_class, mock_reset, mock_exit
    ):
        """Test that --reset exits early."""
        # Configure mock reset to call sys.exit
        mock_reset.side_effect = lambda: mock_exit(0)

        with (
            patch("sys.argv", ["main.py", "--reset"]),
            patch("sys.stdin", side_effect=[""]),
        ):  # Mock stdin to avoid capture issues
            try:
                main.main()
            except SystemExit:
                pass

        mock_reset.assert_called_once()
        mock_exit.assert_called_once_with(0)
        # Should not initialize engines when --reset is used
        mock_llm_class.assert_not_called()
        mock_rag_class.assert_not_called()


class TestCliFunctions:
    """Test CLI workflow functions."""

    def test_run_reset_mode(self):
        """Test reset mode functionality."""
        with (
            patch("auto_man.cli.Rag") as mock_rag_class,
            patch("auto_man.cli.get_models_dir") as mock_get_models,
        ):

            mock_rag_instance = Mock()
            mock_rag_class.return_value = mock_rag_instance
            mock_models_dir = Mock()
            mock_models_dir.exists.return_value = False  # Skip directory iteration
            mock_get_models.return_value = mock_models_dir

            with patch("sys.exit") as mock_exit:
                main.run_reset_mode()

            mock_rag_instance.cleanup.assert_called_once()
            mock_exit.assert_called_once_with(0)

    @patch("auto_man.cli.json.loads")
    @patch("builtins.print")
    @patch("sys.stdin")
    def test_run_mcp_mode(
        self, mock_stdin, mock_print, mock_json_loads, mock_llm_engine, mock_rag
    ):
        """Test MCP server mode."""
        # Mock stdin to return empty lines (exit condition)
        mock_stdin.readline.side_effect = ["", ""]

        mock_json_loads.return_value = {"method": "test"}

        with patch("auto_man.cli.McpServer") as mock_server_class:
            mock_server = Mock()
            mock_server_class.return_value = mock_server
            mock_server.handle_request.return_value = {"result": "test"}

            main.run_mcp_mode(mock_llm_engine, mock_rag)

            mock_server_class.assert_called_once_with(mock_llm_engine, mock_rag)

    def test_run_single_prompt(self):
        """Test single prompt execution."""
        mock_llm_engine = Mock()
        mock_llm_engine.model_name = "test-model"
        main.run_single_prompt(mock_llm_engine, "test prompt")

        # Should call generate with tagged prompt
        mock_llm_engine.generate.assert_called_once()
        args, kwargs = mock_llm_engine.generate.call_args
        prompt = args[0]
        assert "test prompt" in prompt

    def test_run_repo_manual_flow(self, mock_llm_engine, mock_rag):
        """Test repository manual generation flow."""
        with (
            patch("auto_man.cli.generate_manual") as mock_generate,
            patch("auto_man.cli.McpServer") as mock_server_class,
            patch("builtins.input", return_value="y"),
        ):

            mock_server = Mock()
            mock_server_class.return_value = mock_server
            mock_server.handle_request.side_effect = [
                {"result": {"content": [{"text": "tree"}]}},  # fetch_tree
                {
                    "result": {"content": [{"text": "Added repo with ID: repo-123"}]}
                },  # add_repo
                {
                    "result": {"content": [{"text": "Index success: True"}]}
                },  # index_repo
            ]

            main.run_repo_manual_flow(
                mock_llm_engine, mock_rag, "https://github.com/user/repo"
            )

            mock_generate.assert_called_once()
            # Should have made the expected MCP calls
            assert mock_server.handle_request.call_count == 3
