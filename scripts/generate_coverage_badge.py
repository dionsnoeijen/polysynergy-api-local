#!/usr/bin/env python3
"""Generate a coverage badge SVG from coverage.json"""

import json
import os

def generate_badge_svg(coverage_percent):
    """Generate SVG badge with coverage percentage"""
    
    # Choose color based on coverage percentage
    if coverage_percent >= 90:
        color = "brightgreen"
    elif coverage_percent >= 80:
        color = "green" 
    elif coverage_percent >= 70:
        color = "yellowgreen"
    elif coverage_percent >= 60:
        color = "yellow"
    elif coverage_percent >= 50:
        color = "orange"
    else:
        color = "red"
    
    # Generate the SVG
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="104" height="20">
<linearGradient id="b" x2="0" y2="100%">
<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
<stop offset="1" stop-opacity=".1"/>
</linearGradient>
<clipPath id="a">
<rect width="104" height="20" rx="3" fill="#fff"/>
</clipPath>
<g clip-path="url(#a)">
<path fill="#555" d="M0 0h63v20H0z"/>
<path fill="{color}" d="M63 0h41v20H63z"/>
<path fill="url(#b)" d="M0 0h104v20H0z"/>
</g>
<g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="110">
<text x="325" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="530">coverage</text>
<text x="325" y="140" transform="scale(.1)" textLength="530">coverage</text>
<text x="825" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="310">{coverage_percent}%</text>
<text x="825" y="140" transform="scale(.1)" textLength="310">{coverage_percent}%</text>
</g>
</svg>'''
    
    return svg

if __name__ == "__main__":
    # Read coverage data
    try:
        with open('coverage.json', 'r') as f:
            data = json.load(f)
        coverage_percent = round(data['totals']['percent_covered'])
    except FileNotFoundError:
        print("Error: coverage.json not found. Run 'pytest --cov --cov-report=json' first.")
        exit(1)
    except KeyError:
        print("Error: Invalid coverage.json format.")
        exit(1)
    
    # Generate and save badge
    svg_content = generate_badge_svg(coverage_percent)
    with open('coverage-badge.svg', 'w') as f:
        f.write(svg_content)
    
    print(f"Generated coverage badge: {coverage_percent}% coverage")