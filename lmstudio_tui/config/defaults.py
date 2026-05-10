DEFAULT_CONFIG_TOML = """\
[[servers]]
name = "default"
endpoint = "http://localhost:1234"
api_key = ""

[benchmark]
default_prompt_set = "mixed"
default_samples = 10
warmup_runs = 2
export_dir = "~/.lmstudio-tui/benchmarks"

[ui]
poll_interval_s = 3.0
theme = "textual-dark"
"""
