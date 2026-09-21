"""Render a "most used languages" card for the profile README.

Sums the bytes of each language across the user's own public repositories
(forks and archived repos excluded) and writes a dark and a light SVG.
Standard library only; set GITHUB_TOKEN to avoid the anonymous rate limit.

    python .github/scripts/languages_card.py Zeeshan-szf cards
"""

import json
import os
import sys
import urllib.request
from html import escape

API = "https://api.github.com"
TOP = 4  # languages shown by name; the rest are summed into "Other"

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
THEMES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "t1": "#e6edf3", "t2": "#9198a1", "bar": "#3987e5"},
    "light": {"bg": "#ffffff", "border": "#d1d9e0", "t1": "#1f2328", "t2": "#59636e", "bar": "#2a78d6"},
}


def get(url: str):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "languages-card"})
    if token := os.getenv("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def language_bytes(user: str) -> dict[str, int]:
    totals: dict[str, int] = {}
    page = 1
    while repos := get(f"{API}/users/{user}/repos?type=owner&per_page=100&page={page}"):
        for repo in repos:
            if repo["fork"] or repo["archived"]:
                continue
            for language, size in get(repo["languages_url"]).items():
                totals[language] = totals.get(language, 0) + size
        page += 1
    return totals


def top_rows(totals: dict[str, int]) -> list[tuple[str, float]]:
    total = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda item: -item[1])
    rows = [(name, size / total * 100) for name, size in ranked[:TOP]]
    rest = sum(size for _, size in ranked[TOP:])
    if rest:
        rows.append(("Other", rest / total * 100))
    return rows


def pct(value: float) -> str:
    return "<0.1%" if value < 0.1 else f"{value:.1f}%"


def render(rows: list[tuple[str, float]], theme: str) -> str:
    c = THEMES[theme]
    width, top, row_h = 420, 66, 26
    height = top + len(rows) * row_h + 10
    x0, x1 = 118, 336
    biggest = max(value for _, value in rows)
    summary = ", ".join(f"{name} {pct(value)}" for name, value in rows)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Most used languages</title>',
        f'<desc id="desc">{escape(summary)}</desc>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{c["bg"]}" stroke="{c["border"]}"/>',
        f'<g font-family="{FONT}">',
        f'<text x="24" y="32" font-size="15" font-weight="600" fill="{c["t1"]}">Most used languages</text>',
        f'<text x="24" y="50" font-size="11.5" fill="{c["t2"]}">Share of code across my public repositories</text>',
    ]
    for i, (name, value) in enumerate(rows):
        y = top + i * row_h
        w = max(2.0, (x1 - x0) * value / biggest)
        r = min(4.0, w / 2)
        # Thin bar, square on the baseline, rounded at the data end.
        bar = f"M{x0} {y + 5}h{w - r:.2f}q{r} 0 {r} {r}v{10 - 2 * r}q0 {r} -{r} {r}h-{w - r:.2f}z"
        parts += [
            f'<text x="24" y="{y + 14}" font-size="13" fill="{c["t1"]}">{escape(name)}</text>',
            f'<path d="{bar}" fill="{c["bar"]}"/>',
            f'<text x="{width - 24}" y="{y + 14}" font-size="12.5" text-anchor="end" fill="{c["t2"]}" style="font-variant-numeric:tabular-nums">{pct(value)}</text>',
        ]
    parts += ["</g>", "</svg>"]
    return "\n".join(parts) + "\n"


def main() -> None:
    user, out_dir = sys.argv[1], sys.argv[2]
    rows = top_rows(language_bytes(user))
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"languages-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(rows, theme))
    print(", ".join(f"{name} {pct(value)}" for name, value in rows))


if __name__ == "__main__":
    main()
