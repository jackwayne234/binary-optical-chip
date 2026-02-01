"""
Research Literature Search Tool
A Flask application to search arXiv, Semantic Scholar, and Zenodo simultaneously.

Copyright (c) 2026 Christopher Riner
Licensed under the MIT License. See LICENSE file for details.

Wavelength-Division Ternary Optical Computer
https://github.com/jackwayne234/-wavelength-ternary-optical-computer

All three sources are FREE and OPEN ACCESS - no paywalls, no API keys required!
"""

from flask import Flask, render_template, request, jsonify
import requests
import feedparser
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)


def search_arxiv(query, max_results=10):
    """Search arXiv for papers matching the query."""
    try:
        # arXiv API endpoint
        url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f'all:{query}',
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            results = []
            
            for entry in feed.entries:
                results.append({
                    'title': entry.get('title', 'No title'),
                    'authors': [author.get('name', 'Unknown') for author in entry.get('authors', [])],
                    'summary': entry.get('summary', 'No abstract')[:300] + '...',
                    'url': entry.get('link', '#'),
                    'published': entry.get('published', 'Unknown date'),
                    'source': 'arXiv',
                    'id': entry.get('id', '').split('/')[-1]
                })
            
            return results
        else:
            return [{'error': f'arXiv API error: {response.status_code}'}]
    except Exception as e:
        return [{'error': f'arXiv search failed: {str(e)}'}]


def search_semantic_scholar(query, max_results=10):
    """Search Semantic Scholar for papers matching the query.
    
    Semantic Scholar is a free, AI-powered academic search engine that indexes
    over 200 million papers. No API key required for basic search!
    
    Why Semantic Scholar instead of IEEE?
    - ✅ FREE - No paywalls, no API keys needed
    - ✅ Open Access - Focuses on freely available papers
    - ✅ AI-Powered - Better relevance and recommendations
    - ✅ No Registration - Just search and go
    """
    try:
        # Semantic Scholar API endpoint (FREE - no API key required!)
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': query,
            'limit': max_results,
            'fields': 'title,authors,year,abstract,url,openAccessPdf'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            for paper in data.get('data', []):
                # Extract authors
                authors_list = []
                for author in paper.get('authors', []):
                    name = author.get('name', 'Unknown')
                    if name:
                        authors_list.append(name)
                
                # Get the best URL (open access PDF if available, otherwise regular URL)
                open_access = paper.get('openAccessPdf')
                paper_url = open_access.get('url') if open_access else paper.get('url', '#')
                
                results.append({
                    'title': paper.get('title', 'No title'),
                    'authors': authors_list,
                    'summary': paper.get('abstract', 'No abstract')[:300] + '...' if paper.get('abstract') else 'No abstract available',
                    'url': paper_url,
                    'published': str(paper.get('year', 'Unknown')),
                    'source': 'Semantic Scholar',
                    'id': paper.get('paperId', 'unknown'),
                    'open_access': bool(open_access)
                })
            
            return results
        elif response.status_code == 429:
            # Rate limited
            return [{'error': 'Semantic Scholar rate limit reached. Please wait a moment and try again.'}]
        else:
            return [{'error': f'Semantic Scholar API error: {response.status_code}'}]
    except Exception as e:
        return [{'error': f'Semantic Scholar search failed: {str(e)}'}]


def search_zenodo(query, max_results=10):
    """Search Zenodo for records matching the query."""
    try:
        url = "https://zenodo.org/api/records"
        params = {
            'q': query,
            'size': max_results,
            'sort': 'bestmatch',
            'order': 'desc'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            for hit in data.get('hits', {}).get('hits', []):
                metadata = hit.get('metadata', {})
                results.append({
                    'title': metadata.get('title', 'No title'),
                    'authors': [creator.get('name', 'Unknown') for creator in metadata.get('creators', [])],
                    'summary': metadata.get('description', 'No description')[:300] + '...',
                    'url': hit.get('links', {}).get('html', '#'),
                    'published': metadata.get('publication_date', 'Unknown'),
                    'source': 'Zenodo',
                    'id': hit.get('id', 'unknown'),
                    'doi': metadata.get('doi', None)
                })
            
            return results
        else:
            return [{'error': f'Zenodo API error: {response.status_code}'}]
    except Exception as e:
        return [{'error': f'Zenodo search failed: {str(e)}'}]


@app.route('/')
def index():
    """Render the main search page."""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """Handle search requests."""
    query = request.form.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Please enter a search query'})
    
    # Search all three sources in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        arxiv_future = executor.submit(search_arxiv, query)
        semantic_future = executor.submit(search_semantic_scholar, query)
        zenodo_future = executor.submit(search_zenodo, query)
        
        # Add small delay to be nice to APIs
        time.sleep(0.5)
        
        arxiv_results = arxiv_future.result()
        semantic_results = semantic_future.result()
        zenodo_results = zenodo_future.result()
    
    return jsonify({
        'query': query,
        'arxiv': arxiv_results,
        'semantic_scholar': semantic_results,
        'zenodo': zenodo_results,
        'total': len(arxiv_results) + len(semantic_results) + len(zenodo_results)
    })


@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({'status': 'healthy', 'service': 'research-search-tool'})


if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
