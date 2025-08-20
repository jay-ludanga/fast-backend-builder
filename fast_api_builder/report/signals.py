
# Single post_save handler for multiple models
from typing import List, Type
from tortoise import Model

from fast_api_builder.muarms.models.iop import InvestmentOpportunity, Progress, RegistrationProject, OutwardInvestment, \
    Project
from fast_api_builder.report.service import ReportService
from tortoise.signals import post_save

async def shared_post_save_handler(
    sender: Type[Model],
    instance: Model,
    created: bool,
    using_db,
    update_fields: List[str],
) -> None:
    if isinstance(instance, Progress) and instance.evaluation_status == "APPROVED":
        await ReportService().update_report_for([sender])
        
    if isinstance(instance, InvestmentOpportunity) and instance.evaluation_status == "APPROVED":
        await ReportService().update_report_for([sender])
    
    else:
        await ReportService().update_report_for([sender])

post_save(Progress)(shared_post_save_handler)
post_save(InvestmentOpportunity)(shared_post_save_handler)
post_save(RegistrationProject)(shared_post_save_handler)
post_save(OutwardInvestment)(shared_post_save_handler)
post_save(Project)(shared_post_save_handler)