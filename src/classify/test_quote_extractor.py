"""Tests for quote_extractor against synthetic and real-corpus patterns.

Run: python -m src.classify.test_quote_extractor
"""

from __future__ import annotations

from src.classify.quote_extractor import extract_at_depth, quote_depth, is_attribution


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"{msg}\n  expected: {expected!r}\n  actual:   {actual!r}")


def test_quote_depth():
    assert_eq(quote_depth("hello"), 0)
    assert_eq(quote_depth(""), 0)
    assert_eq(quote_depth("> hello"), 1)
    assert_eq(quote_depth(">hello"), 1)
    assert_eq(quote_depth("> > hello"), 2)
    assert_eq(quote_depth(">> hello"), 2)
    assert_eq(quote_depth(">>> hello"), 3)
    assert_eq(quote_depth("> >> hello"), 3)
    assert_eq(quote_depth("  > hello"), 1, "leading whitespace")


def test_attribution_detection():
    assert is_attribution("On Mon, Mar 11, 2014 at 12:00 PM, Jonathan Ellis <jbellis@gmail.com> wrote:")
    assert is_attribution("On Mar 11, 2014, at 7:26 PM, Edward Capriolo wrote:")
    assert is_attribution("----- Original Message -----")
    assert not is_attribution("hello world")
    assert not is_attribution("> On Mon, Mar 11 wrote:")  # quoted attribution stays handled by depth


def test_depth_zero_strips_quotes_and_attribution():
    body = """+1 to the proposal.

On Mon, Mar 11, 2014 at 12:00 PM, Jonathan Ellis <jbellis@gmail.com> wrote:
> CQL3 is almost two years old now and has proved to be the better API
> that Cassandra needed.
> > Even older grandparent quote.
"""
    out = extract_at_depth(body, 0)
    assert "+1 to the proposal." in out
    assert "Jonathan Ellis" not in out, "attribution should be stripped at depth 0"
    assert "CQL3" not in out, "depth-1 quote should be stripped"
    assert "grandparent" not in out, "depth-2 quote should be stripped"


def test_depth_one_keeps_immediate_parent():
    body = """+1.

On Mon wrote:
> Parent content here.
> > Grandparent content.
"""
    out = extract_at_depth(body, 1)
    assert "+1." in out
    assert "Parent content" in out, "depth=1 should keep immediate parent"
    assert "Grandparent" not in out, "depth=1 should drop grandparent"


def test_depth_two_keeps_grandparent():
    body = """Reply text.
> Parent text.
> > Grandparent text.
> > > Great-grandparent text.
"""
    out = extract_at_depth(body, 2)
    assert "Reply text." in out
    assert "Parent text." in out
    assert "Grandparent text." in out
    assert "Great-grandparent" not in out


def test_depth_infinity_keeps_everything():
    body = """Reply.
> Parent.
> > Grandparent.
> > > GGP.
"""
    out = extract_at_depth(body, 999)
    assert "Reply." in out
    assert "Parent." in out
    assert "Grandparent." in out
    assert "GGP." in out


def test_top_posting_bottom_posting():
    # Top-posted (Outlook style): new content first, then attribution, then quotes
    top_posted = """My new reply text.
Has multiple lines.

On Mon wrote:
> Parent content."""
    assert "My new reply text." in extract_at_depth(top_posted, 0)
    assert "Parent content" not in extract_at_depth(top_posted, 0)

    # Bottom-posted (mailing list style): quotes first, new content at end
    bottom_posted = """> Parent content asks a question.
> > Grandparent provided the question.

My answer is here."""
    out0 = extract_at_depth(bottom_posted, 0)
    assert "My answer is here." in out0
    assert "Parent content" not in out0


def test_collapse_blank_lines():
    body = """Line 1.



Line 2."""
    out = extract_at_depth(body, 0)
    # Should not have 3 blank lines in a row
    assert "\n\n\n" not in out


def test_empty_body():
    assert_eq(extract_at_depth("", 0), "")
    assert_eq(extract_at_depth("", 5), "")


def test_only_quoted_returns_empty_at_depth_zero():
    body = """> All quoted.
> > Even more.
"""
    out = extract_at_depth(body, 0)
    assert out.strip() == "", f"expected empty, got: {out!r}"


def main():
    tests = [
        ("quote_depth basic", test_quote_depth),
        ("attribution detection", test_attribution_detection),
        ("depth=0 strips quotes and attribution", test_depth_zero_strips_quotes_and_attribution),
        ("depth=1 keeps immediate parent", test_depth_one_keeps_immediate_parent),
        ("depth=2 keeps grandparent", test_depth_two_keeps_grandparent),
        ("depth=infinity keeps everything", test_depth_infinity_keeps_everything),
        ("top-posting and bottom-posting", test_top_posting_bottom_posting),
        ("collapse blank lines", test_collapse_blank_lines),
        ("empty body", test_empty_body),
        ("only-quoted at depth=0", test_only_quoted_returns_empty_at_depth_zero),
    ]
    failures = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            failures.append(name)
            print(f"  FAIL {name}: {e}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
