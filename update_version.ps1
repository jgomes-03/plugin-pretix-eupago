# Update version numbers in all files from apps.py
# Usage: .\update_version.ps1

# Get directory of the script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginRoot = Split-Path -Parent $ScriptDir

# Run the Python script to update versions
Write-Host "Updating version numbers in all files..."
python -m eupago.scripts.update_version

# Commit the changes if this is a git repository
if (Test-Path -Path "$PluginRoot\.git") {
    $response = Read-Host -Prompt "Do you want to commit the version update? (y/n)"
    
    if ($response -eq "y" -or $response -eq "Y") {
        # Get current version
        $versionLine = Get-Content "$PluginRoot\eupago\apps.py" | Where-Object { $_ -match "__version__ = '(.+)'" }
        $version = $Matches[1]
        
        # Commit changes
        git -C "$PluginRoot" add README.md
        git -C "$PluginRoot" commit -m "Update version to $version"
        
        Write-Host "Changes committed."
        
        # Ask about creating a tag
        $tagResponse = Read-Host -Prompt "Do you want to create a version tag? (y/n)"
        
        if ($tagResponse -eq "y" -or $tagResponse -eq "Y") {
            git -C "$PluginRoot" tag -a "v$version" -m "Version $version"
            Write-Host "Tag v$version created."
            
            $pushResponse = Read-Host -Prompt "Push tag to remote? (y/n)"
            
            if ($pushResponse -eq "y" -or $pushResponse -eq "Y") {
                git -C "$PluginRoot" push origin "v$version"
                Write-Host "Tag pushed to remote."
            }
        }
    }
}

Write-Host "Done!"
