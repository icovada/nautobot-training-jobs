# type: ignore
"""Use retrieve device OS version and document in Nautobot LCM app."""

import csv

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
 
    def run(self, *args, **kwargs):
        with open(self.inputfile, "r") as csvfile:
            reader = csv.DictReader(csvfile)
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

        assert row['city'][:-3] in valid_suffixes, "Invalid suffix"

        row['state'] = valid_suffixes.get(row['state'], row['state'])

        return row



class CreateSoftwareRel(Job):
    """Retrieve os_version and build Software to Device relationship."""

    class Meta:
        """Job attributes."""

        name = "Get Device OS Version"
        description = "Get OS version, build device to software relationship"
        read_only = False
        approval_required = False
        has_sensitive_variables = False

    # Form fields
    tenant_group = MultiObjectVar(model=TenantGroup, required=False)
    tenant = MultiObjectVar(model=Tenant, required=False)
    region = MultiObjectVar(model=Region, required=False)
    site = MultiObjectVar(model=Site, required=False)
    role = MultiObjectVar(model=DeviceRole, required=False)
    manufacturer = MultiObjectVar(model=Manufacturer, required=False)
    platform = MultiObjectVar(model=Platform, required=False)
    device_type = MultiObjectVar(model=DeviceType, required=False)
    device = MultiObjectVar(model=Device, required=False)
    tag = MultiObjectVar(model=Tag, required=False)

    def run(self, data, commit) -> None:
        """Run get os version job."""
        # Init Nornir and run configure device task for each device
        try:
            with init_nornir(data) as nornir_obj:
                nr = nornir_obj
                nr.run(
                    task=self._get_os_version,
                    name=self.name,
                )
        except Exception as err:
            self.log_failure(None, f"```\n{err}\n```")
            raise

    def _get_os_version(self, task: Task) -> Result:
        """Get_facts, update OS Version in Nautobot."""
        # Get device object
        device_obj = task.host.data["obj"]

        # Run NAPALM task to retrieve os_version
        try:
            facts = task.run(task=napalm_get, getters="get_facts")
        except Exception as err:
            self.log_failure(
                obj=device_obj, message=f"FAILED:\n```\n{err.result.exception}\n```"
            )
            raise

        get_facts_version = facts.result["get_facts"]["os_version"]
        software_rel_id = Relationship.objects.get(
            name="Software on Device").id

        # Check if software exists in nautobot database. If not, create it.
        if SoftwareLCM.objects.filter(version=get_facts_version).exists():
            software = SoftwareLCM.objects.get(version=get_facts_version)
        else:
            platform = device_obj.platform
            software = SoftwareLCM(
                version=get_facts_version, device_platform=platform)
            software.validated_save()
            self.log_info(
                obj=software, message=f"Created software version {software.version}"
            )

        # Check if software to dev relationship already exists. If not, create it.
        if RelationshipAssociation.objects.filter(
            relationship=software_rel_id,
            source_id=software.id,
            destination_id=device_obj.id,
        ).exists():
            self.log_info(
                obj=device_obj,
                message=f"Relationship {device_obj.name} <-> {software} exists.",
            )
        else:
            rel_type = Relationship.objects.get(name="Software on Device")
            source_ct = ContentType.objects.get(model="softwarelcm")
            dest_ct = ContentType.objects.get(model="device")
            created_rel = RelationshipAssociation(
                relationship=rel_type,
                source_type=source_ct,
                source=software,
                destination_type=dest_ct,
                destination=device_obj,
            )
            created_rel.validated_save()
            self.log_success(
                obj=device_obj,
                message=f"Created {device_obj.name} <-> {software} relationship.",
            )
