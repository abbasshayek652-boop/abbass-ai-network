from __future__ import annotations

import argparse

from agents.linkedin_agent.models import PostRequest
from agents.linkedin_agent.service import service


def cmd_login(_: argparse.Namespace) -> None:
    url = service.login_url()
    print(url)


def cmd_post(args: argparse.Namespace) -> None:
    result = service.post_text(args.text, args.visibility)
    print(result)


def cmd_post_doc(args: argparse.Namespace) -> None:
    payload = PostRequest(text=args.text, doc_path=args.file, doc_title=args.title, visibility=args.visibility)
    result = service.post_document(payload)
    print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LinkedIn agent helper")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Print the LinkedIn authorization URL")
    login.set_defaults(func=cmd_login)

    post = sub.add_parser("post", help="Publish a text post immediately")
    post.add_argument("--text", required=True)
    post.add_argument("--visibility", default="PUBLIC")
    post.set_defaults(func=cmd_post)

    post_doc = sub.add_parser("post-doc", help="Publish a document post")
    post_doc.add_argument("--file", required=True)
    post_doc.add_argument("--title", required=True)
    post_doc.add_argument("--text", required=True)
    post_doc.add_argument("--visibility", default="PUBLIC")
    post_doc.set_defaults(func=cmd_post_doc)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
