from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import TravelEstimate


@dataclass(frozen=True)
class GeocodeResult:
    lat: float
    lng: float
    provider: str
    confidence_score: float
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TravelEstimateResult:
    origin_text: str
    destination_text: str
    origin_lat: float | None
    origin_lng: float | None
    destination_lat: float | None
    destination_lng: float | None
    drive_minutes: float | None
    drive_hours: float | None
    distance_miles: float | None
    provider: str
    confidence_score: float
    metadata: dict = field(default_factory=dict)
    cached: bool = False
    is_manual_override: bool = False
    error_message: str | None = None


class TravelProvider(Protocol):
    name: str

    def geocode(self, location_text: str) -> GeocodeResult:
        ...

    def calculate_drive_time(self, origin_text: str, destination_text: str) -> TravelEstimateResult:
        ...

    def calculate_drive_time_from_coordinates(
        self,
        *,
        origin_text: str,
        destination_text: str,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
    ) -> TravelEstimateResult:
        ...


class OpenRouteServiceProvider:
    name = "openrouteservice"

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def geocode(self, location_text: str) -> GeocodeResult:
        if not self.api_key:
            raise ValueError("OpenRouteService API key is not configured.")
        url = "https://api.openrouteservice.org/geocode/search?" + urlencode(
            {"api_key": self.api_key, "text": location_text, "size": 1}
        )
        data = self._json(Request(url))
        first = data["features"][0]
        lng, lat = first["geometry"]["coordinates"]
        confidence = float(first.get("properties", {}).get("confidence") or 0.75)
        return GeocodeResult(
            lat=lat,
            lng=lng,
            provider="openrouteservice_geocoding",
            confidence_score=confidence,
            metadata={"id": first.get("id"), "label": first.get("properties", {}).get("label")},
        )

    def calculate_drive_time(self, origin_text: str, destination_text: str) -> TravelEstimateResult:
        origin = self.geocode(origin_text)
        destination = self.geocode(destination_text)
        result = self.calculate_drive_time_from_coordinates(
            origin_text=origin_text,
            destination_text=destination_text,
            origin_lat=origin.lat,
            origin_lng=origin.lng,
            destination_lat=destination.lat,
            destination_lng=destination.lng,
        )
        result.metadata.update(
            {
                "origin_geocoder": origin.provider,
                "destination_geocoder": destination.provider,
                "origin_metadata": origin.metadata,
                "destination_metadata": destination.metadata,
            }
        )
        return TravelEstimateResult(
            **{
                **result.__dict__,
                "confidence_score": min(result.confidence_score, origin.confidence_score, destination.confidence_score),
            }
        )

    def calculate_drive_time_from_coordinates(
        self,
        *,
        origin_text: str,
        destination_text: str,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
    ) -> TravelEstimateResult:
        if not self.api_key:
            raise ValueError("OpenRouteService API key is not configured.")
        body = json.dumps(
            {
                "coordinates": [[origin_lng, origin_lat], [destination_lng, destination_lat]],
                "units": "mi",
            }
        ).encode("utf-8")
        request = Request(
            "https://api.openrouteservice.org/v2/directions/driving-car",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": self.api_key,
            },
            method="POST",
        )
        data = self._json(request)
        summary = data["routes"][0]["summary"]
        drive_minutes = float(summary["duration"]) / 60
        distance_miles = float(summary["distance"])
        return TravelEstimateResult(
            origin_text=origin_text,
            destination_text=destination_text,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            drive_minutes=drive_minutes,
            drive_hours=drive_minutes / 60,
            distance_miles=distance_miles,
            provider="openrouteservice_directions",
            confidence_score=0.9,
            metadata={"routing_endpoint": "directions/driving-car"},
        )

    def _json(self, request: Request) -> dict | list:
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))


class TravelService:
    """Provider-based geocoding and drive-time calculation with database caching."""

    def __init__(self, db: Session | None) -> None:
        self.db = db
        self.settings = get_settings()

    def audition_travel(
        self,
        *,
        origin_text: str | None,
        audition_location: str | None,
        audition_type: str,
        manual_drive_hours: float | None = None,
    ) -> TravelEstimateResult | None:
        if audition_type in {"Self-Tape", "Virtual"}:
            return TravelEstimateResult(
                origin_text=origin_text or "",
                destination_text=audition_location or "Remote audition",
                origin_lat=None,
                origin_lng=None,
                destination_lat=None,
                destination_lng=None,
                drive_minutes=0,
                drive_hours=0,
                distance_miles=0,
                provider="remote_audition",
                confidence_score=1.0,
                metadata={"reason": "Self-tape and virtual auditions require no audition travel."},
            )
        if not origin_text or not audition_location:
            return None
        return self.drive_time(
            origin_text=origin_text,
            destination_text=audition_location,
            manual_drive_hours=manual_drive_hours,
        )

    def production_travel(
        self,
        *,
        origin_text: str | None,
        production_location: str | None,
        manual_drive_hours: float | None = None,
    ) -> TravelEstimateResult | None:
        if not origin_text or not production_location:
            return None
        return self.drive_time(
            origin_text=origin_text,
            destination_text=production_location,
            manual_drive_hours=manual_drive_hours,
        )

    def provider_status(self) -> dict:
        provider = str(self.settings.travel_provider or "manual").lower()
        configured = {
            "google": bool(self.settings.google_maps_api_key),
            "mapbox": bool(self.settings.mapbox_access_token),
            "openrouteservice": bool(self.settings.openrouteservice_api_key),
            "ors": bool(self.settings.openrouteservice_api_key),
            "auto": bool(
                self.settings.google_maps_api_key
                or self.settings.mapbox_access_token
                or self.settings.openrouteservice_api_key
            ),
            "manual": True,
        }.get(provider, False)
        return {
            "provider": provider,
            "state": "Configured" if configured and provider != "manual" else "Manual Entry Required" if provider == "manual" else "Not Configured",
            "configured": configured,
            "cache_days": self.settings.travel_cache_days,
            "safe_fallback": "Manual Override",
        }

    def geocode(self, location_text: str) -> GeocodeResult | None:
        provider = self._active_provider()
        if not provider:
            return None
        try:
            return provider.geocode(location_text)
        except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def calculate_drive_time(self, origin_text: str, destination_text: str) -> TravelEstimateResult | None:
        return self.drive_time(origin_text=origin_text, destination_text=destination_text)

    def calculate_drive_time_from_coordinates(
        self,
        *,
        origin_text: str,
        destination_text: str,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
    ) -> TravelEstimateResult | None:
        provider = self._active_provider()
        if not provider:
            return None
        try:
            return provider.calculate_drive_time_from_coordinates(
                origin_text=origin_text,
                destination_text=destination_text,
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                destination_lat=destination_lat,
                destination_lng=destination_lng,
            )
        except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def drive_time(
        self,
        *,
        origin_text: str,
        destination_text: str,
        manual_drive_hours: float | None = None,
    ) -> TravelEstimateResult | None:
        origin_text = origin_text.strip()
        destination_text = destination_text.strip()
        cached = self._cached(origin_text, destination_text)
        if cached:
            return self._from_model(cached, cached=True)

        result = self._provider_drive_time(origin_text, destination_text)
        if result is None and manual_drive_hours is not None:
            minutes = manual_drive_hours * 60
            result = TravelEstimateResult(
                origin_text=origin_text,
                destination_text=destination_text,
                origin_lat=None,
                origin_lng=None,
                destination_lat=None,
                destination_lng=None,
                drive_minutes=minutes,
                drive_hours=manual_drive_hours,
                distance_miles=None,
                provider="manual_override",
                confidence_score=0.7,
                metadata={"label": "User-entered estimate", "provider_failed": True},
                is_manual_override=True,
            )
        if result:
            self._store(result)
        return result

    def _provider_drive_time(self, origin_text: str, destination_text: str) -> TravelEstimateResult | None:
        provider = str(self.settings.travel_provider or "manual").lower()
        providers = [provider] if provider != "auto" else ["google", "mapbox", "openrouteservice"]
        for candidate in providers:
            try:
                if candidate in {"openrouteservice", "ors"} and self.settings.openrouteservice_api_key:
                    return OpenRouteServiceProvider(self.settings.openrouteservice_api_key).calculate_drive_time(
                        origin_text,
                        destination_text,
                    )
                if candidate == "google" and self.settings.google_maps_api_key:
                    return self._google_drive_time(origin_text, destination_text)
                if candidate == "mapbox" and self.settings.mapbox_access_token:
                    return self._mapbox_drive_time(origin_text, destination_text)
            except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
                continue
        return None

    def _active_provider(self) -> TravelProvider | None:
        provider = str(self.settings.travel_provider or "manual").lower()
        if provider in {"openrouteservice", "ors"} and self.settings.openrouteservice_api_key:
            return OpenRouteServiceProvider(self.settings.openrouteservice_api_key)
        return None

    def _google_drive_time(self, origin_text: str, destination_text: str) -> TravelEstimateResult:
        origin = self._google_geocode(origin_text)
        destination = self._google_geocode(destination_text)
        body = json.dumps(
            {
                "origins": [{"waypoint": {"location": {"latLng": {"latitude": origin.lat, "longitude": origin.lng}}}}],
                "destinations": [{"waypoint": {"location": {"latLng": {"latitude": destination.lat, "longitude": destination.lng}}}}],
                "travelMode": "DRIVE",
            }
        ).encode("utf-8")
        request = Request(
            "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.settings.google_maps_api_key or "",
                "X-Goog-FieldMask": "duration,distanceMeters,status",
            },
            method="POST",
        )
        data = self._json(request)
        item = data[0] if isinstance(data, list) else data
        seconds = self._duration_seconds(item["duration"])
        miles = float(item.get("distanceMeters") or 0) / 1609.344
        return self._result(origin_text, destination_text, origin, destination, seconds / 60, miles, "google_routes", 0.95)

    def _mapbox_drive_time(self, origin_text: str, destination_text: str) -> TravelEstimateResult:
        origin = self._mapbox_geocode(origin_text)
        destination = self._mapbox_geocode(destination_text)
        coords = f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"
        url = (
            f"https://api.mapbox.com/directions-matrix/v1/mapbox/driving/{coords}?"
            + urlencode({"annotations": "duration,distance", "access_token": self.settings.mapbox_access_token or ""})
        )
        data = self._json(Request(url))
        minutes = float(data["durations"][0][1]) / 60
        miles = float(data["distances"][0][1]) / 1609.344
        return self._result(origin_text, destination_text, origin, destination, minutes, miles, "mapbox_matrix", 0.9)

    def _google_geocode(self, text: str) -> GeocodeResult:
        url = "https://maps.googleapis.com/maps/api/geocode/json?" + urlencode(
            {"address": text, "key": self.settings.google_maps_api_key or ""}
        )
        data = self._json(Request(url))
        first = data["results"][0]
        location = first["geometry"]["location"]
        return GeocodeResult(location["lat"], location["lng"], "google_geocoding", 0.95, {"place_id": first.get("place_id")})

    def _mapbox_geocode(self, text: str) -> GeocodeResult:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(text)}.json?" + urlencode(
            {"access_token": self.settings.mapbox_access_token or "", "limit": 1}
        )
        data = self._json(Request(url))
        first = data["features"][0]
        lng, lat = first["center"]
        return GeocodeResult(lat, lng, "mapbox_geocoding", float(first.get("relevance") or 0.8), {"id": first.get("id")})

    def _result(
        self,
        origin_text: str,
        destination_text: str,
        origin: GeocodeResult,
        destination: GeocodeResult,
        drive_minutes: float,
        distance_miles: float | None,
        provider: str,
        confidence_score: float,
    ) -> TravelEstimateResult:
        return TravelEstimateResult(
            origin_text=origin_text,
            destination_text=destination_text,
            origin_lat=origin.lat,
            origin_lng=origin.lng,
            destination_lat=destination.lat,
            destination_lng=destination.lng,
            drive_minutes=drive_minutes,
            drive_hours=drive_minutes / 60,
            distance_miles=distance_miles,
            provider=provider,
            confidence_score=min(confidence_score, origin.confidence_score, destination.confidence_score),
            metadata={
                "origin_geocoder": origin.provider,
                "destination_geocoder": destination.provider,
                "origin_metadata": origin.metadata,
                "destination_metadata": destination.metadata,
            },
        )

    def _cached(self, origin_text: str, destination_text: str) -> TravelEstimate | None:
        if not self.db:
            return None
        now = datetime.now(timezone.utc)
        return self.db.scalars(
            select(TravelEstimate)
            .where(TravelEstimate.origin_text == self._cache_key(origin_text))
            .where(TravelEstimate.destination_text == self._cache_key(destination_text))
            .where(TravelEstimate.expires_at > now)
            .limit(1)
        ).first()

    def _store(self, result: TravelEstimateResult) -> None:
        if not self.db:
            return
        now = datetime.now(timezone.utc)
        existing = self.db.scalars(
            select(TravelEstimate)
            .where(TravelEstimate.origin_text == self._cache_key(result.origin_text))
            .where(TravelEstimate.destination_text == self._cache_key(result.destination_text))
            .limit(1)
        ).first()
        estimate = existing or TravelEstimate(
            origin_text=self._cache_key(result.origin_text),
            destination_text=self._cache_key(result.destination_text),
            calculated_at=now,
            expires_at=now + timedelta(days=self.settings.travel_cache_days),
        )
        estimate.origin_lat = result.origin_lat
        estimate.origin_lng = result.origin_lng
        estimate.destination_lat = result.destination_lat
        estimate.destination_lng = result.destination_lng
        estimate.drive_minutes = result.drive_minutes
        estimate.drive_hours = result.drive_hours
        estimate.distance_miles = result.distance_miles
        estimate.provider = result.provider
        estimate.confidence_score = result.confidence_score
        estimate.calculated_at = now
        estimate.expires_at = now + timedelta(days=self.settings.travel_cache_days)
        estimate.is_manual_override = result.is_manual_override
        estimate.error_message = result.error_message
        if not existing:
            self.db.add(estimate)

    def _from_model(self, estimate: TravelEstimate, cached: bool) -> TravelEstimateResult:
        return TravelEstimateResult(
            origin_text=estimate.origin_text,
            destination_text=estimate.destination_text,
            origin_lat=estimate.origin_lat,
            origin_lng=estimate.origin_lng,
            destination_lat=estimate.destination_lat,
            destination_lng=estimate.destination_lng,
            drive_minutes=estimate.drive_minutes,
            drive_hours=estimate.drive_hours,
            distance_miles=estimate.distance_miles,
            provider=estimate.provider,
            confidence_score=estimate.confidence_score,
            metadata={"cache": "hit"},
            cached=cached,
            is_manual_override=estimate.is_manual_override,
            error_message=estimate.error_message,
        )

    def _json(self, request: Request) -> dict | list:
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))

    def _duration_seconds(self, value: str | int | float) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value).replace("s", ""))

    def _cache_key(self, text: str) -> str:
        return " ".join(str(text or "").lower().strip().split())
