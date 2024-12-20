from nautobot.apps.jobs import register_jobs
from jobs import SiteImportJob

register_jobs(SiteImportJob)