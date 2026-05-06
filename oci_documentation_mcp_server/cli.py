"""Command-line wrapper for OCI documentation helpers."""

import argparse
import asyncio
import sys
from oci_documentation_mcp_server.models import AnswerResponse, SearchResponse
from oci_documentation_mcp_server.server_oci import (
    answer_question,
    read_documentation,
    search_documentation,
)
from typing import Sequence


class CliContext:
    """Minimal context object for reusing MCP tool implementations from the CLI."""

    async def error(self, message: str) -> None:
        """Write tool errors to stderr."""
        print(message, file=sys.stderr)

    async def info(self, message: str) -> None:
        """Write informational tool messages to stderr."""
        print(message, file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the OCI documentation CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    return asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> int:
    """Dispatch a parsed CLI command."""
    ctx = CliContext()
    if args.command == 'answer':
        response = await answer_question(
            ctx,
            question=_join(args.question),
            search_phrase=args.search_phrase,
            max_sources=args.max_sources,
        )
        _print_answer(response, as_json=args.json)
        return 0

    if args.command == 'search':
        response = await search_documentation(
            ctx,
            search_phrase=_join(args.search_phrase),
            search_intent='CLI search',
            limit=args.limit,
        )
        _print_search(response, as_json=args.json)
        return 0

    if args.command == 'read':
        content = await read_documentation(
            ctx,
            url=args.url,
            max_length=args.max_length,
            start_index=args.start_index,
        )
        print(content)
        return 0

    raise ValueError(f'Unsupported command: {args.command}')


def _build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='oci-docs',
        description='Search, read, and answer questions from OCI documentation.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    answer_parser = subparsers.add_parser('answer', help='Answer a question with citations')
    answer_parser.add_argument('question', nargs='+')
    answer_parser.add_argument('--search-phrase', default=None)
    answer_parser.add_argument('--max-sources', type=int, default=3)
    answer_parser.add_argument('--json', action='store_true')

    search_parser = subparsers.add_parser('search', help='Search OCI documentation')
    search_parser.add_argument('search_phrase', nargs='+')
    search_parser.add_argument('--limit', type=int, default=10)
    search_parser.add_argument('--json', action='store_true')

    read_parser = subparsers.add_parser('read', help='Read an OCI documentation URL')
    read_parser.add_argument('url')
    read_parser.add_argument('--max-length', type=int, default=5000)
    read_parser.add_argument('--start-index', type=int, default=0)

    return parser


def _print_answer(response: AnswerResponse, as_json: bool) -> None:
    """Print an answer response."""
    if as_json:
        print(response.model_dump_json(indent=2))
        return

    print(response.answer)
    if response.citations:
        print('\nCitations:')
        for citation in response.citations:
            print(f'[{citation.citation_id}] {citation.title}')
            print(f'    {citation.url}')
            print(f'    {citation.excerpt}')


def _print_search(response: SearchResponse, as_json: bool) -> None:
    """Print a search response."""
    if as_json:
        print(response.model_dump_json(indent=2))
        return

    for result in response.search_results:
        print(f'{result.rank_order}. {result.title}')
        print(f'   {result.url}')
        if result.context:
            print(f'   {result.context}')


def _join(parts: Sequence[str]) -> str:
    """Join shell-tokenized text arguments."""
    return ' '.join(parts)


if __name__ == '__main__':
    raise SystemExit(main())
