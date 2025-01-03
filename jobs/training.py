# type: ignore
"""Use retrieve device OS version and document in Nautobot LCM app."""

import csv
import io

from nautobot.extras.jobs import Job, FileVar
from nautobot.dcim.models import (
    Location, LocationType
)
from nautobot.extras.models import Status

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
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sitemapper = {
            "-DC": LocationType.objects.get(name="Data Center"),
            "-BR": LocationType.objects.get(name="Branch")
        }
 
    def run(self, inputfile, *args, **kwargs):
        textbuffer = io.TextIOWrapper(inputfile)
        reader = csv.DictReader(textbuffer)
        active = Status.objects.get(name="Active")
        for row in reader:
            normalized_row = self.normalize_data(row)
            device, created = Location.objects.update_or_create(
                name=normalized_row['name'],
                physical_address=f"{normalized_row['city']}, {normalized_row['state']}",
                location_type=normalized_row["site_type"],
                status=active
            )

            verb = "Created" if created else "Updated"
            self.logger.info("%s %s" % (verb, device.name))

    def normalize_data(self, row: dict[str,str]) -> dict[str, str]:
        try:
            row['site_type'] = self.sitemapper[row["name"][-3:]]
        except KeyError:
            raise ValueError(f"Invalid suffix for site {row['name']}")
        
        row['state'] = STATE_MAP.get(row['state'], row['state'])

        return row
