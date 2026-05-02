"""Tests for quote_extractor against synthetic and real-corpus patterns.

Run: python -m src.classify.test_quote_extractor
"""

from __future__ import annotations

from src.classify.quote_extractor import extract_at_depth, extract_message_context, quote_depth, is_attribution


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


def test_message_context_basic_top_post():
    body = """My new reply text.
Has multiple lines.

On Mon, Mar 11, 2014 at 12:00 PM, Jonathan Ellis <jbellis@gmail.com> wrote:
> Parent says hi.
> > Grandparent message.
> Parent continues.
--
Sylvain Lebresne
Datastax
"""
    ctx = extract_message_context(body)
    assert ctx["new_content"].startswith("My new reply text."), ctx["new_content"]
    assert "Has multiple lines." in ctx["new_content"]
    assert "Jonathan Ellis" not in ctx["new_content"]
    assert ctx["signature"] == "Sylvain Lebresne\nDatastax", ctx["signature"]
    assert len(ctx["attribution_lines"]) == 1
    assert "Jonathan Ellis" in ctx["attribution_lines"][0]
    # Quoted segments: depth-1 → depth-2 → depth-1 (three segments)
    depths = [s["depth"] for s in ctx["quoted_segments"]]
    assert depths == [1, 2, 1], depths
    assert "Parent says hi." in ctx["quoted_segments"][0]["text"]
    assert "Grandparent" in ctx["quoted_segments"][1]["text"]


def test_message_context_bottom_post():
    body = """> Question from parent?
> > Grandparent context.

Yes, the answer is 42.
"""
    ctx = extract_message_context(body)
    assert ctx["new_content"] == "Yes, the answer is 42."
    assert len(ctx["quoted_segments"]) == 2
    assert ctx["quoted_segments"][0]["depth"] == 1
    assert ctx["quoted_segments"][1]["depth"] == 2
    assert ctx["signature"] is None


def test_message_context_op13_pattern():
    """The Op-13 case: new content + attribution + quoted material with anchor phrase."""
    body = """Unfortunately I don't think we can do much for hint partitioning.
It's too late for a schema change in 2.1, and 3.0 we're already
planning to move to file-based hint storage.

On Mon, Jul 14, 2014 at 12:22 PM, graham sanderson <graham@vast.com> wrote:
> Thanks
> > I plan to address this, but probably not until after 3.0
"""
    ctx = extract_message_context(body)
    assert "Unfortunately" in ctx["new_content"]
    assert "after 3.0" not in ctx["new_content"], "the anchoring phrase should NOT leak into new_content"
    # The quoted text containing "after 3.0" should be in quoted_segments only
    quoted_text = " ".join(s["text"] for s in ctx["quoted_segments"])
    assert "after 3.0" in quoted_text


def test_message_context_no_quotes():
    body = "Just a flat message with no quotes.\nLine two.\n"
    ctx = extract_message_context(body)
    assert ctx["new_content"] == "Just a flat message with no quotes.\nLine two."
    assert ctx["quoted_segments"] == []
    assert ctx["attribution_lines"] == []
    assert ctx["signature"] is None


def test_message_context_signature_dash_dash_no_space():
    body = "Hello.\n--\nName Here\n"
    ctx = extract_message_context(body)
    assert ctx["new_content"] == "Hello."
    assert ctx["signature"] == "Name Here"


def test_message_context_wrapped_attribution():
    """Mailers sometimes wrap 'On X wrote:' across 2-3 lines. Should still be detected."""
    body = """Alright, let's wait on 7743

On Wed, Aug 13, 2014 at 7:46 PM, Benedict Elliott Smith <
belliottsmith@datastax.com> wrote:
> Quoted body content here.
"""
    ctx = extract_message_context(body)
    assert ctx["new_content"] == "Alright, let's wait on 7743", ctx["new_content"]
    assert len(ctx["attribution_lines"]) == 1
    assert "Benedict Elliott Smith" in ctx["attribution_lines"][0]
    assert ctx["attribution_lines"][0].endswith("wrote:")


def test_message_context_empty():
    ctx = extract_message_context("")
    assert ctx == {"new_content": "", "quoted_segments": [], "attribution_lines": [], "signature": None}


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
        ("MessageContext basic top-post", test_message_context_basic_top_post),
        ("MessageContext bottom-post", test_message_context_bottom_post),
        ("MessageContext Op-13 pattern (anchoring phrase in quote)", test_message_context_op13_pattern),
        ("MessageContext no quotes", test_message_context_no_quotes),
        ("MessageContext signature with no trailing space", test_message_context_signature_dash_dash_no_space),
        ("MessageContext wrapped multi-line attribution", test_message_context_wrapped_attribution),
        ("MessageContext empty body", test_message_context_empty),
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
