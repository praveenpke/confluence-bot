#!/usr/bin/env python3
"""
Response formatting utilities for the Confluence Q&A Bot
"""

import re
from typing import List, Dict, Any

def format_technical_list(text: str, title: str = None) -> str:
    """
    Format a technical list with proper structure
    """
    if not text:
        return text
    
    # Add title if provided
    if title:
        formatted = f"## {title}\n\n"
    else:
        formatted = ""
    
    # Split into lines and process
    lines = text.strip().split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if it's a numbered item
        numbered_match = re.match(r'^(\d+)\.\s*(.+)$', line)
        if numbered_match:
            number = numbered_match.group(1)
            content = numbered_match.group(2)
            formatted_lines.append(f"{number}. **{content.split(':')[0]}**: {content.split(':', 1)[1] if ':' in content else content}")
            continue
        
        # Check if it's a bullet point
        bullet_match = re.match(r'^[-*•]\s*(.+)$', line)
        if bullet_match:
            content = bullet_match.group(1)
            formatted_lines.append(f"• **{content.split(':')[0]}**: {content.split(':', 1)[1] if ':' in content else content}")
            continue
        
        # Check if it contains technical data (field: value pattern)
        if ':' in line and any(keyword in line.lower() for keyword in ['field', 'type', 'index', 'data']):
            parts = line.split(':', 1)
            if len(parts) == 2:
                label = parts[0].strip()
                value = parts[1].strip()
                formatted_lines.append(f"**{label}**: {value}")
                continue
        
        # Regular line
        formatted_lines.append(line)
    
    formatted += '\n'.join(formatted_lines)
    return formatted

def format_grid_columns(text: str) -> str:
    """
    Special formatter for grid columns data
    """
    if not text or 'grid' not in text.lower() or 'column' not in text.lower():
        return text
    
    # Extract column information
    lines = text.split('\n')
    formatted_sections = []
    
    current_section = None
    current_items = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for section headers
        if any(keyword in line.lower() for keyword in ['recent columns', 'visible columns', 'active columns', 'group']):
            # Save previous section
            if current_section and current_items:
                formatted_sections.append(f"## {current_section}\n" + '\n'.join(current_items))
            
            current_section = line
            current_items = []
            continue
        
        # Check for column definitions
        if '(' in line and ')' in line and any(keyword in line.lower() for keyword in ['index', 'field', 'type']):
            # Extract column name and details
            parts = line.split('(', 1)
            if len(parts) == 2:
                column_name = parts[0].strip().strip('*').strip()
                details = parts[1].rstrip(')').strip()
                
                # Format the details
                detail_parts = details.split(',')
                formatted_details = []
                for detail in detail_parts:
                    detail = detail.strip()
                    if ':' in detail:
                        key, value = detail.split(':', 1)
                        formatted_details.append(f"**{key.strip()}**: {value.strip()}")
                    else:
                        formatted_details.append(detail)
                
                formatted_item = f"**{column_name}** ({', '.join(formatted_details)})"
                current_items.append(formatted_item)
                continue
        
        # Regular content
        current_items.append(line)
    
    # Add final section
    if current_section and current_items:
        formatted_sections.append(f"## {current_section}\n" + '\n'.join(current_items))
    
    if formatted_sections:
        return '\n\n'.join(formatted_sections)
    
    return text

def enhance_response_formatting(text: str) -> str:
    """
    Main function to enhance response formatting
    """
    if not text:
        return text
    
    # Check for numbered list format first (like "1. Flight Number: This column...")
    if re.search(r'\d+\.\s+[A-Z][^:]*:', text):
        return format_numbered_list(text)
    
    # Check if it's grid columns data (for different format)
    if 'grid' in text.lower() and 'column' in text.lower():
        return format_grid_columns(text)
    
    # Check if it's a technical list
    if any(keyword in text.lower() for keyword in ['list', 'columns', 'fields', 'properties']):
        return format_technical_list(text)
    
    # General formatting improvements
    formatted = text
    
    # Add section headers if missing
    if 'overview' not in text.lower() and len(text) > 200:
        lines = text.split('\n')
        if len(lines) > 5:
            # Add overview section
            overview_end = min(3, len(lines))
            overview = '\n'.join(lines[:overview_end])
            rest = '\n'.join(lines[overview_end:])
            formatted = f"## Overview\n{overview}\n\n## Details\n{rest}"
    
    return formatted

def format_numbered_list(text: str) -> str:
    """
    Format numbered list responses with proper structure
    """
    if not text:
        return text
    
    # Check if the text contains inline numbered lists (all in one paragraph)
    if re.search(r'\d+\.\s+[A-Z][^:]*:', text):
        return format_inline_numbered_list(text)
    
    lines = text.split('\n')
    formatted_lines = []
    
    # Find the overview/introduction part
    intro_lines = []
    numbered_lines = []
    in_numbered_section = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line starts a numbered list
        if re.match(r'^\d+\.\s+[A-Z][^:]*:', line):
            in_numbered_section = True
            numbered_lines.append(line)
        elif in_numbered_section:
            # Continue numbered section
            numbered_lines.append(line)
        else:
            # Still in introduction
            intro_lines.append(line)
    
    # Format the response
    formatted = ""
    
    # Add introduction as overview
    if intro_lines:
        formatted += "## Overview\n"
        formatted += '\n'.join(intro_lines)
        formatted += "\n\n"
    
    # Add numbered list as details
    if numbered_lines:
        formatted += "## Column Details\n"
        for line in numbered_lines:
            # Format numbered items with bold labels
            if re.match(r'^\d+\.\s+[A-Z][^:]*:', line):
                # Extract number, label, and description
                match = re.match(r'^(\d+)\.\s+([^:]+):\s*(.*)', line)
                if match:
                    number = match.group(1)
                    label = match.group(2).strip()
                    description = match.group(3).strip()
                    formatted += f"{number}. **{label}**: {description}\n"
                else:
                    formatted += line + "\n"
            else:
                formatted += line + "\n"
    
    return formatted.strip()

def format_inline_numbered_list(text: str) -> str:
    """
    Format inline numbered lists (all in one paragraph)
    """
    if not text:
        return text
    
    # Find the introduction part (before the numbered list starts)
    intro_end = text.find('1.')
    if intro_end == -1:
        return text
    
    intro = text[:intro_end].strip()
    numbered_part = text[intro_end:].strip()
    
    # Split the numbered part into individual items
    # Pattern to match: "1. Label: Description 2. Label: Description"
    items = re.findall(r'(\d+)\.\s+([^:]+):\s*([^0-9]+?)(?=\d+\.|$)', numbered_part)
    
    # If the regex didn't capture all items, try a different approach
    if len(items) < 5:  # If we didn't get many items, try splitting differently
        # Split by numbered items more aggressively
        parts = re.split(r'(\d+\.\s+[^:]+:)', numbered_part)
        items = []
        for i in range(1, len(parts), 2):  # Skip the first empty part
            if i + 1 < len(parts):
                number_label = parts[i].strip()
                description = parts[i + 1].strip()
                
                # Extract number and label
                match = re.match(r'(\d+)\.\s+(.+)', number_label)
                if match:
                    number = match.group(1)
                    label = match.group(2).rstrip(':')
                    items.append((number, label, description))
    
    formatted = ""
    
    # Add introduction as overview
    if intro:
        formatted += "## Overview\n"
        formatted += intro
        formatted += "\n\n"
    
    # Add numbered list as details
    if items:
        formatted += "## Column Details\n"
        for number, label, description in items:
            formatted += f"{number}. **{label.strip()}**: {description.strip()}\n"
    
    return formatted.strip()

def format_sources(sources: List[Dict[str, Any]]) -> str:
    """
    Format source attribution
    """
    if not sources:
        return ""
    
    formatted = "\n\n## Sources\n"
    for i, source in enumerate(sources, 1):
        title = source.get('title', 'Unknown')
        url = source.get('url', '')
        space = source.get('space_name', '')
        
        if url:
            formatted += f"{i}. [{title} ({space})]({url})\n"
        else:
            formatted += f"{i}. {title} ({space})\n"
    
    return formatted 