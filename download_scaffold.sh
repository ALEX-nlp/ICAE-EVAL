#!/bin/bash

# Classic stable base images for 12 programming languages (prefer LTS / most-used versions from mainstream repos)
images=(
  "mcr.microsoft.com/dotnet/sdk:8.0"     # C#         (.NET 8 LTS, supported until 2026/11)
  "gcc:12"                               # C++        (default gcc on Debian bookworm, mainstream compiler version)
  "dart:3.5"                             # Dart       (stable Dart bundled with Flutter 3.24)
  "golang:1.22"                          # Go         (widely used stable release, best go.mod compatibility)
  "eclipse-temurin:17"                   # Java       (Java 17 LTS, the most common production version)
  "node:20"                              # JavaScript & TypeScript (Node 20 LTS, shared environment)
  "php:8.2"                              # PHP        (PHP 8.2, best framework compatibility)
  "python:3.11"                          # Python     (3.11 has the widest compatibility and library support)
  "ruby:3.2"                             # Ruby       (Ruby 3.2 stable, mainstream Rails pairing)
  "rust:1.81"                            # Rust       (recent stable release, edition 2021 compatible)
)

# Output directory: docker_lang_official under the current folder
output_dir="docker_lang_official"
mkdir -p "$output_dir"

echo "Starting batch download and export of classic stable Docker images..."

for img in "${images[@]}"; do
  echo "======================================"
  echo "Pulling: $img"
  docker pull "$img"

  # Format file name: replace slashes and colons with underscores to avoid breaking the file path
  # Special case: strip the mcr.microsoft.com/ prefix to keep the generated .tar name short and clean
  clean_name=$(echo "$img" | sed 's|mcr.microsoft.com/||g' | tr '/:' '_')
  filename="${output_dir}/${clean_name}.tar"

  echo "Exporting to: $filename"
  docker save -o "$filename" "$img"
done

# The Kotlin image is not pulled from Docker Hub; download the pre-exported .tar anonymously from Zenodo
zenodo_url="https://zenodo.org/records/21058690/files/kotlin_1.9.25.tar?download=1"
kotlin_file="${output_dir}/kotlin_1.9.25.tar"
echo "======================================"
echo "Downloading anonymously from Zenodo: kotlin_1.9.25.tar"
curl -L -o "$kotlin_file" "$zenodo_url"
echo "Saved to: $kotlin_file"

echo "======================================"
echo "All done! All classic stable .tar files are saved in the $output_dir directory."

# Download the RealCode repositories dataset anonymously from Zenodo
repos_url="https://zenodo.org/records/21071802/files/realcode_repos.tar.lz4?download=1"
repos_file="realcode_repos.tar.lz4"
echo "======================================"
echo "Downloading anonymously from Zenodo: realcode_repos.tar.lz4"
curl -L -o "$repos_file" "$repos_url"
echo "Saved to: $repos_file"
# Decompress with: lz4 -d realcode_repos.tar.lz4 | tar -xf -

# Download the RCB test repositories dataset anonymously from Zenodo
rcb_url="https://zenodo.org/records/21076652/files/rcb_tests_repos.tar.gz?download=1"
rcb_file="rcb_tests_repos.tar.gz"
echo "======================================"
echo "Downloading anonymously from Zenodo: rcb_tests_repos.tar.gz"
curl -L -o "$rcb_file" "$rcb_url"
echo "Saved to: $rcb_file"
# Extract with: tar -xzf rcb_tests_repos.tar.gz


