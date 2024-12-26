# type: ignore
"""Use retrieve device OS version and document in Nautobot LCM app."""

import csv
import io

from nautobot.extras.jobs import Job, FileVar
from nautobot.dcim.models import (
    Location
)

STATE_MAP = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming"
}

class SiteImportJob(Job):
    """Import Sites job"""

    class Meta:
        """Job attributes."""

        name = "Load CSV for sites"
        description = "Load CSV"
        read_only = False
        approval_required = False
        has_sensitive_variables = False
        
    inputfile = FileVar(required=True)
 
    def run(self, inputfile, *args, **kwargs):
        textbuffer = io.TextIOWrapper(inputfile)
        reader = csv.DictReader(textbuffer)
        for row in reader:
            normalized_row = self.normalize_data(row)
            device, created = Location.objects.update_or_create(
                name=normalized_row['name'],
                physical_address=f"{normalized_row['city']}, {normalized_row['state']}"
            )

            verb = "Created" if created else "Updated"
            self.logger.info(
                obj=device,
                message=f"{verb} {device.name}",
            )

        return super().run(*args, **kwargs)

    def normalize_data(self, row: dict[str,str]) -> dict[str, str]:
        valid_suffixes = {
            "-DC": None, 
            "-BR": None
        }

        assert row['name'][-3:] in valid_suffixes, f"Invalid suffix for site {row['name']}"

        row['state'] = valid_suffixes.get(row['state'], row['state'])

        return row
