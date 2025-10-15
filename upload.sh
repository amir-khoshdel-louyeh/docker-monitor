#!/bin/bash
# Quick script to upload package to PyPI

echo "🚀 PyPI Upload Guide"
echo "======================================"
echo ""
echo "Step 1: Create a new token"
echo "   Go to: https://pypi.org/manage/account/token/"
echo "   Copy the token"
echo ""
echo "Step 2: Edit the .pypirc.new file"
echo "   Command: nano .pypirc.new"
echo "   Replace the token in the password field"
echo ""
echo "Step 3: Copy to home directory"
read -p "Have you saved the token in .pypirc.new? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📋 Copying file..."
    cp .pypirc.new ~/.pypirc
    chmod 600 ~/.pypirc
    echo "✅ File copied and permissions set"
    echo ""
    
    echo "🔍 Checking package..."
    .venv/bin/twine check dist/*
    
    echo ""
    read -p "Do you want to upload the package? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📤 Uploading to PyPI..."
        .venv/bin/twine upload dist/*
        
        echo ""
        echo "🎉 If successful, your package is available at:"
        echo "   https://pypi.org/project/docker-monitor-manager/"
        echo ""
        echo "📦 Install:"
        echo "   pip install docker-monitor-manager"
    else
        echo "❌ Upload cancelled"
    fi
else
    echo "❌ First save the token:"
    echo "   nano .pypirc.new"
    echo ""
    echo "Then run this script again:"
    echo "   bash upload.sh"
fi
