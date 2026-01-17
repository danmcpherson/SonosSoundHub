"""Sonos API router - /api/sonos/* endpoints.

Uses direct SoCo library for most operations (faster, more reliable).
Falls back to soco-cli HTTP API only for complex operations like macros.
"""

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException

from ..models import (
    ListItem,
    QueueItem,
    ShareLinkRequest,
    SocoCliResponse,
    SonosCommandRequest,
    Speaker,
)
from ..services import SocoCliService, SonosCommandService, SoCoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sonos", tags=["sonos"])

# These will be set by the main app
_soco_cli_service: SocoCliService | None = None
_command_service: SonosCommandService | None = None
_soco_service: SoCoService | None = None


def init_router(
    soco_cli_service: SocoCliService,
    command_service: SonosCommandService,
    soco_service: SoCoService,
) -> None:
    """Initialize the router with services."""
    global _soco_cli_service, _command_service, _soco_service
    _soco_cli_service = soco_cli_service
    _command_service = command_service
    _soco_service = soco_service


def _get_soco_cli_service() -> SocoCliService:
    """Get the soco-cli service."""
    if _soco_cli_service is None:
        raise RuntimeError("Services not initialized")
    return _soco_cli_service


def _get_command_service() -> SonosCommandService:
    """Get the command service."""
    if _command_service is None:
        raise RuntimeError("Services not initialized")
    return _command_service


def _get_soco_service() -> SoCoService:
    """Get the SoCo service."""
    if _soco_service is None:
        raise RuntimeError("Services not initialized")
    return _soco_service


# ========================================
# Server Management
# ========================================


@router.get("/status")
async def get_status() -> dict:
    """Get the status of the soco-cli server."""
    return _get_soco_cli_service().get_status()


@router.post("/start")
async def start_server() -> dict:
    """Start the soco-cli HTTP API server."""
    result = await _get_soco_cli_service().start_server()
    if result:
        return {"message": "Server started successfully"}
    raise HTTPException(status_code=500, detail="Failed to start server")


@router.post("/stop")
async def stop_server() -> dict:
    """Stop the soco-cli HTTP API server."""
    result = _get_soco_cli_service().stop_server()
    if result:
        return {"message": "Server stopped successfully"}
    raise HTTPException(status_code=500, detail="Failed to stop server")


# ========================================
# Speaker Discovery (uses SoCo directly)
# ========================================


@router.get("/speakers")
async def get_speakers() -> list[str]:
    """Get all discovered speakers using SoCo library."""
    return await _get_soco_service().discover_speakers()


@router.post("/rediscover")
async def rediscover_speakers() -> list[str]:
    """Trigger speaker rediscovery using SoCo library."""
    return await _get_soco_service().discover_speakers(force=True)


@router.get("/speakers/{speaker_name}")
async def get_speaker_info(speaker_name: str) -> Speaker:
    """Get detailed information about a speaker using SoCo library."""
    return await _get_soco_service().get_speaker_info(speaker_name)


# ========================================
# Command Execution
# ========================================


@router.post("/command")
async def execute_command(request: SonosCommandRequest) -> SocoCliResponse:
    """Execute a command on a speaker."""
    return await _get_command_service().execute_command(
        request.speaker, request.action, *request.args
    )


# ========================================
# Playback Control (uses SoCo directly)
# ========================================


@router.post("/speakers/{speaker_name}/playpause")
async def play_pause(speaker_name: str) -> dict:
    """Toggle play/pause on a speaker using SoCo library.
    
    Uses lightweight get_playback_state() for fast response.
    """
    state = await _get_soco_service().get_playback_state(speaker_name)
    if state == "PLAYING":
        success = await _get_soco_service().pause(speaker_name)
    else:
        success = await _get_soco_service().play(speaker_name)
    return {"success": success}


@router.post("/speakers/{speaker_name}/volume/{volume}")
async def set_volume(speaker_name: str, volume: int) -> dict:
    """Set the volume (0-100) using SoCo library."""
    if volume < 0 or volume > 100:
        raise HTTPException(status_code=400, detail="Volume must be between 0 and 100")
    success = await _get_soco_service().set_volume(speaker_name, volume)
    return {"success": success}


@router.get("/speakers/{speaker_name}/volume")
async def get_volume(speaker_name: str) -> int:
    """Get the current volume using SoCo library (fast, single call)."""
    volume = await _get_soco_service().get_volume(speaker_name)
    if volume is not None:
        return volume
    raise HTTPException(status_code=500, detail="Failed to get volume")


@router.post("/speakers/{speaker_name}/mute")
async def toggle_mute(speaker_name: str) -> dict:
    """Toggle mute on/off using SoCo library (fast, minimal calls)."""
    is_muted = await _get_soco_service().get_mute(speaker_name)
    if is_muted is None:
        raise HTTPException(status_code=500, detail="Failed to get mute state")
    new_state = not is_muted
    success = await _get_soco_service().set_mute(speaker_name, new_state)
    return {"success": success, "muted": new_state}


@router.get("/speakers/{speaker_name}/track")
async def get_current_track(speaker_name: str) -> dict:
    """Get the current track info using SoCo library (fast, minimal calls)."""
    track = await _get_soco_service().get_current_track(speaker_name)
    return {"track": track or ""}


@router.post("/speakers/{speaker_name}/next")
async def next_track(speaker_name: str) -> dict:
    """Skip to the next track using SoCo library."""
    success = await _get_soco_service().next_track(speaker_name)
    return {"success": success}


@router.post("/speakers/{speaker_name}/previous")
async def previous_track(speaker_name: str) -> dict:
    """Go to the previous track using SoCo library."""
    success = await _get_soco_service().previous_track(speaker_name)
    return {"success": success}


# ========================================
# Grouping (uses SoCo directly)
# ========================================


@router.get("/groups")
async def get_groups() -> dict:
    """Get all speaker groups using SoCo library."""
    groups = await _get_soco_service().get_groups()
    return {"groups": groups}


@router.post("/speakers/{speaker_name}/group/{coordinator_name}")
async def group_speaker(speaker_name: str, coordinator_name: str) -> dict:
    """Group a speaker with another (coordinator) using SoCo library."""
    success = await _get_soco_service().group_speakers(coordinator_name, speaker_name)
    return {"success": success}


@router.post("/speakers/{speaker_name}/ungroup")
async def ungroup_speaker(speaker_name: str) -> dict:
    """Ungroup a speaker from its group using SoCo library."""
    success = await _get_soco_service().ungroup_speaker(speaker_name)
    return {"success": success}


@router.post("/speakers/{speaker_name}/party")
async def party_mode(speaker_name: str) -> dict:
    """Activate party mode (group all speakers) using SoCo library."""
    success = await _get_soco_service().party_mode(speaker_name)
    return {"success": success}


@router.post("/speakers/{speaker_name}/ungroup-all")
async def ungroup_all(speaker_name: str) -> dict:
    """Ungroup all speakers using SoCo library."""
    success = await _get_soco_service().ungroup_all(speaker_name)
    return {"success": success}


@router.post("/speakers/{speaker_name}/group-volume/{volume}")
async def set_group_volume(speaker_name: str, volume: int) -> dict:
    """Set the volume for all speakers in a group using SoCo library."""
    if volume < 0 or volume > 100:
        raise HTTPException(status_code=400, detail="Volume must be between 0 and 100")
    success = await _get_soco_service().set_group_volume(speaker_name, volume)
    return {"success": success}


@router.post("/speakers/{speaker_name}/transfer/{target_speaker}")
async def transfer_playback(speaker_name: str, target_speaker: str) -> dict:
    """Transfer playback to another speaker.
    
    Note: This uses grouping - joins target to source, then ungroups source.
    """
    # Group target with source (source is playing)
    success = await _get_soco_service().group_speakers(speaker_name, target_speaker)
    if success:
        # Ungroup the original speaker, leaving target playing
        await _get_soco_service().ungroup_speaker(speaker_name)
    return {"success": success}


# ========================================
# Playback Settings (uses SoCo directly)
# ========================================


@router.get("/speakers/{speaker_name}/shuffle")
async def get_shuffle(speaker_name: str) -> dict:
    """Get shuffle mode using SoCo library."""
    shuffle = await _get_soco_service().get_shuffle(speaker_name)
    return {"shuffle": shuffle or False}


@router.post("/speakers/{speaker_name}/shuffle/{state}")
async def set_shuffle(speaker_name: str, state: str) -> dict:
    """Set shuffle mode using SoCo library."""
    enabled = state.lower() in ("on", "true", "1")
    success = await _get_soco_service().set_shuffle(speaker_name, enabled)
    return {"success": success}


@router.get("/speakers/{speaker_name}/repeat")
async def get_repeat(speaker_name: str) -> dict:
    """Get repeat mode using SoCo library."""
    repeat = await _get_soco_service().get_repeat(speaker_name)
    return {"repeat": repeat or "off"}


@router.post("/speakers/{speaker_name}/repeat/{mode}")
async def set_repeat(speaker_name: str, mode: str) -> dict:
    """Set repeat mode using SoCo library."""
    success = await _get_soco_service().set_repeat(speaker_name, mode)
    return {"success": success}


@router.get("/speakers/{speaker_name}/crossfade")
async def get_crossfade(speaker_name: str) -> dict:
    """Get crossfade mode using SoCo library."""
    crossfade = await _get_soco_service().get_crossfade(speaker_name)
    return {"crossfade": crossfade or False}


@router.post("/speakers/{speaker_name}/crossfade/{state}")
async def set_crossfade(speaker_name: str, state: str) -> dict:
    """Set crossfade mode using SoCo library."""
    enabled = state.lower() in ("on", "true", "1")
    success = await _get_soco_service().set_crossfade(speaker_name, enabled)
    return {"success": success}


@router.get("/speakers/{speaker_name}/sleep")
async def get_sleep_timer(speaker_name: str) -> dict:
    """Get sleep timer using SoCo library."""
    remaining = await _get_soco_service().get_sleep_timer(speaker_name)
    return {"remaining": remaining or 0}


@router.post("/speakers/{speaker_name}/sleep/{duration}")
async def set_sleep_timer(speaker_name: str, duration: str) -> dict:
    """Set sleep timer using SoCo library."""
    # Parse duration - could be minutes or HH:MM:SS
    try:
        if ":" in duration:
            # Parse HH:MM:SS format
            parts = duration.split(":")
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            # Assume minutes
            seconds = int(duration) * 60
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid duration format")
    
    success = await _get_soco_service().set_sleep_timer(speaker_name, seconds)
    return {"success": success}


@router.delete("/speakers/{speaker_name}/sleep")
async def cancel_sleep_timer(speaker_name: str) -> dict:
    """Cancel sleep timer using SoCo library."""
    success = await _get_soco_service().set_sleep_timer(speaker_name, None)
    return {"success": success}


@router.post("/speakers/{speaker_name}/seek/{position}")
async def seek(speaker_name: str, position: str) -> dict:
    """Seek to a position in the current track using SoCo library."""
    success = await _get_soco_service().seek(speaker_name, position)
    return {"success": success}


# ========================================
# Favorites and Playlists
# ========================================


def _parse_numbered_list(output: str | None) -> list[ListItem]:
    """Parse a numbered list from soco-cli output."""
    items: list[ListItem] = []
    if not output:
        return items
    
    # Known soco-cli status responses that should not be parsed as list items
    invalid_responses = {
        "on", "off", "stopped", "playing", "paused", "transitioning",
        "in progress", "shuffle", "repeat", "crossfade",
    }
    
    for line in output.split("\n"):
        trimmed = line.strip()
        if not trimmed:
            continue
        
        # Skip known status responses
        if trimmed.lower() in invalid_responses:
            continue
        
        colon_index = trimmed.find(":")
        if colon_index > 0:
            try:
                number = int(trimmed[:colon_index].strip())
                name = trimmed[colon_index + 1:].strip()
                if name and name.lower() not in invalid_responses:
                    items.append(ListItem(number=number, name=name))
            except ValueError:
                pass
    
    return items


def _parse_queue_list(output: str | None) -> list[QueueItem]:
    """Parse queue items from soco-cli output."""
    items: list[QueueItem] = []
    if not output:
        return items
    
    for line in output.split("\n"):
        if not line.strip():
            continue
        
        # Check for current track marker (* or *>) and remove it
        is_current = "*" in line
        trimmed = line.replace("*>", "").replace("*", "").strip()
        
        # Find the first colon (after the track number)
        first_colon = trimmed.find(":")
        if first_colon <= 0:
            continue
        
        # Try to parse the track number
        try:
            number = int(trimmed[:first_colon].strip())
        except ValueError:
            continue
        
        content = trimmed[first_colon + 1:].strip()
        
        # Parse Artist: X | Album: Y | Title: Z format
        artist = ""
        album = ""
        title = ""
        
        parts = content.split("|")
        for part in parts:
            part = part.strip()
            if part.lower().startswith("artist:"):
                artist = part[7:].strip()
            elif part.lower().startswith("album:"):
                album = part[6:].strip()
            elif part.lower().startswith("title:"):
                title = part[6:].strip()
        
        # If no structured format, use the whole content as title
        if not title and not artist:
            title = content
        
        items.append(QueueItem(
            number=number,
            title=title,
            artist=artist,
            album=album,
            is_current=is_current,
        ))
    
    return items


@router.get("/favorites")
async def get_favorites() -> dict:
    """Get all Sonos favorites using SoCo library."""
    speakers = await _get_soco_service().discover_speakers()
    if not speakers:
        return {"favorites": []}
    
    favorites = await _get_soco_service().get_favorites(speakers[0])
    return {"favorites": [f.model_dump(by_alias=True) for f in favorites]}


@router.post("/speakers/{speaker_name}/play-favorite/{favorite_name}")
async def play_favorite(speaker_name: str, favorite_name: str) -> dict:
    """Play a favorite by name using SoCo library."""
    success = await _get_soco_service().play_favorite(speaker_name, favorite_name)
    return {"success": success}


@router.post("/speakers/{speaker_name}/play-favorite-number/{number}")
async def play_favorite_by_number(speaker_name: str, number: int) -> dict:
    """Play a favorite by number using SoCo library."""
    success = await _get_soco_service().play_favorite_by_number(speaker_name, number)
    return {"success": success}


@router.get("/playlists")
async def get_playlists() -> dict:
    """Get all Sonos playlists using SoCo library."""
    playlists = await _get_soco_service().get_playlists()
    return {"playlists": [p.model_dump(by_alias=True) for p in playlists]}


@router.get("/playlists/{playlist_name}/tracks")
async def get_playlist_tracks(playlist_name: str) -> dict:
    """Get tracks in a playlist using SoCo library."""
    tracks = await _get_soco_service().get_playlist_tracks(playlist_name)
    return {"tracks": [t.model_dump(by_alias=True) for t in tracks]}


@router.get("/radio-stations")
async def get_radio_stations() -> dict:
    """Get favorite radio stations (TuneIn) using SoCo library."""
    stations = await _get_soco_service().get_radio_stations()
    return {"stations": [s.model_dump(by_alias=True) for s in stations]}


@router.post("/speakers/{speaker_name}/play-radio/{station_name}")
async def play_radio_station(speaker_name: str, station_name: str) -> dict:
    """Play a radio station using SoCo library."""
    success = await _get_soco_service().play_radio_station(speaker_name, station_name)
    return {"success": success}


# ========================================
# Queue Management
# ========================================


@router.get("/speakers/{speaker_name}/queue")
async def get_queue(speaker_name: str) -> dict:
    """Get the current queue using SoCo library."""
    queue = await _get_soco_service().get_queue(speaker_name)
    return {"tracks": [t.model_dump(by_alias=True) for t in queue]}


@router.get("/speakers/{speaker_name}/queue/length")
async def get_queue_length(speaker_name: str) -> dict:
    """Get the queue length using SoCo library."""
    length = await _get_soco_service().get_queue_length(speaker_name)
    return {"length": length}


@router.get("/speakers/{speaker_name}/queue/position")
async def get_queue_position(speaker_name: str) -> dict:
    """Get the current queue position using SoCo library."""
    position = await _get_soco_service().get_queue_position(speaker_name)
    return {"position": position}


@router.post("/speakers/{speaker_name}/queue/play/{track_number}")
async def play_from_queue(speaker_name: str, track_number: int) -> dict:
    """Play a track from the queue using SoCo library."""
    success = await _get_soco_service().play_from_queue(speaker_name, track_number)
    return {"success": success}


@router.post("/speakers/{speaker_name}/queue/play")
async def play_queue(speaker_name: str) -> dict:
    """Play the queue from the beginning using SoCo library."""
    success = await _get_soco_service().play_from_queue(speaker_name, 1)
    return {"success": success}


@router.delete("/speakers/{speaker_name}/queue")
async def clear_queue(speaker_name: str) -> dict:
    """Clear the queue using SoCo library."""
    success = await _get_soco_service().clear_queue(speaker_name)
    return {"success": success}


@router.delete("/speakers/{speaker_name}/queue/{track_number}")
async def remove_from_queue(speaker_name: str, track_number: int) -> dict:
    """Remove a track from the queue using SoCo library."""
    success = await _get_soco_service().remove_from_queue(speaker_name, track_number)
    return {"success": success}


@router.post("/speakers/{speaker_name}/queue/add-favorite/{favorite_name}")
async def add_favorite_to_queue(speaker_name: str, favorite_name: str) -> dict:
    """Add a favorite to the queue using SoCo library."""
    position = await _get_soco_service().add_favorite_to_queue(speaker_name, favorite_name)
    return {"success": position is not None, "position": position}


@router.post("/speakers/{speaker_name}/queue/add-playlist/{playlist_name}")
async def add_playlist_to_queue(speaker_name: str, playlist_name: str) -> dict:
    """Add a playlist to the queue using SoCo library."""
    position = await _get_soco_service().add_playlist_to_queue(speaker_name, playlist_name)
    return {"success": position is not None, "position": position}


@router.post("/speakers/{speaker_name}/queue/add-sharelink")
async def add_share_link_to_queue(speaker_name: str, request: ShareLinkRequest) -> SocoCliResponse:
    """Add a share link (Spotify, Apple Music, etc.) to the queue.
    
    Note: Share links require soco-cli for parsing music service URLs.
    """
    return await _get_command_service().execute_command(speaker_name, "add_sharelink_to_queue", request.url)


@router.post("/speakers/{speaker_name}/queue/save/{playlist_name}")
async def save_queue_as_playlist(speaker_name: str, playlist_name: str) -> SocoCliResponse:
    """Save the current queue as a playlist.
    
    Note: This uses soco-cli as SoCo doesn't have a direct create_sonos_playlist from queue method.
    """
    return await _get_command_service().execute_command(speaker_name, "save_queue", playlist_name)
