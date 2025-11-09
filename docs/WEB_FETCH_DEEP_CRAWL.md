# Web Fetch & Deep Crawling Guide

## Overview

SWE-CLI’s `fetch_url` tool is backed by [Crawl4AI](https://docs.crawl4ai.com/). It can either load a **single page** (default) or perform a **deep crawl** that follows links, filters pages, and aggregates the results for you. This guide explains the enhanced parameters so you know exactly when to request a normal fetch versus a deep crawl.

Key improvements:
- `best_first` is now the default crawl strategy, prioritizing the most relevant links first.
- Optional constraints (domains, URL patterns, page limits) and streaming mode help bound long-running crawls.
- Tool schema + system prompt guidance were updated so the agent can ask for breadth (`bfs`), deep branching (`dfs`), or relevance (`best_first`) depending on your request.

## Normal Fetch vs. Deep Crawl

| Use Case | Recommended Mode | Why |
| --- | --- | --- |
| Grab one doc/page, e.g., “fetch the release notes” | `deep_crawl = false` (default) | Fast, lightweight, returns markdown or HTML for the single page |
| Summaries across docs, “crawl the guides under /docs” | `deep_crawl = true`, `max_depth = 1-2` | Traverses internal links and aggregates results |
| Research across sections with relevance hints | `deep_crawl = true`, `crawl_strategy = best_first` | Prioritizes links containing relevant keywords so you see the important stuff first |

> 💡 Deep crawls are heavier. Always specify reasonable bounds (`max_depth`, `max_pages`, filters) so the agent finishes quickly and doesn’t wander into irrelevant content.

## Parameters Reference

| Parameter | Default | Details |
| --- | --- | --- |
| `extract_text` | `true` | Markdown extraction (set `false` for raw HTML) |
| `max_length` | `50000` | Soft cap on returned characters; truncated results show total length |
| `deep_crawl` | `false` | Enable multi-page crawls when you need broader context |
| `crawl_strategy` | `"best_first"` | `best_first` (relevance), `bfs` (level order), `dfs` (follow a branch). |
| `max_depth` | `1` | Depth beyond the seed URL (depth 0). Must be ≥ 1 when deep crawling |
| `include_external` | `false` | Allow crossing to other domains |
| `max_pages` | `None` | Hard stop on number of pages; always specify for large sites |
| `allowed_domains` / `blocked_domains` | `None` | Safelist/blocklist domains to keep crawls scoped |
| `url_patterns` | `None` | Glob patterns (`*docs*`, `*/guide/*`) to include |
| `stream` | `false` | Stream results as they’re discovered (deep crawl only) |

## Strategy Selection

- **best_first (default)**: Ideal when you care about relevance. Crawl4AI scores URLs and visits high-value pages first. Use when you can describe what “important” means (e.g., mention technologies or keywords).
- **bfs**: Breadth-first search. Covers each depth level evenly—use for TOC-style docs or when you want wide coverage but shallow depth.
- **dfs**: Depth-first search. Follows a link branch as far as allowed, then backtracks. Handy when investigating a nested path (e.g., “follow this guide hierarchy completely”).

## Filtering & Limits

Combine the filters to keep the crawl tight:
- `allowed_domains` / `blocked_domains`: Keep crawls inside `docs.example.com` while skipping `old.docs.example.com`.
- `url_patterns`: Glob syntax, e.g., `["*tutorial*", "*guide*"]`.
- `max_pages`: Prevents runaway crawls—set small values (10–25) unless you really need more.
- `include_external`: Only turn on when you explicitly need off-site links (e.g., following GitHub wiki references).

## Streaming Mode

Setting `stream=true` (with `deep_crawl=true`) yields partial results as each page is processed. SWE-CLI still aggregates the final markdown but you’ll see progress for long crawls and can stop early if needed.

## Example Tool Invocation

```
fetch_url(
  url="https://docs.example.com",
  deep_crawl=true,
  crawl_strategy="best_first",
  max_depth=2,
  max_pages=20,
  allowed_domains=["docs.example.com"],
  url_patterns=["*/guide/*", "*/tutorial/*"]
)
```

This request:
1. Starts at `https://docs.example.com`
2. Uses best-first scoring to prioritize relevant links
3. Crawls at most 2 levels deep and 20 pages total
4. Restricts results to docs pages containing “guide” or “tutorial”

The response includes a per-page breakdown plus aggregated markdown so you can quickly summarize or quote the findings.
