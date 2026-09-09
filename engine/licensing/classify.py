#!/usr/bin/env python3
"""Identify a licence from its own text rather than from packaging metadata.

Package metadata is not authoritative: ocamlgraph 2.2.0 declares plain
"LGPL-2.1-only" in opam while its own LICENSE carries a linking exception.
"""
import re

# Exception clauses are recognised first so a linking exception is never lost.
EXCEPTIONS = [
    ("LGPL-3.0-linking-exception", "as a special exception to the gnu lesser general public license version 3"),
    ("OCaml-LGPL-linking-exception", "as a special exception to the gnu library general public license"),
    ("OCaml-LGPL-linking-exception", "as a special exception to the gnu lesser general public license"),
    ("PCRE2-exception", "pcre2-exception"),
    ("Commons-Clause", "“commons clause” license condition"),
]

# Ordered most specific first; the first phrase that appears decides.
FAMILIES = [
    ("MPL-2.0", "mozilla public license version 2.0"),
    ("MPL-2.0", "mozilla public license v. 2.0"),
    ("LGPL-3.0", "gnu lesser general public license version 3"),
    ("LGPL-3.0", "lesser general public license version 3 29 june 2007"),
    ("GPL-3.0", "gnu general public license version 3 29 june 2007"),
    ("LGPL-2.1", "gnu lesser general public license version 2.1"),
    ("LGPL-2.1", "lesser general public license version 2.1 february 1999"),
    ("LGPL-2.1", "gnu library general public license version 2.1"),
    ("LGPL-2.0", "gnu library general public license version 2"),
    ("LGPL-2.0", "gnu library general public license version 2"),
    ("GPL-2.0", "gnu general public license version 2"),
    ("GPL-2.0", "general public license version 2 june 1991"),
    ("Apache-2.0", "apache license version 2.0"),
    ("CC0-1.0", "cc0 1.0 universal"),
    ("PSF-2.0", "python software foundation license"),
    ("BSD-3-Clause", "neither the name of"),
    ("BSD-3-Clause", "the name of the author may not be used to endorse"),
    ("MIT", "permission is hereby granted free of charge"),
    ("ISC", "permission to use copy modify and/or distribute this software for any purpose"),
    ("ISC", "permission to use copy modify and distribute this software for any purpose with or without fee"),
    ("BSD-2-Clause", "redistributions in binary form must reproduce the above"),
    ("Unlicense", "this is free and unencumbered software released into the public domain"),
]


# Licence texts arrive wrapped in OCaml, C and shell comment markers; the
# marker characters must not break a phrase match.
COMMENT = re.compile(r"^[ \t]*(\(\*|\*\)|\*|#|//|;;?|--)+[ \t]?", re.M)


def normalize(text):
    stripped = COMMENT.sub("", text.lower())
    return re.sub(r"[,;]", "", re.sub(r"\s+", " ", stripped))


def identify(text):
    """Return (spdx_id or None, [exception ids]) for one licence text."""
    flat = normalize(text)
    exceptions = []
    for name, phrase in EXCEPTIONS:
        if phrase in flat and name not in exceptions:
            exceptions.append(name)
    for name, phrase in FAMILIES:
        if phrase in flat:
            return name, exceptions
    return None, exceptions


def expression(spdx, exceptions):
    if spdx is None:
        return None
    linking = [e for e in exceptions if e.endswith("linking-exception")]
    text = spdx + (" WITH " + linking[0] if linking else "")
    if "Commons-Clause" in exceptions:
        text += " AND Commons-Clause"
    return text


# A holder line names a year or bears a (c) mark. Licence bodies talk about
# copyright in prose ("copyright law: that is to say..."), which is not a holder.
HOLDER = re.compile(r"(?i)^copyright\b.*?(\(c\)|©|\b(19|20)\d{2}\b)")
# Grant boilerplate that mentions a placeholder rather than a real holder.
PLACEHOLDER = re.compile(r"(?i)<(year|name of author|copyright holders?)>")


def copyright_holders(text, limit=8, head=60):
    """Holder lines from the head of a licence file."""
    holders = []
    for line in text.splitlines()[:head]:
        stripped = re.sub(r"^[\s*#/;(-]+", "", line).strip()
        if not HOLDER.match(stripped) or PLACEHOLDER.search(stripped):
            continue
        cleaned = re.sub(r"\s+", " ", stripped).rstrip("*/ ")
        if cleaned not in holders:
            holders.append(cleaned)
        if len(holders) >= limit:
            break
    return holders
