from __future__ import annotations

from dataclasses import dataclass


# ── Tool schemas (OpenAI function calling format) ─────────────────────────

CALCULATOR_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Perform basic arithmetic: add, subtract, multiply, or divide two numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The arithmetic operation to perform.",
                },
                "a": {"type": "number", "description": "First operand."},
                "b": {"type": "number", "description": "Second operand."},
            },
            "required": ["operation", "a", "b"],
        },
    },
}

WEATHER_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a given city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name (e.g. 'Paris')."},
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit.",
                    "default": "celsius",
                },
            },
            "required": ["city"],
        },
    },
}

STRING_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "string_transform",
        "description": "Apply a transformation to a text string.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Input text."},
                "operation": {
                    "type": "string",
                    "enum": ["uppercase", "lowercase", "reverse", "word_count"],
                    "description": "Transformation to apply.",
                },
            },
            "required": ["text", "operation"],
        },
    },
}

SEARCH_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for information on a topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string."},
                "num_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}

ALL_TOOLS: list[dict] = [CALCULATOR_TOOL, WEATHER_TOOL, STRING_TOOL, SEARCH_TOOL]


# ── Test cases ────────────────────────────────────────────────────────────

@dataclass
class ToolTestCase:
    prompt: str
    tool_schema: dict
    expected_tool: str
    expected_args: dict
    description: str = ""


TOOL_TEST_CASES: list[ToolTestCase] = [
    # Calculator — unambiguous arithmetic
    ToolTestCase(
        prompt="What is 47 multiplied by 13?",
        tool_schema=CALCULATOR_TOOL,
        expected_tool="calculator",
        expected_args={"operation": "multiply", "a": 47, "b": 13},
        description="multiplication",
    ),
    ToolTestCase(
        prompt="Calculate 256 divided by 8.",
        tool_schema=CALCULATOR_TOOL,
        expected_tool="calculator",
        expected_args={"operation": "divide", "a": 256, "b": 8},
        description="division",
    ),
    ToolTestCase(
        prompt="Add 1024 and 768.",
        tool_schema=CALCULATOR_TOOL,
        expected_tool="calculator",
        expected_args={"operation": "add", "a": 1024, "b": 768},
        description="addition",
    ),
    ToolTestCase(
        prompt="Subtract 99 from 1000.",
        tool_schema=CALCULATOR_TOOL,
        expected_tool="calculator",
        expected_args={"operation": "subtract", "a": 1000, "b": 99},
        description="subtraction",
    ),
    # Weather — city extraction
    ToolTestCase(
        prompt="What is the current weather in Tokyo?",
        tool_schema=WEATHER_TOOL,
        expected_tool="get_weather",
        expected_args={"city": "Tokyo"},
        description="weather lookup",
    ),
    ToolTestCase(
        prompt="Is it cold in Berlin right now? Give me the temperature in Celsius.",
        tool_schema=WEATHER_TOOL,
        expected_tool="get_weather",
        expected_args={"city": "Berlin", "unit": "celsius"},
        description="weather with unit",
    ),
    # String transform
    ToolTestCase(
        prompt='Convert the text "Hello World" to uppercase.',
        tool_schema=STRING_TOOL,
        expected_tool="string_transform",
        expected_args={"text": "Hello World", "operation": "uppercase"},
        description="string uppercase",
    ),
    ToolTestCase(
        prompt='How many words are in the sentence "The quick brown fox jumps over the lazy dog"?',
        tool_schema=STRING_TOOL,
        expected_tool="string_transform",
        expected_args={"text": "The quick brown fox jumps over the lazy dog", "operation": "word_count"},
        description="word count",
    ),
    # Web search
    ToolTestCase(
        prompt="Search the web for information about LM Studio API.",
        tool_schema=SEARCH_TOOL,
        expected_tool="web_search",
        expected_args={"query": "LM Studio API"},
        description="web search",
    ),
    ToolTestCase(
        prompt="Find the top 3 results about Python async programming.",
        tool_schema=SEARCH_TOOL,
        expected_tool="web_search",
        expected_args={"query": "Python async programming", "num_results": 3},
        description="web search with count",
    ),
]


def get_tool_cases_for_mode(subset: str = "all") -> list[ToolTestCase]:
    """Return test cases; subset='all'|'calculator'|'weather'|'string'|'search'."""
    if subset == "all":
        return TOOL_TEST_CASES
    tag_map = {
        "calculator": "calculator",
        "weather": "get_weather",
        "string": "string_transform",
        "search": "web_search",
    }
    tool_name = tag_map.get(subset, subset)
    return [tc for tc in TOOL_TEST_CASES if tc.expected_tool == tool_name]
