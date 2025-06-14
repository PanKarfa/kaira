#!/usr/bin/env bash

# Move to the project root directory
cd "$(dirname "$0")/.." || exit

# Download auto_examples if needed (for ReadTheDocs and other CI environments)
echo "Downloading auto_examples if needed..."
python scripts/download_auto_examples.py

# Generate the API reference documentation automatically
echo "Generating API reference documentation..."
python scripts/generate_api_reference.py docs/api_reference.rst

# Generate the changelog documentation from CHANGELOG.md
echo "Generating changelog documentation..."
python scripts/generate_changelog.py

# Generate example gallery index files automatically
echo "Generating example gallery index files..."
python scripts/generate_example_indices.py

# Move to the docs directory
cd docs || exit

# Generate API documentation for the current Kaira library with no-index option
# to avoid duplicate object descriptions
# sphinx-apidoc --no-headings --no-toc --implicit-namespaces --no-index -f -o . ../kaira

# Clean existing builds and generate HTML documentation.
make clean
make html

echo "Documentation build complete!"
