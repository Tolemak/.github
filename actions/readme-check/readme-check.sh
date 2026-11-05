#!/usr/bin/env bash
set -u
dir=${1:-${INPUT_DIRECTORY:-.}}
status_done=${INPUT_STATUS_DONE:-false}
errors=0
warnings=0
err() { echo "::error file=$1::$2"; errors=$((errors + 1)); }
warn() { echo "::warning file=$1::$2"; warnings=$((warnings + 1)); }

headings() {
    awk '/^```/ { fence = !fence; next } !fence && /^#{1,6} / { n++ } END { print n + 0 }' "$1"
}

empty_sections() {
    awk '
        /^```/ { fence = !fence; if (pending) pending = 0; next }
        fence { next }
        /^#{1,6} / {
            level = index($0, " ") - 1
            if (pending && level <= plevel) print pline
            pending = 1; plevel = level; pline = $0; next
        }
        /^[[:space:]]*$/ { next }
        { pending = 0 }
        END { if (pending) print pline }
    ' "$1"
}

for pair in "README.md:README.pl.md" "README.pl.md:README.md"; do
    file=${pair%%:*}
    other=${pair##*:}
    path="$dir/$file"
    if [ ! -f "$path" ]; then
        err "$path" "missing $file"
        continue
    fi
    head -1 "$path" | grep -q '^# ' || err "$path" "first line must be '# <name>'"
    head -5 "$path" | grep -qF "$other)" || err "$path" "link to $other within the first 5 lines"
    lines=$(wc -l < "$path")
    [ "$lines" -gt 100 ] && err "$path" "$lines lines, move details to docs/ with an index table"
    [ "$lines" -gt 60 ] && [ "$lines" -le 100 ] && warn "$path" "$lines lines, aim for about 50"
    words=$(wc -w < "$path")
    [ "$words" -gt 800 ] && err "$path" "$words words, move details to docs/ with an index table"
    [ "$words" -gt 500 ] && [ "$words" -le 800 ] && warn "$path" "$words words, aim for under 500"
    matches=$(grep -niE 'comprehensive|robust|seamless|powerful|cutting-edge|state-of-the-art|blazing|this (document|repository|project) (describes|contains|provides)|warto zauważyć|warto zaznaczyć|kompleksow|potężn|bezproblemow|niniejsz' "$path" || true)
    if [ -n "$matches" ]; then
        while IFS= read -r match; do err "$path" "banned wording: $match"; done <<< "$matches"
    fi
    matches=$(LC_ALL=C.UTF-8 grep -nP '^#{1,6} .*[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B00}-\x{2BFF}]' "$path" || true)
    if [ -n "$matches" ]; then
        while IFS= read -r match; do err "$path" "emoji in heading: $match"; done <<< "$matches"
    fi
    empty=$(empty_sections "$path")
    [ -n "$empty" ] && err "$path" "section without content: $(echo "$empty" | tr '\n' ' ')"
    if [ "$status_done" = true ] && ! grep -q 'img.shields.io/badge/status-done' "$path"; then
        err "$path" "status-done repository needs the status: done badge"
    fi
done

if [ -f "$dir/README.md" ] && [ -f "$dir/README.pl.md" ]; then
    en=$(headings "$dir/README.md")
    pl=$(headings "$dir/README.pl.md")
    [ "$en" != "$pl" ] && err "$dir/README.pl.md" "README.md has $en headings, README.pl.md has $pl: keep them equal"
fi

echo "$errors errors, $warnings warnings"
[ "$errors" -eq 0 ]
