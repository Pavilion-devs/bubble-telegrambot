import io
import math
import random
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

def generate_bubble_visualization(map_data: Dict[str, Any], width: int = 1200, height: int = 800) -> Optional[bytes]:
    """
    Generate a visualization from Bubblemaps map data
    
    Args:
        map_data: The JSON data from the Bubblemaps API
        width: Image width
        height: Image height
        
    Returns:
        PNG image bytes or None if generation failed
    """
    try:
        # Extract token information
        token_name = map_data.get("full_name", "Unknown Token")
        token_symbol = map_data.get("symbol", "")
        token_address = map_data.get("token_address", "")
        nodes = map_data.get("nodes", [])
        links = map_data.get("links", [])
        
        # Create image and drawing context
        image = Image.new("RGB", (width, height), color=(250, 250, 255))
        draw = ImageDraw.Draw(image)
        
        # Try to get nice fonts
        try:
            title_font = ImageFont.truetype("arial.ttf", 32)
            subtitle_font = ImageFont.truetype("arial.ttf", 22)
            label_font = ImageFont.truetype("arial.ttf", 14)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
        
        # Draw background and title
        draw_title(draw, token_name, token_symbol, token_address, width, title_font, subtitle_font)
        
        # Calculate node positions using a force-directed layout
        node_positions = calculate_node_positions(nodes, links, width, height)
        
        # Draw links
        draw_links(draw, nodes, links, node_positions)
        
        # Draw nodes as bubbles
        draw_nodes(draw, nodes, node_positions, label_font)
        
        # Add legend with top holders
        draw_legend(draw, nodes[:5], width, height, subtitle_font, label_font)
        
        # Add metadata
        update_time = map_data.get("dt_update", "")
        if update_time:
            draw.text((20, height - 40), f"Last Updated: {update_time}", 
                      fill=(120, 120, 120), font=label_font)
        
        # Convert to bytes
        output = io.BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        print(f"Error generating visualization: {e}")
        return None

def draw_title(draw: ImageDraw.Draw, token_name: str, token_symbol: str, token_address: str, 
               width: int, title_font, subtitle_font):
    """Draw the title section of the visualization"""
    title = f"{token_name} ({token_symbol})"
    
    # Draw title background
    draw.rectangle([(0, 0), (width, 80)], fill=(240, 240, 250))
    
    # Draw title and subtitle
    draw.text((20, 15), title, fill=(50, 50, 150), font=title_font)
    
    # Truncate address if needed
    if len(token_address) > 20:
        display_address = token_address[:10] + "..." + token_address[-8:]
    else:
        display_address = token_address
        
    draw.text((20, 50), f"Address: {display_address}", fill=(80, 80, 80), font=subtitle_font)

def calculate_node_positions(nodes: List[Dict[str, Any]], links: List[Dict[str, Any]], 
                            width: int, height: int) -> Dict[int, Tuple[float, float]]:
    """
    Calculate node positions using a simple force-directed layout algorithm
    
    Returns a dictionary mapping node indices to (x, y) positions
    """
    node_positions = {}
    node_count = min(40, len(nodes))  # Limit to top 40 nodes for better visualization
    
    # Initialize random positions
    center_x = width * 0.5
    center_y = height * 0.5
    radius = min(width, height) * 0.35
    
    for i in range(node_count):
        angle = 2 * math.pi * i / node_count
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        node_positions[i] = (x, y)
    
    # Simple force-directed algorithm (limited iterations for performance)
    for _ in range(50):
        for i in range(node_count):
            # Repulsive force from other nodes
            force_x, force_y = 0, 0
            for j in range(node_count):
                if i != j:
                    x1, y1 = node_positions[i]
                    x2, y2 = node_positions[j]
                    dx = x1 - x2
                    dy = y1 - y2
                    distance = max(0.1, math.sqrt(dx*dx + dy*dy))
                    force = 500 / (distance*distance)  # Repulsive force
                    force_x += (dx / distance) * force
                    force_y += (dy / distance) * force
            
            # Attractive force from links
            for link in links:
                source = link.get("source")
                target = link.get("target")
                if source is not None and target is not None:
                    if i == source and target < node_count:
                        x1, y1 = node_positions[i]
                        x2, y2 = node_positions[target]
                        dx = x2 - x1
                        dy = y2 - y1
                        distance = max(0.1, math.sqrt(dx*dx + dy*dy))
                        strength = min(1.0, (link.get("forward", 0) + link.get("backward", 0)) / 1000)
                        force_x += (dx / distance) * strength
                        force_y += (dy / distance) * strength
                    elif i == target and source < node_count:
                        x1, y1 = node_positions[i]
                        x2, y2 = node_positions[source]
                        dx = x2 - x1
                        dy = y2 - y1
                        distance = max(0.1, math.sqrt(dx*dx + dy*dy))
                        strength = min(1.0, (link.get("forward", 0) + link.get("backward", 0)) / 1000)
                        force_x += (dx / distance) * strength
                        force_y += (dy / distance) * strength
            
            # Update position with damping
            x, y = node_positions[i]
            damping = 0.5
            x += force_x * damping
            y += force_y * damping
            
            # Keep nodes within bounds
            margin = 100
            x = max(margin, min(width - margin, x))
            y = max(margin, min(height - margin, y))
            
            node_positions[i] = (x, y)
    
    return node_positions

def draw_links(draw: ImageDraw.Draw, nodes: List[Dict[str, Any]], links: List[Dict[str, Any]], 
               node_positions: Dict[int, Tuple[float, float]]):
    """Draw the links between nodes"""
    node_count = len(node_positions)
    
    for link in links:
        source = link.get("source")
        target = link.get("target")
        
        if (source is not None and target is not None and 
            source < node_count and target < node_count):
            
            x1, y1 = node_positions[source]
            x2, y2 = node_positions[target]
            
            # Determine line width based on transaction volume
            forward = link.get("forward", 0)
            backward = link.get("backward", 0)
            total = forward + backward
            width = max(1, min(5, math.log10(total + 1)))
            
            # Determine color based on direction
            if forward > backward:
                color = (100, 150, 255, 180)  # Blueish for forward
            elif backward > forward:
                color = (150, 100, 255, 180)  # Purplish for backward
            else:
                color = (150, 150, 150, 180)  # Gray for equal
                
            # Draw the link
            draw.line([(x1, y1), (x2, y2)], fill=color, width=int(width))

def draw_nodes(draw: ImageDraw.Draw, nodes: List[Dict[str, Any]], 
               node_positions: Dict[int, Tuple[float, float]], font):
    """Draw the nodes as bubbles with labels"""
    
    # Get max percentage for scaling
    max_percentage = max([node.get("percentage", 0) for node in nodes[:len(node_positions)]])
    
    for i, node in enumerate(nodes):
        if i >= len(node_positions):
            break
            
        x, y = node_positions[i]
        percentage = node.get("percentage", 0)
        
        # Scale bubble size based on percentage
        radius = max(10, min(50, (percentage / max_percentage) * 40 + 10))
        
        # Determine color based on node type
        is_contract = node.get("is_contract", False)
        if is_contract:
            fill_color = (100, 100, 240, 220)  # Blue for contracts
            outline_color = (70, 70, 180)
        else:
            fill_color = (240, 120, 100, 220)  # Red for regular addresses
            outline_color = (180, 70, 70)
            
        # Draw the bubble
        draw.ellipse([(x-radius, y-radius), (x+radius, y+radius)], 
                     fill=fill_color, outline=outline_color, width=2)
        
        # Get node name
        name = node.get("name", "")
        address = node.get("address", "")
        
        # Use name if available, otherwise truncated address
        if not name and address:
            if len(address) > 8:
                name = address[:6] + "..."
            else:
                name = address
                
        # Draw label for top 10 nodes only to avoid clutter
        if i < 10 and name:
            text_width = font.getbbox(name)[2]
            draw.text((x - text_width/2, y + radius + 5), name, fill=(50, 50, 50), font=font)

def draw_legend(draw: ImageDraw.Draw, top_nodes: List[Dict[str, Any]], 
                width: int, height: int, title_font, text_font):
    """Draw a legend with top holders information"""
    
    # Draw legend background
    legend_width = 300
    legend_x = width - legend_width - 20
    legend_y = 100
    legend_height = 30 + len(top_nodes) * 30
    
    draw.rectangle([(legend_x, legend_y), (legend_x + legend_width, legend_y + legend_height)], 
                   fill=(255, 255, 255, 220), outline=(200, 200, 200))
    
    # Draw legend title
    draw.text((legend_x + 10, legend_y + 10), "Top Holders", fill=(80, 80, 120), font=title_font)
    
    # Draw top holders
    for i, node in enumerate(top_nodes):
        name = node.get("name", node.get("address", "Unknown"))
        percentage = node.get("percentage", 0)
        
        # Truncate name if too long
        if len(name) > 25:
            name = name[:22] + "..."
            
        y_pos = legend_y + 50 + i * 30
        draw.text((legend_x + 20, y_pos), f"{i+1}. {name}", fill=(60, 60, 60), font=text_font)
        draw.text((legend_x + legend_width - 80, y_pos), f"{percentage:.2f}%", 
                  fill=(80, 80, 120), font=text_font) 