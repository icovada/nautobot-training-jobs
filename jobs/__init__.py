from nautobot.apps.jobs import register_jobs
from .training import SiteImportJob

register_jobs(SiteImportJob)

