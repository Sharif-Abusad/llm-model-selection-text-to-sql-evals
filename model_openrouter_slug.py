"""
The 5 or 3 models under test, as OpenRouter slugs.
Kept as a list of (display_name, slug) so output table show friendly names.
"""
MODELS = [
    # ("GPT-5.6 Terra", "openai/gpt-5.6-terra-pro"),
    ("Kimi K3", "moonshotai/kimi-k3"),
    ("Grok 4.5", "x-ai/grok-4.5"),
    # ("Claude Sonnet 5", "anthropic/claude-sonnet-5"),
    ("Minimax M3", "minimax/minimax-m3")
]

if __name__ == '__main__':
    print(f"{len(MODELS)} models under test:")
    for name, slug in MODELS:
        print(f"  {name:18s} -> {slug}")