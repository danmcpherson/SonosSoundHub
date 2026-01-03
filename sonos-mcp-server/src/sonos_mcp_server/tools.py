"""MCP tool definitions for Sonos control."""

from mcp.server import Server
from mcp.types import Tool, TextContent
import json
from typing import Any

from .api_client import SonosApiClient


def format_response(data: Any) -> list[TextContent]:
    """Format API response as MCP TextContent."""
    if isinstance(data, (dict, list)):
        return [TextContent(type="text", text=json.dumps(data, indent=2))]
    return [TextContent(type="text", text=str(data))]


def format_error(error: Exception) -> list[TextContent]:
    """Format error as MCP TextContent."""
    return [TextContent(type="text", text=f"Error: {str(error)}")]


def register_tools(server: Server, client: SonosApiClient):
    """Register all Sonos control tools with the MCP server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Return list of available tools."""
        return [
            # ========================================
            # Speaker Discovery
            # ========================================
            Tool(
                name="list_speakers",
                description="Get a list of all discovered Sonos speakers on the network",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="rediscover_speakers",
                description="Trigger a fresh discovery of Sonos speakers on the network",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_speaker_info",
                description="Get detailed information about a speaker including volume, playback state, current track, and battery level (for portable speakers)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        }
                    },
                    "required": ["speaker"]
                }
            ),

            # ========================================
            # Playback Control
            # ========================================
            Tool(
                name="play_pause",
                description="Toggle play/pause on a Sonos speaker",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        }
                    },
                    "required": ["speaker"]
                }
            ),
            Tool(
                name="next_track",
                description="Skip to the next track on a Sonos speaker",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        }
                    },
                    "required": ["speaker"]
                }
            ),
            Tool(
                name="previous_track",
                description="Go back to the previous track on a Sonos speaker",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        }
                    },
                    "required": ["speaker"]
                }
            ),
            Tool(
                name="get_current_track",
                description="Get information about the currently playing track",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        }
                    },
                    "required": ["speaker"]
                }
            ),

            # ========================================
            # Volume Control
            # ========================================
            Tool(
                name="get_volume",
                description="Get the current volume level of a speaker (0-100)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        }
                    },
                    "required": ["speaker"]
                }
            ),
            Tool(
                name="set_volume",
                description="Set the volume level of a speaker (0-100)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        },
                        "volume": {
                            "type": "integer",
                            "description": "Volume level from 0 to 100",
                            "minimum": 0,
                            "maximum": 100
                        }
                    },
                    "required": ["speaker", "volume"]
                }
            ),
            Tool(
                name="toggle_mute",
                description="Toggle mute on/off for a speaker",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        }
                    },
                    "required": ["speaker"]
                }
            ),

            # ========================================
            # Grouping
            # ========================================
            Tool(
                name="get_groups",
                description="Get all current speaker groups",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="group_speakers",
                description="Group a speaker with another speaker (the coordinator)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the speaker to add to the group"
                        },
                        "coordinator": {
                            "type": "string",
                            "description": "Name of the speaker that will be the group coordinator"
                        }
                    },
                    "required": ["speaker", "coordinator"]
                }
            ),
            Tool(
                name="ungroup_speaker",
                description="Remove a speaker from its current group",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker to ungroup"
                        }
                    },
                    "required": ["speaker"]
                }
            ),
            Tool(
                name="party_mode",
                description="Group all speakers together (party mode) with the specified speaker as coordinator",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the speaker to be the coordinator"
                        }
                    },
                    "required": ["speaker"]
                }
            ),
            Tool(
                name="ungroup_all",
                description="Ungroup all speakers - each speaker will play independently",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Any speaker name (command affects all speakers)"
                        }
                    },
                    "required": ["speaker"]
                }
            ),
            Tool(
                name="set_group_volume",
                description="Set the volume for all speakers in a group",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of any speaker in the group"
                        },
                        "volume": {
                            "type": "integer",
                            "description": "Volume level from 0 to 100",
                            "minimum": 0,
                            "maximum": 100
                        }
                    },
                    "required": ["speaker", "volume"]
                }
            ),

            # ========================================
            # Playback Modes
            # ========================================
            Tool(
                name="set_shuffle",
                description="Enable or disable shuffle mode",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        },
                        "enabled": {
                            "type": "boolean",
                            "description": "True to enable shuffle, false to disable"
                        }
                    },
                    "required": ["speaker", "enabled"]
                }
            ),
            Tool(
                name="set_repeat",
                description="Set the repeat mode",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["off", "one", "all"],
                            "description": "Repeat mode: 'off', 'one' (repeat single track), or 'all' (repeat queue)"
                        }
                    },
                    "required": ["speaker", "mode"]
                }
            ),
            Tool(
                name="set_sleep_timer",
                description="Set a sleep timer to stop playback after a duration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        },
                        "minutes": {
                            "type": "integer",
                            "description": "Number of minutes until playback stops (use 0 to cancel)",
                            "minimum": 0
                        }
                    },
                    "required": ["speaker", "minutes"]
                }
            ),

            # ========================================
            # Favorites & Playlists
            # ========================================
            Tool(
                name="list_favorites",
                description="Get all Sonos favorites",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="play_favorite",
                description="Play a Sonos favorite by name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        },
                        "favorite_name": {
                            "type": "string",
                            "description": "Name of the favorite to play"
                        }
                    },
                    "required": ["speaker", "favorite_name"]
                }
            ),
            Tool(
                name="list_playlists",
                description="Get all Sonos playlists",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="list_radio_stations",
                description="Get favorite radio stations (TuneIn)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="play_radio",
                description="Play a radio station by name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        },
                        "station_name": {
                            "type": "string",
                            "description": "Name of the radio station to play"
                        }
                    },
                    "required": ["speaker", "station_name"]
                }
            ),

            # ========================================
            # Queue Management
            # ========================================
            Tool(
                name="get_queue",
                description="Get the current playback queue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        }
                    },
                    "required": ["speaker"]
                }
            ),
            Tool(
                name="clear_queue",
                description="Clear all tracks from the queue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        }
                    },
                    "required": ["speaker"]
                }
            ),
            Tool(
                name="play_from_queue",
                description="Play a specific track from the queue by its position number",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        },
                        "track_number": {
                            "type": "integer",
                            "description": "Position of the track in the queue (1-based)",
                            "minimum": 1
                        }
                    },
                    "required": ["speaker", "track_number"]
                }
            ),
            Tool(
                name="add_favorite_to_queue",
                description="Add a favorite to the end of the queue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        },
                        "favorite_name": {
                            "type": "string",
                            "description": "Name of the favorite to add"
                        }
                    },
                    "required": ["speaker", "favorite_name"]
                }
            ),
            Tool(
                name="add_playlist_to_queue",
                description="Add a playlist to the end of the queue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "description": "Name of the Sonos speaker"
                        },
                        "playlist_name": {
                            "type": "string",
                            "description": "Name of the playlist to add"
                        }
                    },
                    "required": ["speaker", "playlist_name"]
                }
            ),

            # ========================================
            # Macros
            # ========================================
            Tool(
                name="list_macros",
                description="Get all available Sonos macros (automated sequences of commands)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_macro",
                description="Get details of a specific macro including its definition and parameters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the macro"
                        }
                    },
                    "required": ["name"]
                }
            ),
            Tool(
                name="run_macro",
                description="Execute a macro to run a predefined sequence of Sonos commands",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the macro to execute"
                        },
                        "arguments": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional arguments to pass to the macro (e.g., volume level)"
                        }
                    },
                    "required": ["name"]
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        try:
            # Speaker Discovery
            if name == "list_speakers":
                result = client.get_speakers()
                return format_response(result)

            elif name == "rediscover_speakers":
                result = client.rediscover_speakers()
                return format_response(result)

            elif name == "get_speaker_info":
                result = client.get_speaker_info(arguments["speaker"])
                return format_response(result)

            # Playback Control
            elif name == "play_pause":
                result = client.play_pause(arguments["speaker"])
                return format_response(result)

            elif name == "next_track":
                result = client.next_track(arguments["speaker"])
                return format_response(result)

            elif name == "previous_track":
                result = client.previous_track(arguments["speaker"])
                return format_response(result)

            elif name == "get_current_track":
                result = client.get_current_track(arguments["speaker"])
                return format_response(result)

            # Volume Control
            elif name == "get_volume":
                result = client.get_volume(arguments["speaker"])
                return format_response(result)

            elif name == "set_volume":
                result = client.set_volume(arguments["speaker"], arguments["volume"])
                return format_response(result)

            elif name == "toggle_mute":
                result = client.toggle_mute(arguments["speaker"])
                return format_response(result)

            # Grouping
            elif name == "get_groups":
                result = client.get_groups()
                return format_response(result)

            elif name == "group_speakers":
                result = client.group_speaker(arguments["speaker"], arguments["coordinator"])
                return format_response(result)

            elif name == "ungroup_speaker":
                result = client.ungroup_speaker(arguments["speaker"])
                return format_response(result)

            elif name == "party_mode":
                result = client.party_mode(arguments["speaker"])
                return format_response(result)

            elif name == "ungroup_all":
                result = client.ungroup_all(arguments["speaker"])
                return format_response(result)

            elif name == "set_group_volume":
                result = client.set_group_volume(arguments["speaker"], arguments["volume"])
                return format_response(result)

            # Playback Modes
            elif name == "set_shuffle":
                state = "on" if arguments["enabled"] else "off"
                result = client.set_shuffle(arguments["speaker"], state)
                return format_response(result)

            elif name == "set_repeat":
                result = client.set_repeat(arguments["speaker"], arguments["mode"])
                return format_response(result)

            elif name == "set_sleep_timer":
                minutes = arguments["minutes"]
                if minutes == 0:
                    result = client.cancel_sleep_timer(arguments["speaker"])
                else:
                    result = client.set_sleep_timer(arguments["speaker"], f"{minutes}m")
                return format_response(result)

            # Favorites & Playlists
            elif name == "list_favorites":
                result = client.get_favorites()
                return format_response(result)

            elif name == "play_favorite":
                result = client.play_favorite(arguments["speaker"], arguments["favorite_name"])
                return format_response(result)

            elif name == "list_playlists":
                result = client.get_playlists()
                return format_response(result)

            elif name == "list_radio_stations":
                result = client.get_radio_stations()
                return format_response(result)

            elif name == "play_radio":
                result = client.play_radio(arguments["speaker"], arguments["station_name"])
                return format_response(result)

            # Queue Management
            elif name == "get_queue":
                result = client.get_queue(arguments["speaker"])
                return format_response(result)

            elif name == "clear_queue":
                result = client.clear_queue(arguments["speaker"])
                return format_response(result)

            elif name == "play_from_queue":
                result = client.play_from_queue(arguments["speaker"], arguments["track_number"])
                return format_response(result)

            elif name == "add_favorite_to_queue":
                result = client.add_favorite_to_queue(arguments["speaker"], arguments["favorite_name"])
                return format_response(result)

            elif name == "add_playlist_to_queue":
                result = client.add_playlist_to_queue(arguments["speaker"], arguments["playlist_name"])
                return format_response(result)

            # Macros
            elif name == "list_macros":
                result = client.get_macros()
                return format_response(result)

            elif name == "get_macro":
                result = client.get_macro(arguments["name"])
                return format_response(result)

            elif name == "run_macro":
                args = arguments.get("arguments", [])
                result = client.run_macro(arguments["name"], args)
                return format_response(result)

            else:
                return format_error(ValueError(f"Unknown tool: {name}"))

        except Exception as e:
            return format_error(e)
