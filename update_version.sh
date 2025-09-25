#!/bin/bash

# Update version numbers in all files from apps.py
# Usage: ./update_version.sh

# Get directory of the script
SCRIPT_DIR=$(dirname "$0")
PLUGIN_ROOT=$(dirname "$SCRIPT_DIR")

# Run the Python script to update versions
echo "Updating version numbers in all files..."
python "$SCRIPT_DIR/eupago/scripts/update_version.py"

# Commit the changes if this is a git repository
if [ -d "$PLUGIN_ROOT/.git" ]; then
    read -p "Do you want to commit the version update? (y/n) " -n 1 -r
    echo    # Move to a new line
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Get current version
        VERSION=$(grep "__version__ = " "$PLUGIN_ROOT/eupago/apps.py" | sed "s/__version__ = '\(.*\)'/\1/")
        
        # Commit changes
        git add "$PLUGIN_ROOT/README.md"
        git commit -m "Update version to $VERSION"
        
        echo "Changes committed."
        
        # Ask about creating a tag
        read -p "Do you want to create a version tag? (y/n) " -n 1 -r
        echo    # Move to a new line
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git tag -a "v$VERSION" -m "Version $VERSION"
            echo "Tag v$VERSION created."
            
            read -p "Push tag to remote? (y/n) " -n 1 -r
            echo    # Move to a new line
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git push origin "v$VERSION"
                echo "Tag pushed to remote."
            fi
        fi
    fi
fi

echo "Done!"
