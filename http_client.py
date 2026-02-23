import asyncio
import json
import logging
from logging_setup import setup_colored_logger
from typing import Any, Dict, List, Optional, Callable
from mcp.client.streamable_http import streamable_http_client
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
import mcp.types as types


class MCPInteractiveHTTPClient:
    """
    Interactive MCP client using ClientSession, with pluggable transport:
    - transport="http": streamable-http transport via /mcp
    - transport="sse":  SSE transport via /sse

    Defines:
    - MCPInteractiveHTTPClient:
        Wrapper around mcp.client.session.ClientSession with an interactive CLI:
        - initialize MCP session
        - list tools and let the user choose one
        - show tool argument schema and prompt for values
        - call the tool and pretty-print the result
        - optional logging setup via `activate_logger` argument

    Constructor:
        MCPInteractiveHTTPClient(
            url: str,
            transport: str = "http",       # "http" (streamable-http) or "sse"
            activate_logger: bool = True,  # configure logging on first use if True
        )

    Example usage:
        from http_client import MCPInteractiveHTTPClient
        import asyncio

        HTTP_URL = "http://localhost:8000/mcp"
        SSE_URL = "http://localhost:8000/sse"

        async def main_http():
            async with MCPInteractiveHTTPClient(
                HTTP_URL,
                transport="http",
                activate_logger=True,
            ) as client:
                await client.run()

        async def main_sse():
            async with MCPInteractiveHTTPClient(
                SSE_URL,
                transport="sse",
                activate_logger=True,
            ) as client:
                await client.run()

        if __name__ == "__main__":
            asyncio.run(main_http())
    """

    def __init__(
        self,
        url: str,
        transport: str = "http",
        activate_logger: bool = True,
    ):
        """
        Initialize an interactive MCP client.

        :param url: Base URL for the MCP endpoint (e.g. http://localhost:8000/mcp or /sse).
        :param transport: "http" for streamable-http, "sse" for SSE transport.
        :param activate_logger: If True, configure logging (info in green) on first instantiation.
        """
        self.url = url
        self.transport = transport
        self._ctx = None
        self._read_stream = None
        self._write_stream = None
        # Callable that returns the session id (only set for streamable-http transport)
        self._get_session_id: Optional[Callable[[], str]] = None
        self._session: Optional[ClientSession] = None

        # logger for this class/module
        self.logger = logging.getLogger("MCPInteractiveHTTPClient")

        # configure logging once
        if activate_logger:
            # if no handlers are configured, set up the info-green logger
            if not logging.getLogger().handlers:
                setup_colored_logger(logging.INFO)
            self.logger.info("Logger activated for MCPInteractiveHTTPClient")

    async def __aenter__(self) -> "MCPInteractiveHTTPClient":
        """
        Open the chosen transport and wrap it in a ClientSession.

        :return: Self, with active transport and ClientSession.
        """
        self.logger.info(
            "Opening interactive client (transport=%s, url=%s)",
            self.transport,
            self.url,
        )
        try:
            if self.transport == "http":
                # streamable-http client context
                self._ctx = streamable_http_client(self.url, terminate_on_close=True)
                (
                    self._read_stream,
                    self._write_stream,
                    self._get_session_id,
                ) = await self._ctx.__aenter__()
                session_id = self._get_session_id() if self._get_session_id else None
                self.logger.info(
                    "Streamable-http session started (session_id=%s)", session_id
                )
            elif self.transport == "sse":
                # SSE client context
                self._ctx = sse_client(self.url)
                self._read_stream, self._write_stream = await self._ctx.__aenter__()
                self.logger.info("SSE connection established")
            else:
                # invalid transport configuration
                self.logger.error("Unknown client transport: '%s'", self.transport)
                raise ValueError(f"Unknown client transport: {self.transport}")

            # create MCP client session on top of the chosen transport streams
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.__aenter__()
            self.logger.info("ClientSession successfully entered")
            return self
        except Exception as e:
            # include traceback for easier debugging
            self.logger.error("Failed to open interactive client: %s", e, exc_info=True)
            raise

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """
        Close ClientSession and underlying transport.

        :param exc_type: Exception type if an exception was raised in the context.
        :param exc: Exception instance if an exception was raised in the context.
        :param tb: Traceback if an exception was raised in the context.
        :return: None
        """
        self.logger.info("Closing interactive client")
        try:
            if self._session is not None:
                await self._session.__aexit__(exc_type, exc, tb)
                self.logger.info("ClientSession closed")
        except Exception as e:
            self.logger.error("Error while closing ClientSession: %s", e, exc_info=True)

        try:
            if self._ctx is not None:
                await self._ctx.__aexit__(exc_type, exc, tb)
                self.logger.info("Transport context closed")
        except Exception as e:
            self.logger.error(
                "Error while closing transport context: %s", e, exc_info=True
            )

    async def initialize(self) -> None:
        """
        Perform MCP initialize handshake via ClientSession.

        :raises RuntimeError: If the session has not been started.
        :return: None
        """
        if self._session is None:
            raise RuntimeError("Session not started")

        self.logger.info("Initializing MCP session")
        try:
            await self._session.initialize()
            self.logger.info("MCP session successfully initialized")
        except Exception as e:
            self.logger.error("Initialize failed: %s", e, exc_info=True)
            raise

    async def list_tools(self) -> List[types.Tool]:
        """
        Fetch and return the list of available tools from the MCP server.

        :raises RuntimeError: If the session has not been started.
        :return: List of Tool objects provided by the MCP server.
        """
        if self._session is None:
            raise RuntimeError("Session not started")

        self.logger.info("Requesting tools/list")
        try:
            tools_result = await self._session.list_tools()
        except Exception as e:
            self.logger.error("tools/list failed: %s", e, exc_info=True)
            raise

        self.logger.info("Received %d tools", len(tools_result.tools))
        return tools_result.tools

    async def list_tools_simple(self) -> List[str]:
        """
        Convenience method: return only the tool names as a simple list of strings.

        Useful for programmatic usage without the interactive CLI layer.
        """
        tools = await self.list_tools()
        return [t.name for t in tools]

    def choose_tool(self, tools: List[types.Tool]) -> Optional[types.Tool]:
        """
        Print the list of tools and let the user select one by number.

        :param tools: List of Tool objects to choose from.
        :return: The chosen Tool object, or None if selection is invalid or list is empty.
        """
        if not tools:
            return None

        print("\nAvailable tools:")
        for i, tool in enumerate(tools, start=1):
            print(f"{i}. {tool.name} - {tool.description or ''}")

        choice = input("\nSelect a tool by number: ").strip()
        try:
            idx = int(choice)
            if 1 <= idx <= len(tools):
                chosen = tools[idx - 1]
                self.logger.info("User selected tool: '%s'", chosen.name)
                return chosen
        except ValueError:
            self.logger.warning("User entered invalid tool index: '%s'", choice)

        return None

    def _parse_schema_value(
        self, prop_name: str, prop_type: str, value_str: str
    ) -> Any:
        """
        Helper to parse a single schema value from a string based on JSON Schema type.

        Supports:
        - string, integer, number, boolean
        - array, object (JSON)

        :param prop_name: Name of the property.
        :param prop_type: JSON schema type (string, integer, ...).
        :param value_str: Raw input string from the user.
        :return: Parsed Python value.
        :raises ValueError: If parsing fails.
        """
        if prop_type == "integer":
            return int(value_str)
        elif prop_type == "number":
            return float(value_str)
        elif prop_type == "boolean":
            lower = value_str.lower()
            if lower in ("true", "1", "yes", "y"):
                return True
            if lower in ("false", "0", "no", "n"):
                return False
            raise ValueError("Please enter true/false.")
        elif prop_type in ("array", "object"):
            # For arrays and objects we expect valid JSON from the user.
            # This keeps the CLI simple but allows complex arguments.
            try:
                return json.loads(value_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Please enter valid JSON for {prop_type}: {e}") from e
        else:
            # default: treat as string
            return value_str

    def prompt_arguments_for_tool(self, tool: types.Tool) -> Dict[str, Any]:
        """
        Prompt the user for argument values based on the tool's input schema.

        Supports basic JSON schema types:
        - string, integer, number, boolean
        - array, object (JSON)
        and respects "required" properties.

        :param tool: Tool whose inputSchema should be used to prompt for arguments.
        :return: Dictionary of argument values keyed by property name.
        """
        name = tool.name
        input_schema = tool.inputSchema or {}
        schema_props = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        print(f"\nTool '{name}' argument schema:")
        if not schema_props:
            print("  (no schema provided, using empty arguments {})")
            self.logger.info(
                "Tool '%s' has no input schema; using empty arguments", name
            )
            return {}

        arguments: Dict[str, Any] = {}

        for prop_name, prop_def in schema_props.items():
            desc = prop_def.get("description", "")
            prop_type = prop_def.get("type", "string")
            is_required = prop_name in required

            label = f"{prop_name} ({prop_type})"
            if desc:
                label += f" - {desc}"
            label += " [required]" if is_required else " [optional]"

            # for array/object
            if prop_type in ("array", "object"):
                label += " (enter JSON value)"

            while True:
                value_str = input(f"{label}: ").strip()

                if not value_str:
                    if is_required:
                        print("This field is required.")
                        self.logger.warning(
                            "Required field '%s' left empty by user", prop_name
                        )
                        continue
                    # optional & empty -> do not set
                    break

                try:
                    value = self._parse_schema_value(prop_name, prop_type, value_str)
                except ValueError as e:
                    print(e)
                    self.logger.warning(
                        "Invalid value for '%s': '%s' (%s)",
                        prop_name,
                        value_str,
                        e,
                    )
                    continue

                arguments[prop_name] = value
                break

        self.logger.info("Collected arguments for tool '%s': '%s'", name, arguments)
        return arguments

    async def call_tool(
        self, tool: types.Tool, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call the given tool with provided arguments and return the raw result dict.

        This is the interactive variant used by the CLI:
        - prints arguments
        - prints raw JSON result
        - prints a slightly post-processed "final" result (mainly for readability)

        :param tool: Tool to call.
        :param arguments: Arguments dictionary to pass to the tool.
        :raises RuntimeError: If the session has not been started.
        :return: Raw result dictionary from the tool call.
        """
        if self._session is None:
            raise RuntimeError("Session not started")

        self.logger.info("Calling tool '%s'", tool.name)
        print(f"\nCalling tool '{tool.name}' with arguments:")
        print(json.dumps(arguments, indent=2))

        try:
            call_result = await self._session.call_tool(
                name=tool.name,
                arguments=arguments,
            )
            result_dict = call_result.model_dump(mode="json")
        except Exception as e:
            self.logger.error(
                "Tool call for '%s' failed: %s", tool.name, e, exc_info=True
            )
            raise

        # Pretty-print raw JSON result
        result_json_str = json.dumps(result_dict, indent=2)
        print("\n[TOOL RESULT (raw JSON)]")
        print(result_json_str)

        result_final = result_json_str.replace("\\n", "\n")
        result_final = result_final.replace("\\", "")

        print(
            "\n[FINAL RESULT (rendered for readability, JSON formatting may be invalid)]"
        )
        print(result_final)

        return result_dict

    async def call_tool_by_name(
        self, name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convenience method: Call a tool by name with given arguments and return the raw result dict.

        This method is intended for programmatic use without the interactive CLI.
        It does not print anything by itself, only logs.

        :param name: Tool name to call.
        :param arguments: Arguments dictionary to pass to the tool.
        :raises RuntimeError: If the session has not been started.
        :return: Raw result dictionary from the tool call.
        """
        if self._session is None:
            raise RuntimeError("Session not started")

        self.logger.info("Calling tool by name '%s' (non-interactive)", name)
        try:
            call_result = await self._session.call_tool(
                name=name,
                arguments=arguments,
            )
            return call_result.model_dump(mode="json")
        except Exception as e:
            self.logger.error(
                "Non-interactive tool call for '%s' failed: %s", name, e, exc_info=True
            )
            raise

    async def run(self) -> None:
        """
        High-level interactive loop:
        - initialize session
        - list tools
        - repeatedly:
            * let user choose a tool
            * prompt for arguments
            * call the tool
            * pretty-print the result
            * ask if the user wants to call another tool

        This is mainly intended for manual testing / exploration of an MCP server.

        :return: None
        """
        try:
            await self.initialize()
            tools = await self.list_tools()
        except Exception as e:
            self.logger.error("Failed to start interactive loop: %s", e, exc_info=True)
            return

        if not tools:
            print("No tools available.")
            self.logger.warning("Server returned no tools")
            return

        while True:
            try:
                chosen_tool = self.choose_tool(tools)
                if chosen_tool is None:
                    # invalid selection, re-prompt
                    continue

                arguments = self.prompt_arguments_for_tool(chosen_tool)
                _ = await self.call_tool(chosen_tool, arguments)
            except Exception as e:
                self.logger.error(
                    "Error during interactive tool call: %s", e, exc_info=True
                )
                break

            again = input("\nCall another tool? [y/n]: ").strip().lower()
            if again in ("n", "no", ""):
                self.logger.info("User chose to exit interactive loop")
                break
