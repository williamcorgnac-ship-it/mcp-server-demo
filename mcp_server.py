from mcp.server.fastmcp import FastMCP
from datetime import datetime

# Create the FastMCP server instance
mcp = FastMCP("mcp-documentation-server")

# Register the tool using FastMCP decorator
@mcp.tool()
def get_documentation_from_database() -> dict:
    """
    This tool returns the documentation from the database for the project.
    It is very useful for figuring out what the project is about.
    """
    ## actual implementation would query a real database here

    return {
        "title": "How to Use MCP Servers",
        "body": "This is a mocked documentation entry from the database. MCP servers expose tools and resources for AI agents.",
        "source": "mocked_database"
    }


@mcp.tool()
def capture_mobile_data(
    device_id: str,
    event_type: str,
    payload: dict,
) -> dict:
    """
    Simulates capturing a mobile event from a device.

    Args:
        device_id: Unique identifier for the mobile device (e.g. "device-abc123").
        event_type: Type of event being captured (e.g. "tap", "swipe", "form_submit").
        payload: Arbitrary key/value data associated with the event.

    Returns:
        A capture receipt with a timestamp and the echoed event details.
    """
    return {
        "status": "captured",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "device_id": device_id,
        "event_type": event_type,
        "payload": payload,
    }


if __name__ == "__main__":
    mcp.run("stdio")
