#!/usr/bin/env python
"""
Diagnostic tool for MCP server endpoints and Elasticsearch.
"""

import os
import requests
import json
import sys
from urllib.parse import quote
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MCP_ROUTES = [
    # Original MCP endpoints
    "/mcp/resource?uri=nixos://package/python",
    "/mcp/resource?uri=nixos://search/packages/python",
    "/mcp-original/resource?uri=nixos://package/python",
    
    # Direct MCP endpoints
    "/direct-mcp/resource?uri=nixos://package/python",
    "/direct-mcp/resource?uri=nixos://search/packages/python",
    
    # Direct API endpoints
    "/api/package/python",
    "/api/search/packages/python",
    "/api/option/services.nginx",
    
    # Debug and utility endpoints
    "/health",
    "/status",
    "/debug/mcp-registered",
    "/debug/resource/package/python",
    "/debug/resource/search/python",
    "/docs",
]

def check_endpoints(base_url="http://localhost:9421"):
    """Test all endpoints and return results."""
    results = []
    
    print(f"Testing against server: {base_url}")
    print("-" * 60)
    
    for route in MCP_ROUTES:
        url = f"{base_url}{route}"
        print(f"Testing: {url}")
        
        try:
            response = requests.get(url)
            status = response.status_code
            
            if status == 200:
                result = "✅ OK"
                data = response.json()
            else:
                result = f"❌ ERROR ({status})"
                data = response.text
                
            print(f"  Result: {result}")
            
            # For successful responses, show a brief summary
            if status == 200 and isinstance(data, dict):
                if "error" in data:
                    print(f"  Response: {data['error']}")
                elif "results" in data and isinstance(data["results"], list):
                    print(f"  Found: {len(data['results'])} results")
                else:
                    keys = list(data.keys())[:3]
                    print(f"  Keys: {', '.join(keys)}...")
            
            results.append({
                "url": url,
                "status": status,
                "result": result
            })
            
        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                "url": url,
                "status": None,
                "result": f"❌ EXCEPTION: {str(e)}"
            })
            
        print()
    
    return results

def check_elasticsearch():
    """Check Elasticsearch connection and do a test search."""
    print("\nChecking Elasticsearch Configuration:")
    print("-" * 60)
    
    es_url = os.getenv("ELASTICSEARCH_URL", "https://search.nixos.org/backend/latest-42-nixos-unstable/_search")
    es_user = os.getenv("ELASTICSEARCH_USER")
    es_password = os.getenv("ELASTICSEARCH_PASSWORD")
    
    print(f"Elasticsearch URL: {es_url}")
    print(f"Elasticsearch credentials configured: {'Yes' if es_user and es_password else 'No'}")
    
    if not es_user or not es_password:
        print("❌ ERROR: Elasticsearch credentials not set in .env file")
        return False
    
    # Make a direct test request to Elasticsearch
    print("\nTesting direct Elasticsearch connection:")
    try:
        # Basic search query for packages
        search_body = {
            "size": 2,
            "query": {
                "bool": {
                    "should": [
                        {"match": {"package_pname": "python"}},
                    ],
                    "filter": [
                        {"term": {"type": "package"}}
                    ]
                }
            }
        }
        
        response = requests.post(
            es_url,
            auth=(es_user, es_password),
            json=search_body,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            total_hits = data.get("hits", {}).get("total", {}).get("value", 0)
            print(f"✅ SUCCESS: Elasticsearch connection successful")
            print(f"Found {total_hits} hits for 'python' query")
            
            # Show first result as sample
            if total_hits > 0:
                first_hit = data.get("hits", {}).get("hits", [])[0]
                source = first_hit.get("_source", {})
                print(f"\nSample result:")
                print(f"  Name: {source.get('package_pname')}")
                print(f"  Version: {source.get('package_version')}")
                print(f"  Attribute: {source.get('package_attr_name')}")
            
            return True
        else:
            print(f"❌ ERROR: Elasticsearch returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to Elasticsearch: {e}")
        return False

def main():
    """Main function."""
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="NixMCP diagnostic tool")
    parser.add_argument("--url", default="http://localhost:9421", help="Server URL")
    parser.add_argument("--es-only", action="store_true", help="Only check Elasticsearch")
    args = parser.parse_args()
    
    if args.es_only:
        # Only check Elasticsearch
        es_success = check_elasticsearch()
        print("\nOverall Diagnostic Results:")
        print("-" * 60)
        print(f"Elasticsearch: {'✅ OK' if es_success else '❌ Not working'}")
        return
    
    # Check endpoints
    results = check_endpoints(args.url)
    
    # Print endpoint summary
    print("\nEndpoint Status Summary:")
    print("-" * 60)
    
    working = [r for r in results if r["status"] == 200]
    failing = [r for r in results if r["status"] != 200]
    
    print(f"✅ Working endpoints: {len(working)}/{len(results)}")
    print(f"❌ Failing endpoints: {len(failing)}/{len(results)}")
    
    if failing:
        print("\nFailing endpoints:")
        for r in failing:
            print(f"  - {r['url']}: {r['result']}")
    
    # Check Elasticsearch
    es_success = check_elasticsearch()
    
    # Overall status
    print("\nOverall Diagnostic Results:")
    print("-" * 60)
    print(f"API Endpoints: {'✅ OK' if len(failing) == 0 else f'❌ {len(failing)} failing'}")
    print(f"Elasticsearch: {'✅ OK' if es_success else '❌ Not working'}")

if __name__ == "__main__":
    main()