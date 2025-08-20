import uuid
from typing import Any, Dict, List

from tortoise import fields
from tortoise.queryset import Q

from fast_api_builder.muarms.enums import HeadshipType
from fast_api_builder.muarms.models import TimeStampedModel
from fast_api_builder.muarms.models.lookups import District, Institution, Region
from tortoise.transactions import in_transaction


# Registration Project as per registration
class RegistrationProject(TimeStampedModel):
    name = fields.CharField(max_length=200)
    project_number = fields.CharField(max_length=45)
    registration_date = fields.DateField()
    commencement_date = fields.DateField()
    specific_activity = fields.CharField(max_length=1000, null=True)

    # enum field with values in CapitalSource enum
    local_equity = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    local_loan = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    foreign_equity = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    foreign_loan = fields.DecimalField(max_digits=20, decimal_places=2, default=0)

    # enum field with values in ProductionSource enum
    production_source = fields.CharField(max_length=45, null=True)
    # enum field with values in OwnershipType enum
    ownership_type = fields.CharField(max_length=45, null=True)
    land_size = fields.CharField(max_length=45, null=True)
    investment_capital = fields.FloatField(null=True)

    total_local_employment = fields.IntField(default=0)
    total_foreign_employment = fields.IntField(default=0)
    male_local_employment = fields.IntField(default=0)
    female_local_employment = fields.IntField(default=0)
    male_foreign_employment = fields.IntField(default=0)
    female_foreign_employment = fields.IntField(default=0)

    production_capacity = fields.CharField(max_length=45, null=True)
    # enum field with values in ProjectStatus
    status = fields.CharField(max_length=45, null=True)
    # used for saving verification status as well as time verified
    verified_at = fields.DatetimeField(null=True)

    institution = fields.ForeignKeyField('models.Institution', related_name='registration_projects',
                                         on_delete=fields.RESTRICT)
    registration_company = fields.ForeignKeyField('models.RegistrationCompany', related_name='registration_projects',
                                                  on_delete=fields.RESTRICT)
    sector = fields.ForeignKeyField('models.Sector', related_name='registration_projects', on_delete=fields.RESTRICT)

    # Locations
    region = fields.CharField(max_length=45)
    district = fields.CharField(max_length=100)
    ward = fields.CharField(max_length=100)
    street = fields.CharField(max_length=100, null=True)

    created_by = fields.ForeignKeyField(
        "models.User",
        null=True,
        on_delete=fields.SET_NULL,
        related_name="registration_projects_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "registration_projects"
        verbose_name = "Registration Project"
        verbose_name_plural = "Registration Projects"
        unique_together = (("project_number", "institution"),)  # Unique constraint on project_number and institution

    def __str__(self):
        return f"{self.name} ({self.project_number})"

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'institution_id',
                'path': None
            }
        ]


# Company Contact person
class ContactPerson(TimeStampedModel):
    name = fields.CharField(max_length=50)
    phone_number = fields.CharField(max_length=25)
    email = fields.CharField(max_length=50)

    class Meta:
        table = "contact_person"
        verbose_name = "Contact Person"
        verbose_name_plural = "Contact Persons"

    def __str__(self):
        return self.name


# Registration Company
class RegistrationCompany(TimeStampedModel):
    name = fields.CharField(max_length=200)
    incorporation_number = fields.CharField(max_length=20)
    contact_person = fields.ForeignKeyField('models.ContactPerson', related_name='registration_companies',
                                            on_delete=fields.RESTRICT)
    address = fields.CharField(max_length=100)

    class Meta:
        table = "registration_companies"
        verbose_name = "Registration Company"
        verbose_name_plural = "Registration Companies"

    def __str__(self):
        return self.name


# Registration Shareholder
class RegistrationShareholder(TimeStampedModel):
    name = fields.CharField(max_length=50)
    share_value = fields.FloatField()
    registration_company = fields.ForeignKeyField('models.RegistrationCompany',
                                                  related_name='registration_shareholders',
                                                  on_delete=fields.RESTRICT)
    country = fields.ForeignKeyField('models.Country', related_name='registration_shareholders',
                                     on_delete=fields.RESTRICT)

    class Meta:
        table = "registration_shareholders"
        verbose_name = "Registration Shareholder"
        verbose_name_plural = "Registration Shareholders"

    def __str__(self):
        return self.name


"""
THE FOLLOWING ARE MODELS AS PER VERIFIED PROJECTS
"""


class Project(TimeStampedModel):
    # Fields from Project model
    name = fields.CharField(max_length=210)
    project_number = fields.CharField(max_length=45, null=True)
    registration_date = fields.DateField()
    commencement_date = fields.DateField()
    specific_activity = fields.CharField(max_length=1000)
    capital_source = fields.CharField(max_length=45, null=True)
    land_size = fields.CharField(max_length=45, null=True)
    production_capacity = fields.CharField(max_length=45, null=True)
    approved_at = fields.DatetimeField(null=True)
    institution = fields.ForeignKeyField('models.Institution', related_name='combined_projects',
                                         on_delete=fields.RESTRICT, null=True)
    sector = fields.ForeignKeyField('models.Sector', related_name='combined_projects', on_delete=fields.RESTRICT,
                                    null=True)

    # Fields from Progress model
    ownership_type = fields.CharField(max_length=45)
    investment_capital = fields.FloatField()
    male_local_permanent_employment_number = fields.IntField(null=True)
    female_local_permanent_employment_number = fields.IntField(null=True)
    male_local_temporary_employment_number = fields.IntField(null=True)
    female_local_temporary_employment_number = fields.IntField(null=True)
    male_foreign_permanent_employment_number = fields.IntField(null=True)
    female_foreign_permanent_employment_number = fields.IntField(null=True)
    male_foreign_temporary_employment_number = fields.IntField(null=True)
    female_foreign_temporary_employment_number = fields.IntField(null=True)
    male_foreign_disabled_employment_number = fields.IntField(null=True)
    female_foreign_disabled_employment_number = fields.IntField(null=True)
    male_local_disabled_employment_number = fields.IntField(null=True)
    female_local_disabled_employment_number = fields.IntField(null=True)
    status = fields.CharField(max_length=45, null=True)
    production_source = fields.CharField(max_length=45, null=True)
    annual_sales = fields.FloatField(null=True)
    annual_export = fields.FloatField(null=True)
    street = fields.CharField(max_length=250)
    title_deed_type = fields.CharField(max_length=45, null=True)
    other_title_deed_type = fields.CharField(max_length=45, null=True)
    title_deed_date = fields.DateField(null=True)
    ward = fields.ForeignKeyField('models.Ward', related_name='projects', on_delete=fields.RESTRICT)
    evaluation_status = fields.CharField(max_length=45, default="DRAFT")
    last_progress_status = fields.CharField(max_length=45, null=True)
    physical_location = fields.CharField(max_length=50, null=True)
    number_of_progress = fields.IntField(default=0)

    created_by = fields.ForeignKeyField(
        "models.User",
        null=True,
        on_delete=fields.SET_NULL,
        related_name="projects_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "projects"
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return f"{self.name}"

    def resource_notification_message(self):
        return f"Registration/Progress of Project '{self.name}'"

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Region,
                'headship_type': HeadshipType.REGION,
                'column': 'ward_id',
                'path': 'districts__councils__wards',
            },
            {
                'model': District,
                'headship_type': HeadshipType.DISTRICT,
                'column': 'ward_id',
                'path': 'councils__wards'
            },
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'institution_id',
                'path': None
            },
            {
                'model': Company,
                'combine': 'OR',  # Combine with OR
                'headship_type': HeadshipType.COMPANY,
                'column': 'project_companies__company_id',
                'path': None,
                'filter_func': Q(project_companies__is_active=True),
            },
        ]


# Project Progress
class Progress(TimeStampedModel):
    # Fields from Project model
    name = fields.CharField(max_length=210)
    project_number = fields.CharField(max_length=45, null=True)
    registration_date = fields.DateField()
    commencement_date = fields.DateField()
    specific_activity = fields.CharField(max_length=1000)
    capital_source = fields.CharField(max_length=45, null=True)
    land_size = fields.CharField(max_length=45, null=True)
    production_capacity = fields.CharField(max_length=45, null=True)
    approved_at = fields.DatetimeField(null=True)
    institution = fields.ForeignKeyField('models.Institution', related_name='projects',
                                         on_delete=fields.RESTRICT, null=True)
    sector = fields.ForeignKeyField('models.Sector', related_name='projects', on_delete=fields.RESTRICT,
                                    null=True)

    # Fields from Progress model
    ownership_type = fields.CharField(max_length=45)
    investment_capital = fields.FloatField()
    male_local_permanent_employment_number = fields.IntField(null=True)
    female_local_permanent_employment_number = fields.IntField(null=True)
    male_local_temporary_employment_number = fields.IntField(null=True)
    female_local_temporary_employment_number = fields.IntField(null=True)
    male_foreign_permanent_employment_number = fields.IntField(null=True)
    female_foreign_permanent_employment_number = fields.IntField(null=True)
    male_foreign_temporary_employment_number = fields.IntField(null=True)
    female_foreign_temporary_employment_number = fields.IntField(null=True)
    male_foreign_disabled_employment_number = fields.IntField(null=True)
    female_foreign_disabled_employment_number = fields.IntField(null=True)
    male_local_disabled_employment_number = fields.IntField(null=True)
    female_local_disabled_employment_number = fields.IntField(null=True)
    status = fields.CharField(max_length=45,null=True)
    production_source = fields.CharField(max_length=45, null=True)
    annual_sales = fields.FloatField(null=True)
    annual_export = fields.FloatField(null=True)
    street = fields.CharField(max_length=250)
    title_deed_type = fields.CharField(max_length=45, null=True)
    other_title_deed_type = fields.CharField(max_length=45, null=True)
    title_deed_date = fields.DateField(null=True)
    ward = fields.ForeignKeyField('models.Ward', related_name='progress', on_delete=fields.RESTRICT)
    evaluation_status = fields.CharField(max_length=45, default="DRAFT")
    physical_location = fields.CharField(max_length=50, null=True)
    project = fields.ForeignKeyField('models.Project', related_name='progress', on_delete=fields.RESTRICT,
                                     null=True)

    class Meta:
        table = "progress"
        verbose_name = "Progress"
        verbose_name_plural = "Progresses"

    def __str__(self):
        return f"Progress on {self.created_at} for {self.project.name}"

    def resource_notification_message(self):
        return f"Progress of Project '{self.project.name}'"

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Region,
                'headship_type': HeadshipType.REGION,
                'column': 'ward_id',
                'path': 'districts__councils__wards'
            },
            {
                'model': District,
                'headship_type': HeadshipType.DISTRICT,
                'column': 'ward_id',
                'path': 'councils__wards'
            },
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'institution_id',
                'path': None
            },
            {
                'model': Company,
                'combine': 'OR',  # Combine with OR
                'headship_type': HeadshipType.COMPANY,
                'column': 'project_companies__company_id',
                'path': None,
                'filter_func': Q(project_companies__is_active=True),
            },
        ]


class ProgressExportCountry(TimeStampedModel):
    country = fields.ForeignKeyField('models.Country', related_name='export_countries', on_delete=fields.RESTRICT)
    progress = fields.ForeignKeyField('models.Progress', related_name='export_countries', on_delete=fields.RESTRICT)

    class Meta:
        table = "progress_export_country"
        verbose_name = "Progress Export Country"
        verbose_name_plural = "Progress Export Countries"
        unique_together = ("country", "progress")


# progress cooperate social
class ProgressCsr(TimeStampedModel):
    progress = fields.ForeignKeyField('models.Progress', related_name='csr_contributions', on_delete=fields.RESTRICT)
    cooperate_social = fields.ForeignKeyField('models.CooperateSocial', related_name='csr_contributions',
                                              on_delete=fields.RESTRICT)
    value = fields.FloatField(null=True)

    class Meta:
        table = "progress_csr"
        verbose_name = "Progress Csr"
        verbose_name_plural = "Progress Csrs"


class ProgressCapitalSource(TimeStampedModel):
    progress = fields.ForeignKeyField('models.Progress', related_name='progress_capital_sources',
                                      on_delete=fields.RESTRICT)
    capital_source = fields.CharField(max_length=45)
    value = fields.FloatField(null=True)

    class Meta:
        table = "progress_capital_source"
        verbose_name = "Progress Capital Source"
        verbose_name_plural = "Progress Capital Sources"


class Company(TimeStampedModel):
    name = fields.CharField(max_length=250)
    incorporation_number = fields.CharField(max_length=50, null=True)
    address = fields.CharField(max_length=200, null=True)
    email = fields.CharField(max_length=200, null=True)
    phone_number = fields.CharField(max_length=100, null=True)

    class Meta:
        table = "companies"
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


# Project Company
class ProjectCompany(TimeStampedModel):
    company = fields.ForeignKeyField('models.Company', related_name='project_companies',
                                     on_delete=fields.RESTRICT)
    project = fields.ForeignKeyField('models.Project', related_name='project_companies',
                                     on_delete=fields.RESTRICT)
    progress = fields.ForeignKeyField('models.Progress', related_name='project_companies',
                                      on_delete=fields.RESTRICT)
    # is true for company that own project currently
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "project_companies"
        verbose_name = "Project Company"
        verbose_name_plural = "Project Companies"

    def __str__(self):
        return f"Company {self.company} - Project {self.project}"


# company representative profile
class CompanyRepresentativeProfile(TimeStampedModel):
    company = fields.ForeignKeyField('models.Company', related_name='company_representatives',
                                     on_delete=fields.RESTRICT)
    user = fields.ForeignKeyField('models.User', related_name='company_representative_profiles',
                                  on_delete=fields.RESTRICT)

    class Meta:
        table = "company_representative_profiles"
        verbose_name = "Company Representative Profile"
        verbose_name_plural = "Company Representative Profiles"
        unique_together = ("company", "user")


# Shareholder
class Shareholder(TimeStampedModel):
    name = fields.CharField(max_length=45)
    value = fields.FloatField()
    is_active = fields.BooleanField(default=True)  # is true if currently own shares in the company
    country = fields.ForeignKeyField('models.Country', related_name='shareholders', on_delete=fields.RESTRICT)
    company = fields.ForeignKeyField('models.Company', related_name='shareholders',
                                     on_delete=fields.RESTRICT)

    class Meta:
        table = "shareholders"
        verbose_name = "Shareholder"
        verbose_name_plural = "Shareholders"

    def __str__(self):
        return self.name


# Share
class Share(TimeStampedModel):
    value = fields.FloatField()
    shareholder = fields.ForeignKeyField('models.Shareholder', related_name='shares',
                                         on_delete=fields.RESTRICT)
    progress = fields.ForeignKeyField('models.Progress', related_name='shares',
                                      on_delete=fields.RESTRICT)

    class Meta:
        table = "shares"
        verbose_name = "Share"
        verbose_name_plural = "Share"

    def __str__(self):
        return f"Share Value: {self.value}"


# Pagination Data will be inserted upon success receiving of data
class PaginationData(TimeStampedModel):
    institution = fields.ForeignKeyField('models.Institution', related_name='paginations',
                                         on_delete=fields.RESTRICT)
    retrieved_at = fields.DateField()
    page = fields.IntField()
    fetched_items = fields.IntField(default=0)
    limit = fields.IntField()
    api_code = fields.CharField(max_length=45)

    class Meta:
        table = "pagination_data"
        verbose_name = "Pagination Data"
        verbose_name_plural = "Pagination Data"

    def __str__(self):
        return f"Page {self.page} - Limit {self.limit}"


# Investment Opportunity
class InvestmentOpportunity(TimeStampedModel):
    street = fields.CharField(max_length=45)
    land_use = fields.CharField(max_length=250)
    land_size = fields.FloatField(null=True)
    land_unit = fields.CharField(max_length=45, null=True)
    ownership = fields.CharField(max_length=45)
    other_ownership = fields.CharField(max_length=100, null=True)
    type = fields.CharField(max_length=45)
    land_type = fields.CharField(max_length=45, null=True)
    investment_mode = fields.CharField(max_length=45)
    is_surveyed = fields.BooleanField()
    plot_number = fields.CharField(max_length=45, null=True)
    block_number = fields.CharField(max_length=45, null=True)
    status = fields.CharField(max_length=45)
    evaluation_status = fields.CharField(max_length=45, default="DRAFT")
    is_published = fields.BooleanField(default=False)
    description = fields.CharField(max_length=1000, null=True)
    ward = fields.ForeignKeyField('models.Ward', related_name='investment_opportunities', on_delete=fields.RESTRICT)
    sector = fields.ForeignKeyField('models.Sector', related_name='investment_opportunities', on_delete=fields.RESTRICT)
    institution = fields.ForeignKeyField('models.Institution', related_name='investment_opportunities',
                                         on_delete=fields.RESTRICT, null=True)

    created_by = fields.ForeignKeyField(
        "models.User",
        null=True,
        on_delete=fields.SET_NULL,
        related_name="investment_opportunities_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "investment_opportunities"
        verbose_name = "Investment Opportunity"
        verbose_name_plural = "Investment Opportunities"

    def __str__(self):
        return f"Investment at {self.street}"

    def resource_notification_message(self):
        return f"Registered Investment Opportunity at {self.street}"

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Region,
                'headship_type': HeadshipType.REGION,
                'column': 'ward_id',
                'path': 'districts__councils__wards'
            },
            {
                'model': District,
                'headship_type': HeadshipType.DISTRICT,
                'column': 'ward_id',
                'path': 'councils__wards'
            },
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'institution_id',
                'path': None
            },
        ]


# IO facility
class IOFacility(TimeStampedModel):
    name = fields.CharField(max_length=45)
    description = fields.CharField(max_length=100, null=True)
    io = fields.ForeignKeyField('models.InvestmentOpportunity', related_name='facilities',
                                on_delete=fields.RESTRICT)

    class Meta:
        table = "io_facilities"
        verbose_name = "IO Facility"
        verbose_name_plural = "IO Facilities"

    def __str__(self):
        return self.name


# IO Coordinate
class IOCoordinate(TimeStampedModel):
    longitude = fields.DecimalField(max_digits=25, decimal_places=16, null=False, help_text="Longitude of the point")
    latitude = fields.DecimalField(max_digits=25, decimal_places=16, null=False, help_text="Latitude of the point")
    io = fields.ForeignKeyField(
        'models.InvestmentOpportunity',
        related_name='coordinates',
        on_delete=fields.RESTRICT,
        help_text="Related investment opportunity"
    )

    class Meta:
        table = "io_coordinates"
        verbose_name = "IO Coordinate"
        verbose_name_plural = "IO Coordinates"

    def __str__(self):
        return f"Coordinate: ({self.latitude}, {self.longitude})"


# IO Property
class IOProperty(TimeStampedModel):
    name = fields.CharField(max_length=100, help_text="The name of the property, e.g., 'Size', 'Location', etc.")
    value = fields.TextField(null=True, help_text="The value of the property, e.g., '500 sqm', 'City Center', etc.")
    io = fields.ForeignKeyField(
        'models.InvestmentOpportunity',
        related_name='properties',
        on_delete=fields.RESTRICT,
        help_text="The investment opportunity to which this property belongs"
    )

    class Meta:
        table = "io_properties"
        verbose_name = "IO Property"
        verbose_name_plural = "IO Properties"

    def __str__(self):
        return f"{self.name}: {self.value}"


# Outward Investment
class OutwardInvestment(TimeStampedModel):
    company = fields.CharField(max_length=100)
    investment_capital = fields.FloatField()
    other_reason = fields.CharField(max_length=200, null=True)
    sector = fields.ForeignKeyField('models.Sector', related_name='outward_investments', on_delete=fields.RESTRICT)
    country = fields.ForeignKeyField('models.Country', related_name='outward_investments', on_delete=fields.RESTRICT)
    created_by = fields.ForeignKeyField(
        "models.User",
        null=True,
        on_delete=fields.SET_NULL,
        related_name="outward_investments_created"  # Specific related_name to avoid conflict
    )
    local_job_created = fields.IntField(null=True) # Tanzania
    foreign_job_created = fields.IntField(null=True) # Other
    status = fields.CharField(max_length=100, null=True)
    service_offered = fields.CharField(max_length=200, null=True)
    start_date = fields.DateField(null=True)



    class Meta:
        table = "outward_investments"
        verbose_name = "Outward Investment"
        verbose_name_plural = "Outward Investments"

    def __str__(self):
        return self.company


class OutwardInvestmentReasons(TimeStampedModel):
    outward_investment = fields.ForeignKeyField('models.OutwardInvestment', related_name='reasons',
                                                on_delete=fields.RESTRICT)
    reason = fields.CharField(max_length=200)

    class Meta:
        table = "outward_investment_reasons"
        verbose_name = "Outward Investment Reason"
        verbose_name_plural = "Outward Investment Reasons"


# Survey
class Survey(TimeStampedModel):
    name = fields.CharField(max_length=100)
    code = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)
    start_date = fields.CharField(max_length=200)
    end_date = fields.CharField(max_length=200)

    created_by = fields.ForeignKeyField(
        "models.User",
        null=True,
        on_delete=fields.SET_NULL,
        related_name="surveys_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "surveys"
        verbose_name = "Survey"
        verbose_name_plural = "Surveys"

    def __str__(self):
        return self.name

    async def save(self, *args, **kwargs):
        # Generate unique code if not set
        if not self.code:
            self.code = f"SURV-{uuid.uuid4().hex[:8].upper()}"  # Example format: SURV-XXXXXX
        await super().save(*args, **kwargs)


# Survey Data
class SurveyData(TimeStampedModel):
    batch = fields.ForeignKeyField('models.SurveyDataBatch', related_name='survey_datas', on_delete=fields.RESTRICT)
    name = fields.CharField(max_length=210, null=True)
    project_number = fields.CharField(max_length=45, null=True)
    registration_date = fields.DateField()
    commencement_date = fields.DateField()
    specific_activity = fields.CharField(max_length=1000)
    # capital_source = fields.CharField(max_length=45, null=True)
    land_size = fields.CharField(max_length=45, null=True)
    production_capacity = fields.CharField(max_length=45, null=True)
    approved_at = fields.DatetimeField(null=True)

    institution = fields.ForeignKeyField('models.Institution', related_name='survey_datas',
                                         on_delete=fields.RESTRICT, null=True)

    sector = fields.CharField(max_length=45)
    ownership_type = fields.CharField(max_length=45)
    investment_capital = fields.FloatField()
    male_local_permanent_employment_number = fields.IntField(null=True)
    female_local_permanent_employment_number = fields.IntField(null=True)
    male_local_temporary_employment_number = fields.IntField(null=True)
    female_local_temporary_employment_number = fields.IntField(null=True)
    male_foreign_permanent_employment_number = fields.IntField(null=True)
    female_foreign_permanent_employment_number = fields.IntField(null=True)
    male_foreign_temporary_employment_number = fields.IntField(null=True)
    female_foreign_temporary_employment_number = fields.IntField(null=True)
    male_foreign_disabled_employment_number = fields.IntField(null=True)
    female_foreign_disabled_employment_number = fields.IntField(null=True)
    male_local_disabled_employment_number = fields.IntField(null=True)
    female_local_disabled_employment_number = fields.IntField(null=True)
    status = fields.CharField(max_length=45)
    # said to be source of raw materials
    production_source = fields.CharField(max_length=45, null=True)
    annual_sales = fields.FloatField(null=True)
    annual_export = fields.FloatField(null=True)
    export_countries = fields.CharField(max_length=200, null=True)
    physical_location = fields.CharField(max_length=50, null=True)
    street = fields.CharField(max_length=45)
    title_deed_type = fields.CharField(max_length=45, null=True)
    title_deed_date = fields.DateField(max_length=45, null=True)
    ward = fields.CharField(max_length=50)
    # Company Data
    company_name = fields.CharField(max_length=250)
    incorporation_number = fields.CharField(max_length=45, null=True)
    company_address = fields.CharField(max_length=100, null=True)
    company_email = fields.CharField(max_length=100, null=True)
    company_phone_number = fields.CharField(max_length=100, null=True)
    # Shareholders values
    shareholders = fields.JSONField(null=True)
    csr_contributions = fields.JSONField(null=True)
    progress_capital_source = fields.JSONField(null=True)
    # Representative Data
    representative_email = fields.CharField(max_length=100)
    representative_phone_number = fields.CharField(max_length=100)
    representative_first_name = fields.CharField(max_length=50)
    representative_middle_name = fields.CharField(max_length=50, null=True)  # Optional
    representative_last_name = fields.CharField(max_length=50)
    representative_gender = fields.CharField(max_length=50, null=True)

    # Processing flags
    processing_status = fields.CharField(max_length=50, null=True)
    error_remark = fields.CharField(max_length=250, null=True)

    created_by = fields.ForeignKeyField(
        "models.User",
        null=True,
        on_delete=fields.SET_NULL,
        related_name="survey_datas_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "survey_data"
        verbose_name = "Survey Data"
        verbose_name_plural = "Survey Data"

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'institution_id',
                'path': None
            },
        ]


# Project Correlation
class ProjectCorrelation(TimeStampedModel):
    registration_project = fields.ForeignKeyField(
        'models.RegistrationProject', related_name='project_correlations', on_delete=fields.RESTRICT
    )
    standalone_project = fields.ForeignKeyField(
        'models.Project', related_name='project_correlations', on_delete=fields.RESTRICT
    )
    correlation = fields.FloatField(default=100.0)

    class Meta:
        table = "project_correlations"
        verbose_name = "Project Correlation"
        verbose_name_plural = "Project Correlations"

    def __str__(self):
        return f"Correlation: Registration Project {self.registration_project} - Standalone Project {self.standalone_project}"


#
class RegistrationProjectData(TimeStampedModel):
    batch = fields.ForeignKeyField('models.RegistrationProjectDataBatch', related_name='registration_project_data',
                                   on_delete=fields.RESTRICT)

    institution = fields.ForeignKeyField('models.Institution', related_name='registered_project_datas',
                                         on_delete=fields.RESTRICT, null=True)

    sector = fields.CharField(max_length=45)
    name = fields.CharField(max_length=200)
    project_number = fields.CharField(max_length=45)
    registration_date = fields.DateField()
    commencement_date = fields.DateField()
    specific_activity = fields.CharField(max_length=1000, null=True)
    # enum field with values in CapitalSource enum
    local_equity = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    local_loan = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    foreign_equity = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    foreign_loan = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    # enum field with values in ProductionSource enum
    production_source = fields.CharField(max_length=45, null=True)
    # enum field with values in OwnershipType enum
    ownership_type = fields.CharField(max_length=45, null=True)
    land_size = fields.CharField(max_length=45, null=True)
    investment_capital = fields.FloatField(null=True)
    total_local_employment = fields.IntField(default=0)
    total_foreign_employment = fields.IntField(default=0)
    male_local_employment = fields.IntField(default=0)
    female_local_employment = fields.IntField(default=0)
    male_foreign_employment = fields.IntField(default=0)
    female_foreign_employment = fields.IntField(default=0)
    production_capacity = fields.CharField(max_length=45, null=True)
    # enum field with values in ProjectStatus
    status = fields.CharField(max_length=45, null=True)
    region = fields.CharField(max_length=45)
    district = fields.CharField(max_length=45)
    ward = fields.CharField(max_length=45)
    # Company Data
    company_name = fields.CharField(max_length=250)
    incorporation_number = fields.CharField(max_length=45, null=True)
    company_address = fields.CharField(max_length=100, null=True)
    company_email = fields.CharField(max_length=100, null=True)
    company_phone_number = fields.CharField(max_length=100, null=True)

    # Shareholders
    shareholders = fields.JSONField(null=True)

    # Representative Data
    representative_email = fields.CharField(max_length=100)
    representative_first_name = fields.CharField(max_length=50)
    representative_middle_name = fields.CharField(max_length=50, null=True)  # Optional
    representative_last_name = fields.CharField(max_length=50)
    representative_phone_number = fields.CharField(max_length=50)
    representative_gender = fields.CharField(max_length=50, null=True)

    # Processing flags
    processing_status = fields.CharField(max_length=50, null=True)
    error_remark = fields.CharField(max_length=250, null=True)

    created_by = fields.ForeignKeyField(
        "models.User",
        null=True,
        on_delete=fields.SET_NULL,
        related_name="registration_project_datas_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "registration_project_data"
        verbose_name = "Registration Project Data"
        verbose_name_plural = "Registration Project Data"

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'institution_id',
                'path': None
            },
        ]


class SurveyDataBatch(TimeStampedModel):
    batch_number = fields.CharField(max_length=100, unique=True)
    file_name = fields.CharField(max_length=100)
    survey = fields.ForeignKeyField('models.Survey', related_name='batches', on_delete=fields.RESTRICT)


    class Meta:
        table = "survey_data_batch"
        verbose_name = "Survey Data Batch"
        verbose_name_plural = "Survey Data Batch"

    # async def save(self, *args, **kwargs):
    #     if not self.batch_number:  # Ensure the batch number is only generated once
    #         unique_suffix = str(uuid.uuid4())[:8].upper()  # Generate an 8-character unique suffix
    #         self.batch_number = f"SUV-{unique_suffix}"  # Create the formatted batch number
    #     await super().save(*args, **kwargs)

class RegistrationProjectDataBatch(TimeStampedModel):
    batch_number = fields.CharField(max_length=100, unique=True)
    file_name = fields.CharField(max_length=100)


    class Meta:
        table = "registration_project_data_batch"
        verbose_name = "Registration Project Data Batch"
        verbose_name_plural = "Registration Project Data Batch"

    # async def save(self, *args, **kwargs):
    #     if not self.batch_number:  # Ensure the batch number is only generated once
    #         unique_suffix = str(uuid.uuid4())[:8].upper()  # Generate an 8-character unique suffix
    #         self.batch_number = f"REP-{unique_suffix}"  # Create the formatted batch number
    #     await super().save(*args, **kwargs)
