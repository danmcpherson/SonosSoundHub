"""Service for direct SoCo library operations.

This service uses the SoCo Python library directly for speaker discovery,
playback control, volume, and other basic operations. This is faster and
more reliable than routing through soco-cli HTTP API.

soco-cli is still used for macro execution (complex chained commands).
"""

import asyncio
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import soco
from soco import SoCo
from soco.exceptions import SoCoException

from ..config import Settings
from ..models import Speaker, Favorite, QueueItem, ListItem

logger = logging.getLogger(__name__)


class SoCoService:
    """Service for direct SoCo library operations."""
    
    def __init__(self, settings: Settings):
        """Initialize the service.
        
        Args:
            settings: Application settings.
        """
        self._settings = settings
        self._speakers_cache: dict[str, SoCo] = {}
        self._last_discovery: datetime | None = None
        self._discovery_lock = asyncio.Lock()
    
    def _scan_ip_for_sonos(self, ip: str) -> tuple[str, str] | None:
        """Check if a Sonos speaker exists at the given IP.
        
        Returns:
            Tuple of (ip, speaker_name) if found, None otherwise.
        """
        try:
            result = subprocess.run(
                ["curl", "-s", "--connect-timeout", "1", f"http://{ip}:1400/status/zp"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if "ZPSupportInfo" in result.stdout:
                match = re.search(r'<ZoneName>([^<]+)</ZoneName>', result.stdout)
                if match:
                    return (ip, match.group(1))
        except Exception:
            pass
        return None
    
    def _discover_by_ip_scan(self, subnet: str = "192.168.1") -> dict[str, SoCo]:
        """Fallback discovery by scanning IP range.
        
        Used when multicast discovery doesn't work (e.g., Docker).
        Only returns visible speakers (excludes bonded subs, surrounds).
        """
        speakers: dict[str, SoCo] = {}
        ips_to_scan = [f"{subnet}.{i}" for i in range(1, 255)]
        
        logger.info("Falling back to IP scan discovery on %s.x", subnet)
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(self._scan_ip_for_sonos, ip): ip for ip in ips_to_scan}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    ip, _ = result  # Ignore XML name, use SoCo's player_name instead
                    try:
                        device = SoCo(ip)
                        # Only include visible speakers (not bonded subs/surrounds)
                        if not device.is_visible:
                            logger.debug("Skipping non-visible speaker at %s", ip)
                            continue
                        # Use SoCo's player_name for consistency with other SoCo APIs
                        name = device.player_name
                        if name:
                            speakers[name] = device
                            logger.info("Found speaker via IP scan: %s at %s", name, ip)
                    except Exception as e:
                        logger.debug("Could not connect to %s: %s", ip, e)
        
        return speakers
    
    async def discover_speakers(self, force: bool = False) -> list[str]:
        """Discover all Sonos speakers on the network.
        
        Args:
            force: Force rediscovery even if cache is fresh.
            
        Returns:
            List of speaker names.
        """
        async with self._discovery_lock:
            # Use cached results if available and not forcing
            if not force and self._speakers_cache and self._last_discovery:
                age = (datetime.now(timezone.utc) - self._last_discovery).total_seconds()
                if age < 300:  # Cache for 5 minutes
                    return list(self._speakers_cache.keys())
            
            # Run discovery in thread pool (blocking I/O)
            try:
                speakers = await asyncio.to_thread(soco.discover, timeout=5)
                
                if speakers:
                    # Filter to only visible speakers (excludes bonded subs, surrounds)
                    self._speakers_cache = {
                        speaker.player_name: speaker
                        for speaker in speakers
                        if speaker.player_name and speaker.is_visible
                    }
                    self._last_discovery = datetime.now(timezone.utc)
                    logger.info("Discovered %d visible speakers via multicast", len(self._speakers_cache))
                    return list(self._speakers_cache.keys())
                else:
                    logger.warning("Multicast discovery found no speakers, trying IP scan")
                    # Fallback to IP scan (useful in Docker where multicast doesn't work)
                    scanned = await asyncio.to_thread(self._discover_by_ip_scan)
                    if scanned:
                        self._speakers_cache = scanned
                        self._last_discovery = datetime.now(timezone.utc)
                        logger.info("Discovered %d visible speakers via IP scan", len(self._speakers_cache))
                        return list(self._speakers_cache.keys())
                    return []
                    
            except Exception as e:
                logger.error("Speaker discovery failed: %s", e)
                return list(self._speakers_cache.keys())  # Return cached if discovery fails
    
    def _get_speaker(self, name: str) -> SoCo | None:
        """Get a speaker by name from cache.
        
        Args:
            name: Speaker name.
            
        Returns:
            SoCo instance or None if not found.
        """
        return self._speakers_cache.get(name)
    
    async def get_speaker_info(self, speaker_name: str) -> Speaker:
        """Get detailed information about a speaker.
        
        Args:
            speaker_name: Name of the speaker.
            
        Returns:
            Speaker information.
        """
        speaker = Speaker(name=speaker_name)
        device = self._get_speaker(speaker_name)
        
        if not device:
            # Try discovery if speaker not in cache
            await self.discover_speakers(force=True)
            device = self._get_speaker(speaker_name)
            
        if not device:
            speaker.is_offline = True
            speaker.error_message = "Speaker not found"
            return speaker
        
        try:
            # Run all blocking calls in thread pool
            info = await asyncio.to_thread(self._get_speaker_info_sync, device)
            speaker.volume = info.get("volume")
            speaker.is_muted = info.get("is_muted", False)
            speaker.playback_state = info.get("playback_state")
            speaker.current_track = info.get("current_track")
            speaker.ip_address = info.get("ip_address")
            speaker.model = info.get("model")
            speaker.is_coordinator = info.get("is_coordinator", False)
            speaker.group_members = info.get("group_members", [])
            
            # Battery level for portable speakers
            battery = info.get("battery_level")
            if battery is not None:
                speaker.battery_level = battery
                
        except SoCoException as e:
            error_str = str(e)
            # Satellite speakers (surrounds, subs) often return empty responses
            if error_str == "b''" or not error_str:
                logger.debug("Satellite speaker %s doesn't support this operation", speaker_name)
                speaker.error_message = "Satellite speaker - view main speaker"
            else:
                logger.error("SoCo error for %s: %s", speaker_name, e)
                speaker.is_offline = True
                speaker.error_message = error_str
        except Exception as e:
            logger.error("Failed to get speaker info for %s: %s", speaker_name, e)
            speaker.error_message = str(e)
        
        return speaker
    
    def _get_speaker_info_sync(self, device: SoCo) -> dict[str, Any]:
        """Synchronous helper to get speaker info (runs in thread pool)."""
        info: dict[str, Any] = {}
        
        try:
            info["volume"] = device.volume
            info["is_muted"] = device.mute
            info["ip_address"] = device.ip_address
            
            # Check if coordinator
            info["is_coordinator"] = device.is_coordinator
            
            # For grouped speakers, get playback state from coordinator
            playback_device = device
            if device.group and not device.is_coordinator:
                playback_device = device.group.coordinator
            
            # Get playback state (from coordinator if grouped)
            transport_info = playback_device.get_current_transport_info()
            state = transport_info.get("current_transport_state", "UNKNOWN")
            info["playback_state"] = state
            
            # Get current track (from coordinator if grouped)
            track_info = playback_device.get_current_track_info()
            title = track_info.get("title", "")
            artist = track_info.get("artist", "")
            if title and artist:
                info["current_track"] = f"{artist} - {title}"
            elif title:
                info["current_track"] = title
            
            # Get speaker info
            speaker_info = device.get_speaker_info()
            info["model"] = speaker_info.get("model_name", "")
            
            # Get group members
            if device.group:
                info["group_members"] = [
                    m.player_name for m in device.group.members
                    if m.player_name != device.player_name
                ]
            
            # Try to get battery level (for Roam, Move, etc.)
            try:
                battery_info = device.get_battery_info()
                if battery_info and "Level" in battery_info:
                    info["battery_level"] = int(battery_info["Level"])
            except (SoCoException, AttributeError):
                pass  # Not a portable speaker
                
        except Exception as e:
            logger.warning("Error getting info for %s: %s", device.player_name, e)
            raise
        
        return info
    
    def _get_playback_device(self, device: SoCo) -> SoCo:
        """Get the playback device (coordinator) for transport operations.
        
        Transport operations (play, pause, next, previous, etc.) must be
        executed on the group coordinator, not on member speakers.
        
        Args:
            device: The SoCo device instance.
            
        Returns:
            The coordinator if grouped, otherwise the device itself.
        """
        try:
            if device.group and not device.is_coordinator:
                return device.group.coordinator
        except Exception:
            pass  # If we can't get group info, use the device itself
        return device
    
    async def get_playback_state(self, speaker_name: str) -> str:
        """Get just the playback state (fast, minimal UPnP calls).
        
        Args:
            speaker_name: Name of the speaker.
            
        Returns:
            Playback state: 'PLAYING', 'PAUSED_PLAYBACK', 'STOPPED', or 'UNKNOWN'
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return "UNKNOWN"
        try:
            def get_state():
                # For grouped speakers, get state from coordinator
                if device.group and not device.is_coordinator:
                    transport = device.group.coordinator.get_current_transport_info()
                else:
                    transport = device.get_current_transport_info()
                return transport.get("current_transport_state", "UNKNOWN")
            
            return await asyncio.to_thread(get_state)
        except Exception as e:
            logger.error("Get playback state failed for %s: %s", speaker_name, e)
            return "UNKNOWN"
    
    async def play(self, speaker_name: str) -> bool:
        """Start playback on a speaker.
        
        Uses the group coordinator for grouped speakers.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        try:
            def _play():
                playback_device = self._get_playback_device(device)
                playback_device.play()
            await asyncio.to_thread(_play)
            return True
        except Exception as e:
            logger.error("Play failed for %s: %s", speaker_name, e)
            return False
    
    async def pause(self, speaker_name: str) -> bool:
        """Pause playback on a speaker.
        
        Uses the group coordinator for grouped speakers.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        try:
            def _pause():
                playback_device = self._get_playback_device(device)
                playback_device.pause()
            await asyncio.to_thread(_pause)
            return True
        except Exception as e:
            logger.error("Pause failed for %s: %s", speaker_name, e)
            return False
    
    async def stop(self, speaker_name: str) -> bool:
        """Stop playback on a speaker.
        
        Uses the group coordinator for grouped speakers.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        try:
            def _stop():
                playback_device = self._get_playback_device(device)
                playback_device.stop()
            await asyncio.to_thread(_stop)
            return True
        except Exception as e:
            logger.error("Stop failed for %s: %s", speaker_name, e)
            return False
    
    async def next_track(self, speaker_name: str) -> bool:
        """Skip to next track.
        
        Uses the group coordinator for grouped speakers.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        try:
            def _next():
                playback_device = self._get_playback_device(device)
                playback_device.next()
            await asyncio.to_thread(_next)
            return True
        except Exception as e:
            logger.error("Next track failed for %s: %s", speaker_name, e)
            return False
    
    async def previous_track(self, speaker_name: str) -> bool:
        """Skip to previous track.
        
        Uses the group coordinator for grouped speakers.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        try:
            def _previous():
                playback_device = self._get_playback_device(device)
                playback_device.previous()
            await asyncio.to_thread(_previous)
            return True
        except Exception as e:
            logger.error("Previous track failed for %s: %s", speaker_name, e)
            return False
    
    async def set_volume(self, speaker_name: str, volume: int) -> bool:
        """Set speaker volume (0-100)."""
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        try:
            volume = max(0, min(100, volume))
            await asyncio.to_thread(setattr, device, "volume", volume)
            return True
        except Exception as e:
            logger.error("Set volume failed for %s: %s", speaker_name, e)
            return False
    
    async def get_volume(self, speaker_name: str) -> int | None:
        """Get speaker volume (fast, single UPnP call).
        
        Args:
            speaker_name: Name of the speaker.
            
        Returns:
            Volume (0-100) or None if failed.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return None
        try:
            return await asyncio.to_thread(lambda: device.volume)
        except Exception as e:
            logger.error("Get volume failed for %s: %s", speaker_name, e)
            return None
    
    async def get_mute(self, speaker_name: str) -> bool | None:
        """Get speaker mute state (fast, single UPnP call).
        
        Args:
            speaker_name: Name of the speaker.
            
        Returns:
            True if muted, False if not, None if failed.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return None
        try:
            return await asyncio.to_thread(lambda: device.mute)
        except Exception as e:
            logger.error("Get mute failed for %s: %s", speaker_name, e)
            return None
    
    async def get_current_track(self, speaker_name: str) -> str | None:
        """Get current track info (fast, minimal UPnP calls).
        
        Args:
            speaker_name: Name of the speaker.
            
        Returns:
            Track string like "Artist - Title" or None if failed.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return None
        try:
            def get_track():
                # For grouped speakers, get track from coordinator
                if device.group and not device.is_coordinator:
                    track_info = device.group.coordinator.get_current_track_info()
                else:
                    track_info = device.get_current_track_info()
                title = track_info.get("title", "")
                artist = track_info.get("artist", "")
                if title and artist:
                    return f"{artist} - {title}"
                return title or None
            
            return await asyncio.to_thread(get_track)
        except Exception as e:
            logger.error("Get current track failed for %s: %s", speaker_name, e)
            return None
    
    async def set_mute(self, speaker_name: str, mute: bool) -> bool:
        """Set speaker mute state."""
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        try:
            await asyncio.to_thread(setattr, device, "mute", mute)
            return True
        except Exception as e:
            logger.error("Set mute failed for %s: %s", speaker_name, e)
            return False
    
    def _get_any_coordinator(self) -> SoCo | None:
        """Get any coordinator speaker from the cache.
        
        Coordinators are needed for operations like getting favorites.
        Non-coordinator speakers (satellites) may fail these operations.
        
        Returns:
            A coordinator SoCo instance, or None if none found.
        """
        for device in self._speakers_cache.values():
            try:
                if device.is_coordinator:
                    return device
            except Exception:
                continue
        # Fallback to any speaker
        return next(iter(self._speakers_cache.values()), None) if self._speakers_cache else None
    
    async def get_favorites(self, speaker_name: str) -> list[Favorite]:
        """Get Sonos favorites.
        
        Args:
            speaker_name: Any speaker name (favorites are system-wide).
            
        Returns:
            List of favorites.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            # Try to get a coordinator (needed for favorites)
            device = await asyncio.to_thread(self._get_any_coordinator)
            if not device:
                return []
        
        # Need to use the group coordinator
        try:
            coordinator = await asyncio.to_thread(lambda: device.group.coordinator)
            device = coordinator
        except Exception:
            pass  # Use original device if group.coordinator fails
        
        try:
            favorites = await asyncio.to_thread(self._get_favorites_sync, device)
            return favorites
        except Exception as e:
            logger.error("Failed to get favorites: %s", e)
            return []
    
    def _get_favorites_sync(self, device: SoCo) -> list[Favorite]:
        """Synchronous helper to get favorites."""
        favorites: list[Favorite] = []
        try:
            music_library = device.music_library
            sonos_favorites = music_library.get_sonos_favorites()
            
            for i, fav in enumerate(sonos_favorites):
                favorites.append(Favorite(
                    id=str(i),
                    name=fav.title,
                    album_art_uri=getattr(fav, "album_art_uri", None),
                ))
        except Exception as e:
            logger.warning("Error getting favorites: %s", e)
        
        return favorites
    
    async def play_favorite(self, speaker_name: str, favorite_name: str) -> bool:
        """Play a Sonos favorite by name.
        
        Args:
            speaker_name: Speaker to play on.
            favorite_name: Name of the favorite to play.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            result = await asyncio.to_thread(
                self._play_favorite_sync, device, favorite_name
            )
            return result
        except Exception as e:
            logger.error("Failed to play favorite %s: %s", favorite_name, e)
            return False
    
    def _play_favorite_sync(self, device: SoCo, favorite_name: str) -> bool:
        """Synchronous helper to play a favorite.
        
        Handles track/album favorites by adding to queue and playing.
        Container-type favorites (artists, playlists from streaming services)
        are not currently supported by SoCo and will return False.
        """
        try:
            # Use coordinator for playback operations
            playback_device = self._get_playback_device(device)
            music_library = playback_device.music_library
            favorites = music_library.get_sonos_favorites()
            
            for fav in favorites:
                if fav.title.lower() == favorite_name.lower():
                    # Check if favorite has resources (track/album type)
                    if fav.resources:
                        # Track/album - add to queue and play
                        playback_device.clear_queue()
                        playback_device.add_to_queue(fav)
                        playback_device.play_from_queue(0)
                        return True
                    else:
                        # Container type (artist/playlist from streaming service)
                        # SoCo does not support playing these directly
                        logger.warning(
                            "Favorite '%s' is a container type (artist/playlist) which "
                            "cannot be played directly. Only track/album favorites are supported.",
                            favorite_name
                        )
                        return False
            
            logger.warning("Favorite not found: %s", favorite_name)
            return False
            
        except Exception as e:
            logger.error("Error playing favorite: %s", e)
            return False
    
    async def play_favorite_by_number(self, speaker_name: str, number: int) -> bool:
        """Play a Sonos favorite by its number (1-based).
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker to play on.
            number: 1-based index of the favorite.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _play_favorite_by_number():
                playback_device = self._get_playback_device(device)
                favorites = playback_device.music_library.get_sonos_favorites()
                if number < 1 or number > len(favorites):
                    raise ValueError(f"Favorite number {number} out of range (1-{len(favorites)})")
                
                fav = favorites[number - 1]  # Convert 1-based to 0-based
                playback_device.clear_queue()
                playback_device.add_to_queue(fav)
                playback_device.play_from_queue(0)
            
            await asyncio.to_thread(_play_favorite_by_number)
            return True
        except Exception as e:
            logger.error("Failed to play favorite #%d: %s", number, e)
            return False
    
    async def get_queue(self, speaker_name: str) -> list[QueueItem]:
        """Get the current queue for a speaker.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            
        Returns:
            List of queue items.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return []
        
        try:
            def _get_queue():
                playback_device = self._get_playback_device(device)
                return self._get_queue_sync(playback_device)
            queue = await asyncio.to_thread(_get_queue)
            return queue
        except Exception as e:
            logger.error("Failed to get queue for %s: %s", speaker_name, e)
            return []
    
    def _get_queue_sync(self, device: SoCo) -> list[QueueItem]:
        """Synchronous helper to get queue."""
        items: list[QueueItem] = []
        try:
            queue = device.get_queue()
            for i, item in enumerate(queue):
                items.append(QueueItem(
                    position=i + 1,
                    title=item.title,
                    artist=getattr(item, "creator", None),
                    album=getattr(item, "album", None),
                    album_art_uri=getattr(item, "album_art_uri", None),
                ))
        except Exception as e:
            logger.warning("Error getting queue: %s", e)
        
        return items
    
    async def get_groups(self) -> list[dict[str, Any]]:
        """Get all speaker groups.
        
        Returns:
            List of groups with coordinator and members.
        """
        # Ensure we have speakers
        if not self._speakers_cache:
            await self.discover_speakers()
        
        if not self._speakers_cache:
            return []
        
        try:
            # Get any speaker to query groups
            device = next(iter(self._speakers_cache.values()))
            groups = await asyncio.to_thread(self._get_groups_sync, device)
            return groups
        except Exception as e:
            logger.error("Failed to get groups: %s", e)
            return []
    
    def _get_groups_sync(self, device: SoCo) -> list[dict[str, Any]]:
        """Synchronous helper to get groups."""
        groups: list[dict[str, Any]] = []
        seen_coordinators: set[str] = set()
        
        try:
            # Get all zones
            zones = device.all_zones
            
            for zone in zones:
                # Only include visible coordinators (not bonded satellites)
                if zone.is_coordinator and zone.is_visible:
                    coord_name = zone.player_name
                    if coord_name in seen_coordinators:
                        continue
                    seen_coordinators.add(coord_name)
                    
                    members = []
                    if zone.group:
                        # Only include visible members (not bonded subs/surrounds)
                        members = [
                            m.player_name for m in zone.group.members
                            if m.player_name != coord_name and m.is_visible
                        ]
                    
                    groups.append({
                        "coordinator": coord_name,
                        "members": members,
                    })
                    
        except Exception as e:
            logger.warning("Error getting groups: %s", e)
        
        return groups
    
    async def group_speakers(self, coordinator: str, member: str) -> bool:
        """Add a speaker to a group.
        
        Args:
            coordinator: Name of the coordinator speaker.
            member: Name of the speaker to add to the group.
            
        Returns:
            True if successful.
        """
        coord_device = self._get_speaker(coordinator)
        member_device = self._get_speaker(member)
        
        if not coord_device or not member_device:
            return False
        
        try:
            await asyncio.to_thread(member_device.join, coord_device)
            return True
        except Exception as e:
            logger.error("Failed to group %s with %s: %s", member, coordinator, e)
            return False
    
    async def ungroup_speaker(self, speaker_name: str) -> bool:
        """Remove a speaker from its group.
        
        Args:
            speaker_name: Name of the speaker to ungroup.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            await asyncio.to_thread(device.unjoin)
            return True
        except Exception as e:
            logger.error("Failed to ungroup %s: %s", speaker_name, e)
            return False
    
    async def party_mode(self, speaker_name: str) -> bool:
        """Group all speakers together with the given speaker as coordinator.
        
        Args:
            speaker_name: Name of the coordinator speaker.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            await asyncio.to_thread(device.partymode)
            return True
        except Exception as e:
            logger.error("Failed to activate party mode on %s: %s", speaker_name, e)
            return False
    
    async def ungroup_all(self, speaker_name: str) -> bool:
        """Ungroup all speakers.
        
        Args:
            speaker_name: Any speaker name (used to get zone list).
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _ungroup_all():
                for zone in device.all_zones:
                    if zone.is_visible and not zone.is_coordinator:
                        try:
                            zone.unjoin()
                        except Exception:
                            pass
            await asyncio.to_thread(_ungroup_all)
            return True
        except Exception as e:
            logger.error("Failed to ungroup all: %s", e)
            return False
    
    async def set_group_volume(self, speaker_name: str, volume: int) -> bool:
        """Set volume for all speakers in a group.
        
        Args:
            speaker_name: Name of any speaker in the group.
            volume: Volume level (0-100).
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            await asyncio.to_thread(setattr, device, "group_volume", volume)
            return True
        except Exception as e:
            logger.error("Failed to set group volume on %s: %s", speaker_name, e)
            return False
    
    async def get_shuffle(self, speaker_name: str) -> bool | None:
        """Get shuffle mode.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            
        Returns:
            True if shuffle is on, False if off, None on error.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return None
        
        try:
            def _get_shuffle():
                playback_device = self._get_playback_device(device)
                return playback_device.shuffle
            shuffle = await asyncio.to_thread(_get_shuffle)
            return shuffle
        except Exception as e:
            logger.error("Failed to get shuffle for %s: %s", speaker_name, e)
            return None
    
    async def set_shuffle(self, speaker_name: str, enabled: bool) -> bool:
        """Set shuffle mode.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            enabled: True to enable, False to disable.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _set_shuffle():
                playback_device = self._get_playback_device(device)
                playback_device.shuffle = enabled
            await asyncio.to_thread(_set_shuffle)
            return True
        except Exception as e:
            logger.error("Failed to set shuffle for %s: %s", speaker_name, e)
            return False
    
    async def get_repeat(self, speaker_name: str) -> str | None:
        """Get repeat mode.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            
        Returns:
            'off', 'one', or 'all', or None on error.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return None
        
        try:
            def _get_repeat():
                playback_device = self._get_playback_device(device)
                # SoCo repeat returns: False (off), True (all), or 'ONE' (one)
                repeat = playback_device.repeat
                if repeat is False:
                    return "off"
                elif repeat is True:
                    return "all"
                elif repeat == "ONE":
                    return "one"
                return "off"
            return await asyncio.to_thread(_get_repeat)
        except Exception as e:
            logger.error("Failed to get repeat for %s: %s", speaker_name, e)
            return None
    
    async def set_repeat(self, speaker_name: str, mode: str) -> bool:
        """Set repeat mode.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            mode: 'off', 'one', or 'all'.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _set_repeat():
                playback_device = self._get_playback_device(device)
                # SoCo repeat accepts: False (off), True (all), or 'ONE' (one)
                mode_lower = mode.lower()
                if mode_lower == "off":
                    playback_device.repeat = False
                elif mode_lower == "all":
                    playback_device.repeat = True
                elif mode_lower == "one":
                    playback_device.repeat = "ONE"
                else:
                    playback_device.repeat = False
            await asyncio.to_thread(_set_repeat)
            return True
        except Exception as e:
            logger.error("Failed to set repeat for %s: %s", speaker_name, e)
            return False
    
    async def get_crossfade(self, speaker_name: str) -> bool | None:
        """Get crossfade mode.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            
        Returns:
            True if crossfade is on, False if off, None on error.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return None
        
        try:
            def _get_crossfade():
                playback_device = self._get_playback_device(device)
                return playback_device.cross_fade
            crossfade = await asyncio.to_thread(_get_crossfade)
            return crossfade
        except Exception as e:
            logger.error("Failed to get crossfade for %s: %s", speaker_name, e)
            return None
    
    async def set_crossfade(self, speaker_name: str, enabled: bool) -> bool:
        """Set crossfade mode.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            enabled: True to enable, False to disable.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _set_crossfade():
                playback_device = self._get_playback_device(device)
                playback_device.cross_fade = enabled
            await asyncio.to_thread(_set_crossfade)
            return True
        except Exception as e:
            logger.error("Failed to set crossfade for %s: %s", speaker_name, e)
            return False
    
    async def get_sleep_timer(self, speaker_name: str) -> int | None:
        """Get remaining sleep timer in seconds.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            
        Returns:
            Remaining seconds, 0 if no timer, None on error.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return None
        
        try:
            def _get_sleep_timer():
                playback_device = self._get_playback_device(device)
                return playback_device.get_sleep_timer()
            timer = await asyncio.to_thread(_get_sleep_timer)
            return timer or 0
        except Exception as e:
            logger.error("Failed to get sleep timer for %s: %s", speaker_name, e)
            return None
    
    async def set_sleep_timer(self, speaker_name: str, seconds: int | None) -> bool:
        """Set or cancel sleep timer.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            seconds: Seconds until sleep, or None to cancel.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _set_sleep_timer():
                playback_device = self._get_playback_device(device)
                playback_device.set_sleep_timer(seconds)
            await asyncio.to_thread(_set_sleep_timer)
            return True
        except Exception as e:
            logger.error("Failed to set sleep timer for %s: %s", speaker_name, e)
            return False
    
    async def seek(self, speaker_name: str, position: str) -> bool:
        """Seek to a position in the current track.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            position: Position in HH:MM:SS format.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _seek():
                playback_device = self._get_playback_device(device)
                playback_device.seek(position)
            await asyncio.to_thread(_seek)
            return True
        except Exception as e:
            logger.error("Failed to seek on %s: %s", speaker_name, e)
            return False
    
    # ========================================
    # Queue Operations
    # ========================================
    
    async def get_queue_length(self, speaker_name: str) -> int:
        """Get the number of items in the queue.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            
        Returns:
            Queue length.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return 0
        
        try:
            def _get_queue_length():
                playback_device = self._get_playback_device(device)
                return playback_device.queue_size
            length = await asyncio.to_thread(_get_queue_length)
            return length or 0
        except Exception as e:
            logger.error("Failed to get queue length for %s: %s", speaker_name, e)
            return 0
    
    async def get_queue_position(self, speaker_name: str) -> int:
        """Get the current position in the queue.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            
        Returns:
            Current position (1-based).
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return 0
        
        try:
            def _get_queue_position():
                playback_device = self._get_playback_device(device)
                track_info = playback_device.get_current_track_info()
                return int(track_info.get("playlist_position", 0))
            position = await asyncio.to_thread(_get_queue_position)
            return position
        except Exception as e:
            logger.error("Failed to get queue position for %s: %s", speaker_name, e)
            return 0
    
    async def play_from_queue(self, speaker_name: str, position: int) -> bool:
        """Play a specific track from the queue.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            position: Track position (0-based index).
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _play_from_queue():
                playback_device = self._get_playback_device(device)
                playback_device.play_from_queue(position)
            await asyncio.to_thread(_play_from_queue)
            return True
        except Exception as e:
            logger.error("Failed to play from queue on %s: %s", speaker_name, e)
            return False
    
    async def clear_queue(self, speaker_name: str) -> bool:
        """Clear the queue.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _clear_queue():
                playback_device = self._get_playback_device(device)
                playback_device.clear_queue()
            await asyncio.to_thread(_clear_queue)
            return True
        except Exception as e:
            logger.error("Failed to clear queue on %s: %s", speaker_name, e)
            return False
    
    async def remove_from_queue(self, speaker_name: str, position: int) -> bool:
        """Remove a track from the queue.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            position: Track position (0-based index).
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _remove_from_queue():
                playback_device = self._get_playback_device(device)
                playback_device.remove_from_queue(position)
            await asyncio.to_thread(_remove_from_queue)
            return True
        except Exception as e:
            logger.error("Failed to remove from queue on %s: %s", speaker_name, e)
            return False
    
    async def add_uri_to_queue(self, speaker_name: str, uri: str) -> bool:
        """Add a URI to the queue.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            uri: URI to add.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _add_uri_to_queue():
                playback_device = self._get_playback_device(device)
                playback_device.add_uri_to_queue(uri)
            await asyncio.to_thread(_add_uri_to_queue)
            return True
        except Exception as e:
            logger.error("Failed to add to queue on %s: %s", speaker_name, e)
            return False
    
    async def add_favorite_to_queue(self, speaker_name: str, favorite_name: str) -> int | None:
        """Add a favorite to the queue.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            favorite_name: Name of the favorite to add.
            
        Returns:
            Queue position of added item, or None if failed.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return None
        
        try:
            def _add_favorite_to_queue():
                playback_device = self._get_playback_device(device)
                favorites = playback_device.music_library.get_sonos_favorites()
                for fav in favorites:
                    if fav.title.lower() == favorite_name.lower():
                        return playback_device.add_to_queue(fav)
                logger.error("Favorite '%s' not found", favorite_name)
                return None
            result = await asyncio.to_thread(_add_favorite_to_queue)
            return result
        except Exception as e:
            logger.error("Failed to add favorite to queue on %s: %s", speaker_name, e)
            return None
    
    async def add_playlist_to_queue(self, speaker_name: str, playlist_name: str) -> int | None:
        """Add a Sonos playlist to the queue.
        
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            playlist_name: Name of the playlist to add.
            
        Returns:
            Queue position of first added item, or None if failed.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return None
        
        try:
            def _add_playlist_to_queue():
                playback_device = self._get_playback_device(device)
                playlists = playback_device.get_sonos_playlists()
                for pl in playlists:
                    if pl.title.lower() == playlist_name.lower():
                        return playback_device.add_to_queue(pl)
                logger.error("Playlist '%s' not found", playlist_name)
                return None
            result = await asyncio.to_thread(_add_playlist_to_queue)
            return result
        except Exception as e:
            logger.error("Failed to add playlist to queue on %s: %s", speaker_name, e)
            return None
    
    async def play_radio_station(self, speaker_name: str, station_name: str) -> bool:
        """Play a radio station from Sonos favorites.
        
        Radio stations are stored in Sonos favorites in modern Sonos systems.
        Uses the group coordinator for grouped speakers.
        
        Args:
            speaker_name: Speaker name.
            station_name: Name of the radio station.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            def _play_radio_station():
                playback_device = self._get_playback_device(device)
                # Radio stations are now stored in Sonos favorites
                favorites = playback_device.music_library.get_sonos_favorites()
                for fav in favorites:
                    if fav.title.lower() == station_name.lower():
                        # Check if it has resources (playable item)
                        if fav.resources:
                            uri = fav.resources[0].uri
                            meta = fav.resource_meta_data
                            playback_device.play_uri(uri, meta=meta)
                            return True
                        else:
                            # Try play_uri with just the reference
                            logger.warning(
                                "Favorite '%s' has no resources, may not play correctly",
                                station_name
                            )
                            return False
                logger.error("Radio station '%s' not found in favorites", station_name)
                return False
            result = await asyncio.to_thread(_play_radio_station)
            return result
        except Exception as e:
            logger.error("Failed to play radio station on %s: %s", speaker_name, e)
            return False
    
    async def get_playlists(self, speaker_name: str | None = None) -> list[ListItem]:
        """Get list of Sonos playlists.
        
        Args:
            speaker_name: Any speaker name (optional).
            
        Returns:
            List of ListItem models.
        """
        device = None
        if speaker_name:
            device = self._get_speaker(speaker_name)
        if not device:
            # Try any speaker
            device = await asyncio.to_thread(self._get_any_coordinator)
            if not device:
                return []
        
        try:
            playlists = await asyncio.to_thread(device.get_sonos_playlists)
            return [ListItem(number=i + 1, name=p.title) for i, p in enumerate(playlists)]
        except Exception as e:
            logger.error("Failed to get playlists: %s", e)
            return []
    
    async def get_playlist_tracks(self, playlist_name: str, speaker_name: str | None = None) -> list[ListItem]:
        """Get tracks in a Sonos playlist.
        
        Args:
            playlist_name: Name of the playlist.
            speaker_name: Any speaker name (optional).
            
        Returns:
            List of ListItem models with track names.
        """
        device = None
        if speaker_name:
            device = self._get_speaker(speaker_name)
        if not device:
            device = await asyncio.to_thread(self._get_any_coordinator)
            if not device:
                return []
        
        try:
            playlists = await asyncio.to_thread(device.get_sonos_playlists)
            for pl in playlists:
                if pl.title.lower() == playlist_name.lower():
                    # Get the playlist tracks using browse
                    def get_tracks():
                        return device.music_library.browse(pl)
                    
                    items = await asyncio.to_thread(get_tracks)
                    return [ListItem(number=i + 1, name=item.title) for i, item in enumerate(items)]
            logger.error("Playlist '%s' not found", playlist_name)
            return []
        except Exception as e:
            logger.error("Failed to get playlist tracks: %s", e)
            return []
    
    async def get_radio_stations(self, speaker_name: str | None = None) -> list[ListItem]:
        """Get list of favorite radio stations.
        
        Args:
            speaker_name: Any speaker name (optional).
            
        Returns:
            List of ListItem models.
        """
        device = None
        if speaker_name:
            device = self._get_speaker(speaker_name)
        if not device:
            device = await asyncio.to_thread(self._get_any_coordinator)
            if not device:
                return []
        
        try:
            stations = await asyncio.to_thread(device.get_favorite_radio_stations)
            return [ListItem(number=i + 1, name=s.title) for i, s in enumerate(stations)]
        except Exception as e:
            logger.error("Failed to get radio stations: %s", e)
            return []
    
    async def play_uri(self, speaker_name: str, uri: str) -> bool:
        """Play a URI.
        
        Args:
            speaker_name: Speaker name.
            uri: URI to play.
            
        Returns:
            True if successful.
        """
        device = self._get_speaker(speaker_name)
        if not device:
            return False
        
        try:
            await asyncio.to_thread(device.play_uri, uri)
            return True
        except Exception as e:
            logger.error("Failed to play URI on %s: %s", speaker_name, e)
            return False
