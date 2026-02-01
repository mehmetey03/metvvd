name: HDFilmCehennemi Scraper

on:
  schedule:
    - cron: '0 */6 * * *'  # 6 saatte bir
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: pip install requests beautifulsoup4
    
    - name: Run Simple Scraper
      run: |
        echo "📅 Started: $(date)"
        python hdfilmcehennemi_simple.py
        
    - name: Check Results
      run: |
        if [ -f "hdfilmcehennemi.json" ]; then
          COUNT=$(python3 -c "import json; print(len(json.load(open('hdfilmcehennemi.json'))))")
          echo "✅ Collected $COUNT films"
          
          if [ "$COUNT" -lt 5 ]; then
            echo "⚠️ Warning: Less than 5 films collected"
          fi
        else
          echo "❌ No JSON file created!"
          exit 1
        fi
    
    - name: Commit Changes
      run: |
        git config user.email "action@github.com"
        git config user.name "GitHub Action"
        
        git add hdfilmcehennemi.json
        if git diff --cached --quiet; then
          echo "📝 No changes to commit"
        else
          COUNT=$(python3 -c "import json; print(len(json.load(open('hdfilmcehennemi.json'))))")
          git commit -m "🎬 Update: $COUNT films [$(date +'%Y-%m-%d %H:%M:%S UTC')]"
          git push
          echo "✅ Changes pushed"
        fi
