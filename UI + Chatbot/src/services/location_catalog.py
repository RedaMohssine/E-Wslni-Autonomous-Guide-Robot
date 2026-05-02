import json
import re
from pathlib import Path
from typing import Iterable, List, Optional
from unicodedata import normalize

from rapidfuzz import process, fuzz

from src.models import Destination


DEFAULT_CATEGORY_BY_NAME = {
    "cafeteria": "alimentation",
    "cafétéria": "alimentation",
    "student lounge": "détente",
    "foyer étudiant": "détente",
    "administration": "administratif",
    "reception": "administratif",
    "réception": "administratif",
    "accueil": "administratif",
    "health center": "santé",
    "centre de santé": "santé",
    "laboratoire de physique expérimentale": "laboratoire",
    "laboratoire de projet d'ingénierie": "laboratoire",
    "laboratoire de mécatronique": "laboratoire",
    "radio étudiante": "média",
    "bureau e-tech": "clubs",
    "bureau e-olive": "clubs",
    "bureau e-mix": "clubs",
    "service d'impression": "services",
    "toilettes": "sanitaires",
}


class LocationCatalogService:
    def __init__(self, locations_file: str = "data/locations.json"):
        self.locations_file = Path(locations_file)
        self._locations = self._load_locations()
        
        # Pre-compute normalized strings for rapidfuzz on startup (makes it instant)
        self._fuzzy_choices_strings: List[str] = []
        self._fuzzy_choices_map: List[Destination] = []
        
        for loc in self._locations:
            # Add canonical name
            self._add_fuzzy_choice(loc.location_name, loc)
            # Add all aliases
            for alias in loc.aliases:
                self._add_fuzzy_choice(alias, loc)

    def _add_fuzzy_choice(self, text: str, location: Destination):
        normalized = self._normalize_text(text)
        self._fuzzy_choices_strings.append(normalized)
        self._fuzzy_choices_map.append(location)

    def _load_locations(self) -> List[Destination]:
        with self.locations_file.open("r", encoding="utf-8") as handle:
            raw_locations = json.load(handle)

        locations: List[Destination] = []
        for raw_location in raw_locations:
            coords = raw_location.get("coordinates", {})
            location_name = str(raw_location.get("location_name", "")).strip()
            aliases = self._normalize_aliases(raw_location.get("aliases"))
            category = self._normalize_category(raw_location.get("category"), location_name)

            locations.append(
                Destination(
                    location_name=location_name,
                    category=category,
                    description=str(raw_location.get("description", "")).strip(),
                    latitude=float(coords.get("latitude", 0.0)),
                    longitude=float(coords.get("longitude", 0.0)),
                    building=str(raw_location.get("building", "")).strip(),
                    floor=str(raw_location.get("floor", "")).strip(),
                    accessible=bool(raw_location.get("accessible", False)),
                    aliases=aliases,
                )
            )

        return sorted(locations, key=lambda location: (location.category, location.location_name))

    def _normalize_aliases(self, raw_aliases: object) -> List[str]:
        if raw_aliases is None:
            return []

        values: Iterable[object]
        if isinstance(raw_aliases, list):
            values = raw_aliases
        elif isinstance(raw_aliases, str):
            values = raw_aliases.split(",")
        else:
            values = [raw_aliases]

        aliases: List[str] = []
        seen: set[str] = set()
        for raw_alias in values:
            alias = " ".join(str(raw_alias).strip().split())
            if not alias:
                continue

            alias_key = alias.lower()
            if alias_key in seen:
                continue

            seen.add(alias_key)
            aliases.append(alias)

        return aliases

    def _normalize_category(self, raw_category: object, location_name: str) -> str:
        category = str(raw_category or "").strip()
        if category:
            return category
        return DEFAULT_CATEGORY_BY_NAME.get(location_name.lower(), "autres")

    def list_locations(self) -> List[Destination]:
        return list(self._locations)

    def get_categories(self) -> List[str]:
        return sorted({location.category for location in self._locations})

    def get_location(self, location_name: str) -> Optional[Destination]:
        lookup = self._normalize_text(location_name)
        for location in self._locations:
            if self._normalize_text(location.location_name) == lookup:
                return location
        return None

    def search_locations(
        self,
        query: str = "",
        category: str = "All",
        limit: Optional[int] = None,
    ) -> List[Destination]:
        # Strict matching for the UI search bar
        normalized_query = self._normalize_text(query)
        normalized_category = self._normalize_text(category)

        filtered = [
            location
            for location in self._locations
            if (
                normalized_category in {"", "all", "toutes"}
                or normalized_category.startswith("toutes les cat")
                or normalized_category.startswith("tous les empl")
            )
            or self._normalize_text(location.category) == normalized_category
        ]

        if not normalized_query:
            return filtered[:limit] if limit else filtered

        query_tokens = [token for token in normalized_query.split() if token]
        matching_locations = [
            location
            for location in filtered
            if all(token in self._normalize_text(location.location_name) for token in query_tokens)
        ]
        return matching_locations[:limit] if limit else matching_locations

    # ====================================================================
    # RAPIDFUZZ VOICE / LLM MATCHING
    # ====================================================================
    def resolve_location(self, user_input: str, threshold: int = 75) -> Optional[Destination]:
        """Fuzzy matches user voice/text input against all names and aliases."""
        if not user_input:
            return None
            
        normalized_input = self._normalize_text(user_input)
        if not normalized_input:
            return None

        # WRatio is the best scorer for phrases with missing/extra words or typos
        match, score, idx = process.extractOne(
            normalized_input, 
            self._fuzzy_choices_strings, 
            scorer=fuzz.WRatio
        )

        # If score is above threshold, return the mapped Destination object
        if score >= threshold:
            return self._fuzzy_choices_map[idx]
            
        return None

    # ====================================================================
    # HELPERS
    # ====================================================================
    def _normalize_text(self, value: str) -> str:
        """Strips accents and lowercases for rapidfuzz comparison."""
        normalized = normalize("NFKD", value or "")
        return "".join(char for char in normalized if ord(char) < 128).lower().strip()

    def _tokenize(self, value: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", value)