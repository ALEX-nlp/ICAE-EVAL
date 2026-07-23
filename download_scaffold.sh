#!/usr/bin/env bash
#
# Download the base-language Docker images and benchmark data. The script is
# restart-safe: completed files/directories are skipped and partial HTTP
# downloads are resumed.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

for command_name in docker curl tar lz4; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "[download] missing command: $command_name" >&2
        exit 1
    fi
done

if ! docker info >/dev/null 2>&1; then
    echo "[download] Docker is installed but the daemon is not available." >&2
    echo "[download] Start Docker and make sure the current user can run 'docker info'." >&2
    exit 1
fi

download_file() {
    local url="$1"
    local target="$2"
    local partial="${target}.part"

    if [ -s "$target" ]; then
        echo "[download] exists, skipping: $target"
        return
    fi

    echo "[download] fetching: $target"
    curl --fail --location --retry 3 --continue-at - --output "$partial" "$url"
    mv "$partial" "$target"
}

dataset_ready() {
    local directory="$1"
    local marker="$directory/.icae-download-complete"
    local directory_count

    [ -f "$marker" ] && return 0
    [ -d "$directory" ] || return 1

    # Both published datasets contain one top-level directory for each of the
    # 480 benchmark repositories. This also recognizes complete directories
    # unpacked by older versions of this script that did not write a marker.
    directory_count="$(
        find "$directory" -mindepth 1 -maxdepth 1 -type d -print |
            awk 'END { print NR + 0 }'
    )"
    if [ "$directory_count" -ge 480 ]; then
        touch "$marker"
        return 0
    fi
    return 1
}

# Eleven images cover the twelve benchmark languages (JavaScript and TypeScript
# share Node.js). Kotlin is distributed as a pre-exported tar below.
images=(
    "mcr.microsoft.com/dotnet/sdk:8.0"
    "gcc:12"
    "dart:3.5"
    "golang:1.22"
    "eclipse-temurin:17"
    "node:20"
    "php:8.2"
    "python:3.11"
    "ruby:3.2"
    "rust:1.81"
)

output_dir="$ROOT/docker_lang_official"
mkdir -p "$output_dir"

for image in "${images[@]}"; do
    clean_name="$(printf '%s' "$image" | sed 's|mcr.microsoft.com/||g' | tr '/:' '_')"
    target="$output_dir/${clean_name}.tar"
    if [ -s "$target" ]; then
        echo "[download] exists, skipping: ${target#$ROOT/}"
        continue
    fi

    echo "[download] pulling Docker image: $image"
    docker pull "$image"
    echo "[download] exporting: ${target#$ROOT/}"
    docker save --output "${target}.part" "$image"
    mv "${target}.part" "$target"
done

download_file \
    "https://zenodo.org/records/21058690/files/kotlin_1.9.25.tar?download=1" \
    "$output_dir/kotlin_1.9.25.tar"

repos_file="$ROOT/realcode_repos.tar.lz4"
download_file \
    "https://zenodo.org/records/21071802/files/realcode_repos.tar.lz4?download=1" \
    "$repos_file"
if dataset_ready "$ROOT/realcode_repos"; then
    echo "[download] already unpacked: realcode_repos/"
else
    echo "[download] unpacking: realcode_repos.tar.lz4"
    lz4 --decompress --stdout "$repos_file" | tar -xf - -C "$ROOT"
    if ! dataset_ready "$ROOT/realcode_repos"; then
        echo "[download] realcode_repos/ is incomplete after extraction." >&2
        exit 1
    fi
fi

rcb_file="$ROOT/rcb_tests_repos.tar.gz"
download_file \
    "https://zenodo.org/records/21076652/files/rcb_tests_repos.tar.gz?download=1" \
    "$rcb_file"
if dataset_ready "$ROOT/rcb_tests_repos"; then
    echo "[download] already unpacked: rcb_tests_repos/"
else
    echo "[download] unpacking: rcb_tests_repos.tar.gz"
    tar -xzf "$rcb_file" -C "$ROOT"
    if ! dataset_ready "$ROOT/rcb_tests_repos"; then
        echo "[download] rcb_tests_repos/ is incomplete after extraction." >&2
        exit 1
    fi
fi

echo "[download] all language images and benchmark data are ready."
