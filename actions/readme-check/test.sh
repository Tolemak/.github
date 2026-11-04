#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
action="$root/actions/readme-check/readme-check.sh"
fixtures="$root/actions/readme-check/testdata"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

prepare() {
    rm -rf "$tmp/case"
    mkdir -p "$tmp/case"
    cp "$fixtures/passing/README.md" "$tmp/case/README.md"
    cp "$fixtures/passing/README.pl.md" "$tmp/case/README.pl.md"
}

expect_failure() {
    name=$1
    expected=$2
    shift 2
    if output=$(INPUT_STATUS_DONE="$1" bash "$action" "$tmp/case" 2>&1); then
        echo "not ok - $name passed unexpectedly"
        exit 1
    fi
    if ! grep -q "$expected" <<< "$output"; then
        echo "not ok - $name did not report '$expected'"
        echo "$output"
        exit 1
    fi
    echo "ok - $name"
}

prepare
bash "$action" "$tmp/case"
echo "ok - passing pair"

prepare
rm "$tmp/case/README.pl.md"
expect_failure "missing pair file" "missing README.pl.md" false

prepare
cp "$fixtures/failures/title.md" "$tmp/case/README.md"
expect_failure "title" "first line must be" false

prepare
cp "$fixtures/failures/late-link.md" "$tmp/case/README.md"
expect_failure "late language link" "within the first 5 lines" false

prepare
printf '\n## Extra\nContent.\n' >> "$tmp/case/README.md"
expect_failure "heading count mismatch" "keep them equal" false

prepare
cat "$fixtures/failures/too-long.md" >> "$tmp/case/README.md"
expect_failure "too long" "lines, move details" false

prepare
cp "$fixtures/failures/banned-word.md" "$tmp/case/README.md"
expect_failure "banned word" "banned wording" false

prepare
cp "$fixtures/failures/emoji-heading.md" "$tmp/case/README.md"
expect_failure "emoji in heading" "emoji in heading" false

prepare
cp "$fixtures/failures/empty-section.md" "$tmp/case/README.md"
expect_failure "empty section" "section without content" false

prepare
expect_failure "missing done badge" "status: done badge" true
