from datetime import date
from typing import List, Type
from tortoise import Tortoise
from tortoise import fields
from tortoise.exceptions import ConfigurationError

from fast_api_builder.common.schemas import ModelType
from fast_api_builder.muarms.models import HeadshipModel
from fast_api_builder.muarms.models import Progress
from fast_api_builder.muarms.models.iop import ProgressCsr, Project, RegistrationProject, InvestmentOpportunity, \
    IOFacility, IOCoordinate, IOProperty, OutwardInvestment
from fast_api_builder.muarms.models.lookups import Council, Country, District, Region, Sector, Ward
from fast_api_builder.muarms.models.website import Enquiry
from fast_api_builder.utils.error_logging import log_exception, log_warning

class ReportView(HeadshipModel):
    """
    Base class for report views.
    Requires subclasses to define:
      - `query`: SQL query to create the report view.
      - `refresh_query`: SQL query to refresh the report view.
    Optionally, subclasses can define:
      - `dependencies`: List of models that the report view depends on.
    """
    
    class Meta:
        abstract = True  # Prevent Tortoise from treating this as a table

    @classmethod
    def get_query(cls) -> str:
        if not hasattr(cls.Meta, "query"):
            raise ConfigurationError(f"{cls.__name__} must define a 'query' in Meta.")
        return cls.Meta.query

    @classmethod
    def get_refresh_query(cls) -> str:
        if not hasattr(cls.Meta, "refresh_query"):
            raise ConfigurationError(f"{cls.__name__} must define a 'refresh_query' in Meta.")
        return cls.Meta.refresh_query

    @classmethod
    def get_dependencies(cls) -> list:
        return getattr(cls.Meta, "dependencies", [])
    
    
    @classmethod
    def get_report_name(cls, **args) -> str:
        """
        Generates a report name by replacing placeholders in the template with values from args.

        :param args: Dictionary of placeholders and their replacement values.
        :return: Formatted report name string.
        """
        # Get the template from Meta or use a default template
        template = getattr(cls.Meta, "report_name", "Report")
        
        # Format the template with the provided args
        try:
            return template.format(**args)
        except KeyError as e:
            raise ValueError(f"Missing placeholder value for {e} in args.") from e
        
    @classmethod
    def get_report_description(cls, **args) -> str:
        """
        Generates a report description by replacing placeholders in the template with values from args.

        :param args: Dictionary of placeholders and their replacement values.
        :return: Formatted report description string.
        """
        # Get the template from Meta or use a default template
        template = getattr(cls.Meta, "report_description", "Report")
        
        # Format the template with the provided args
        try:
            return template.format(**args)
        except KeyError as e:
            raise ValueError(f"Missing placeholder value for {e} in args.") from e
    
    @classmethod
    def has_dependants(cls, models: List[Type[ModelType]]) -> bool:
        try:
            for registered_model in Tortoise.apps["report_views"].values():
                if issubclass(registered_model, ReportView):
                    # Check dependencies for each registered model
                    dependencies = registered_model.get_dependencies()
                    if any(dep.__name__ == model.__name__ for dep in dependencies for model in models):
                        return True
        except Exception as e:
            log_exception(e)

        return False
                
    @classmethod
    def get_dependants(cls, models: List[Type[ModelType]]) -> List[Type["ReportView"]]:
        """
        Returns a list of models that depend on the current model.

        A dependent model is any model that lists the current model in its dependencies.
        """
        dependants = []
        try:
            for registered_model in Tortoise.apps["report_views"].values():
                if issubclass(registered_model, ReportView):
                    dependencies = registered_model.get_dependencies()
                    if any(dep.__name__ == model.__name__ for dep in dependencies for model in models):
                        dependants.append(registered_model)
        except Exception as e:
            log_exception(e)

        return dependants
    
    @classmethod
    async def create_view(cls):
        """Creates the report view."""
        query = cls.get_query()
        await cls._meta.db.execute_query(query)

    @classmethod
    async def refresh_view(cls):
        """Refreshes the report view."""
        refresh_query = cls.get_refresh_query()
        await cls._meta.db.execute_query(refresh_query)
        
    @classmethod
    async def check_dependencies(cls):
        """Check if all dependencies exist before creating the view."""
        dependencies = cls.get_dependencies()
        for model in dependencies:
            table = model.Meta.table
            query = f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = '{table}'
            );
            """
            result = await cls._meta.db.execute_query(query)
            if not result[0]:
                raise ConfigurationError(f"Dependency table {table} does not exist for {cls.__name__}.")
            
    @classmethod
    async def setup_views(cls):
        """
        Setup report views for all subclasses of ReportView.
        """
        for model in Tortoise.apps["report_views"].values():
            if issubclass(model, ReportView):
                try:
                    await model.check_dependencies()
                    await model.create_view()
                except ConfigurationError as e:
                    # Add more context to the error message and rethrow
                    raise ConfigurationError(
                        f"Error setting up report view {model.__name__}: {e}"
                    ) from e
        print("Report views generated successfully.")
                    
    @classmethod
    async def drop_views(cls, models: List[Type[ModelType]] = None):
        for model in Tortoise.apps["report_views"].values():
            if issubclass(model, ReportView):
                query = f"DROP MATERIALIZED VIEW IF EXISTS {model.Meta.table};"
                try:
                    await model._meta.db.execute_query(query)
                except:
                    log_exception(f"Failed to drop Materialized view '{model.Meta.table}'")

class ProjectsOwnership(ReportView):
    id = fields.IntField(pk=True) 
    region = fields.CharField(max_length=50)
    date = fields.CharField(max_length=10)
    local = fields.DecimalField(max_digits=10, decimal_places=2)
    foreign = fields.DecimalField(max_digits=10, decimal_places=2)
    joint_venture = fields.DecimalField(max_digits=10, decimal_places=2)
    total = fields.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        table = "projects_ownership"
        verbose_name = "Projects Ownership"  # Human-readable name for admin, etc.
        verbose_name_plural = "Projects Ownerships"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS projects_ownership AS
        SELECT 
            row_number() OVER (ORDER BY r.name) AS id,  -- Add a unique integer ID
            r.name AS region,  -- Select the region name

            TO_CHAR(p.created_at, 'YYYY-MM') AS date,

            SUM(CASE WHEN p.ownership_type ILIKE '%Local%' THEN 1 ELSE 0 END) AS local,
            SUM(CASE WHEN p.ownership_type ILIKE '%Foreign%' THEN 1 ELSE 0 END) AS foreign,
            SUM(CASE WHEN p.ownership_type ILIKE '%Joint Venture%' THEN 1 ELSE 0 END) AS joint_venture,

            SUM(CASE WHEN p.ownership_type ILIKE '%Local%' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN p.ownership_type ILIKE '%Foreign%' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN p.ownership_type ILIKE '%Joint Venture%' THEN 1 ELSE 0 END) AS total
            
        FROM 
            public.progress p
        JOIN 
            public.wards w ON p.ward_id = w.id
        JOIN 
            public.councils c ON w.council_id = c.id
        JOIN 
            public.districts d ON c.district_id = d.id
        JOIN 
            public.regions r ON d.region_id = r.id  -- Join with the region table
        WHERE
            p.evaluation_status = 'APPROVED'
        GROUP BY 
            r.name, date
        ORDER BY 
            r.name, date;
        """
        app = 'report_views'
        refresh_query = "REFRESH MATERIALIZED VIEW projects_ownership;"
        dependencies = [Progress, Ward, Council, District, Region]
        report_name = "Projects' Ownership Report"
        report_description = None
        managed = False  # Prevent Tortoise from managing this table

class ProjectsCommencementBySector(ReportView):
    id = fields.IntField(pk=True)
    sector = fields.CharField(max_length=200)  # Adjusted to hold both sector name and code
    commencement_year_month = fields.CharField(max_length=15)
    commenced_count = fields.IntField()

    class Meta:
        table = "projects_commencement_by_sector"
        verbose_name = "Projects Commencement Sector"
        verbose_name_plural = "Projects Commencement Sectors"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS projects_commencement_by_sector AS
        SELECT 
            row_number() OVER (ORDER BY s.name) AS id,
            CONCAT(s.name, ' (', s.code, ')') AS sector, 
            TO_CHAR(p.commencement_date, 'YYYY-MM') AS commencement_year_month,
            COUNT(CASE WHEN p.commencement_date IS NOT NULL THEN 1 END) AS commenced_count
        FROM 
            public.progress p
        JOIN 
            public.sectors s ON p.sector_id = s.id
        WHERE
            p.evaluation_status = 'APPROVED'
        GROUP BY 
            s.name, s.code, commencement_year_month
        ORDER BY 
            s.name, commencement_year_month;
        """
        app = 'report_views'
        refresh_query = "REFRESH MATERIALIZED VIEW projects_commencement_by_sector;"
        dependencies = [Progress, Sector]
        report_name = "Project Commencement Report"
        report_description = "Commenced Projects for each sector"
        managed = False 
        
class VerifiedVsRegisteredProjects(ReportView):
    id = fields.IntField(pk=True)
    sector = fields.CharField(max_length=200)  # For both sector name and code
    date = fields.CharField(max_length=10)
    total_registered_projects = fields.IntField()
    total_verified_projects = fields.IntField()
    total_registered_investment = fields.DecimalField(max_digits=15, decimal_places=2)
    total_verified_investment = fields.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        table = "verified_vs_registered_projects"
        verbose_name = "Comparison of Verified vs Registered Projects"
        verbose_name_plural = "Comparisons of Verified vs Registered Projects"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS verified_vs_registered_projects AS
        WITH registered_projects AS (
            SELECT 
                rp.sector_id,
                TO_CHAR(rp.created_at, 'YYYY-MM') AS date,
                COUNT(DISTINCT rp.id) AS total_registered_projects,
                COALESCE(SUM(rp.investment_capital), 0) AS total_registered_investment
            FROM 
                public.registration_projects rp
            GROUP BY 
                rp.sector_id, date
        ),
        verified_projects AS (
            SELECT 
                p.sector_id,
                TO_CHAR(p.created_at, 'YYYY-MM') AS date,
                COUNT(DISTINCT p.id) AS total_verified_projects,
                COALESCE(SUM(CASE 
                                WHEN p.evaluation_status = 'APPROVED' AND p.project_number IS NOT NULL 
                                THEN p.investment_capital 
                            END), 0) AS total_verified_investment
            FROM 
                public.projects p
            WHERE 
                p.evaluation_status = 'APPROVED' AND p.project_number IS NOT NULL
            GROUP BY 
                p.sector_id, date
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY s.name, COALESCE(rp.date, vp.date)) AS id,
            CONCAT(s.name, ' (', s.code, ')') AS sector,
            COALESCE(rp.date, vp.date) AS date,
            COALESCE(rp.total_registered_projects, 0) AS total_registered_projects,
            COALESCE(vp.total_verified_projects, 0) AS total_verified_projects,
            COALESCE(rp.total_registered_investment, 0.00) AS total_registered_investment,
            COALESCE(vp.total_verified_investment, 0.00) AS total_verified_investment
        FROM 
            public.sectors s
        LEFT JOIN 
            registered_projects rp ON rp.sector_id = s.id
        LEFT JOIN 
            verified_projects vp ON vp.sector_id = s.id AND rp.date = vp.date
        WHERE
            rp.date IS NOT NULL
        ORDER BY 
            s.name, date;
        """
        app = 'report_views'
        refresh_query = "REFRESH MATERIALIZED VIEW verified_vs_registered_projects;"
        dependencies = [RegistrationProject, Project, Sector]
        report_name = "Verified vs Registered"
        report_description = (
            "Comparison of verified projects against registered projects by sector."
        )
        managed = False
        
class EmploymentByRegion(ReportView):
    id = fields.IntField(pk=True)
    region = fields.CharField(max_length=200)
    district = fields.CharField(max_length=200)
    date = fields.CharField(max_length=10)
    total_projects = fields.IntField()
    permanent_male = fields.IntField()
    permanent_female = fields.IntField()
    temporary_male = fields.IntField()
    temporary_female = fields.IntField()
    total_permanent = fields.IntField()
    total_temporary = fields.IntField()
    total_employment = fields.IntField()

    class Meta:
        table = "employment_by_region"
        verbose_name = "Employment by Region"
        verbose_name_plural = "Employment by Region"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS employment_by_region AS
        SELECT 
            ROW_NUMBER() OVER (ORDER BY r.name, d.name) AS id,
            r.name AS region,
            d.name AS district,
            TO_CHAR(p.created_at, 'YYYY-MM') AS date,
            COUNT(p.id) AS total_projects,
            COALESCE(SUM(p.male_local_permanent_employment_number), 0) AS permanent_male,
            COALESCE(SUM(p.female_local_permanent_employment_number), 0) AS permanent_female,
            COALESCE(SUM(p.male_local_temporary_employment_number), 0) AS temporary_male,
            COALESCE(SUM(p.female_local_temporary_employment_number), 0) AS temporary_female,
            COALESCE(SUM(p.male_local_permanent_employment_number + p.female_local_permanent_employment_number), 0) AS total_permanent,
            COALESCE(SUM(p.male_local_temporary_employment_number + p.female_local_temporary_employment_number), 0) AS total_temporary,
            COALESCE(SUM(
                p.male_local_permanent_employment_number +
                p.female_local_permanent_employment_number +
                p.male_local_temporary_employment_number +
                p.female_local_temporary_employment_number
            ), 0) AS total_employment
        FROM 
            public.progress p
        LEFT JOIN 
            public.wards w ON p.ward_id = w.id
        LEFT JOIN 
            public.councils c ON w.council_id = c.id
        LEFT JOIN 
            public.districts d ON c.district_id = d.id
        LEFT JOIN 
            public.regions r ON d.region_id = r.id
        WHERE
            p.evaluation_status = 'APPROVED'
        GROUP BY 
            r.name, d.name, date
        ORDER BY 
            r.name, d.name, date;
        """
        app = "report_views"
        refresh_query = "REFRESH MATERIALIZED VIEW employment_by_region;"
        dependencies = [Progress, Ward, District, Region]
        report_name = "Employment by Region"
        report_description = "Aggregates employment data by region and district yearly."
        managed = False
        
class CSRByRegion():
    id = fields.IntField(pk=True)
    region = fields.CharField(max_length=200)
    district = fields.CharField(max_length=200)
    year = fields.CharField(max_length=200)
    total_projects = fields.IntField()
    education_services = fields.FloatField()
    health_services = fields.FloatField()
    water_services = fields.FloatField()
    physical_services = fields.FloatField()
    infrastructures_services = fields.FloatField()
    religious_services = fields.FloatField()
    others = fields.FloatField()
    total_value = fields.FloatField()

    class Meta:
        table = "csr_by_region"
        verbose_name = "CSR By Region"
        verbose_name_plural = "CSR By Region"
        managed = False
        app = "report_views"
        # query = """
        # CREATE MATERIALIZED VIEW IF NOT EXISTS csr_by_region AS
        # SELECT
        #     ROW_NUMBER() OVER (ORDER BY r.name, d.name) AS id,
        #     r.name AS region,
        #     d.name AS district,
        #     EXTRACT(YEAR FROM p.approved_at) AS year,
        #     COUNT(DISTINCT p.id) AS total_projects,
        #     COALESCE(SUM(CASE WHEN pc.cooperate_social = 'Education Services' THEN pc.value ELSE 0 END), 0) AS education_services,
        #     COALESCE(SUM(CASE WHEN pc.cooperate_social = 'Health Services' THEN pc.value ELSE 0 END), 0) AS health_services,
        #     COALESCE(SUM(CASE WHEN pc.cooperate_social = 'Water Services' THEN pc.value ELSE 0 END), 0) AS water_services,
        #     COALESCE(SUM(CASE WHEN pc.cooperate_social = 'Physical Infrastructures' THEN pc.value ELSE 0 END), 0) AS physical_infrastructures,
        #     COALESCE(SUM(CASE WHEN pc.cooperate_social = 'Religious Services' THEN pc.value ELSE 0 END), 0) AS religious_services,
        #     COALESCE(SUM(CASE 
        #                 WHEN pc.cooperate_social NOT IN ('Education Services', 'Health Services', 'Water Services', 
        #                                     'Physical Infrastructures', 'Religious Services') 
        #                 THEN pc.value 
        #                 ELSE 0 END), 0) AS others,
        #     COALESCE(SUM(pc.value), 0) AS total_value
        # FROM
        #     public.progress_csr pc
        # LEFT JOIN
        #     public.progress p ON pc.progress_id = p.id
        # LEFT JOIN
        #     public.wards w ON p.ward_id = w.id
        # LEFT JOIN
        #     public.councils c ON w.council_id = c.id
        # LEFT JOIN
        #     public.districts d ON c.district_id = d.id
        # LEFT JOIN
        #     public.regions r ON d.region_id = r.id
        # GROUP BY
        #     r.name, d.name, year
        # ORDER BY
        #     r.name, d.name, year;
        # """
        # refresh_query = "REFRESH MATERIALIZED VIEW csr_by_region;"
        # dependencies = [Progress, Ward, District, Region, ProgressCsr]
        # report_name = "Community Social Responsibility Report"
        # report_description = "Aggregates the monetary value of investments segmented by various CSR across regions and districts."
        
class ProjectsShares(ReportView):
    id = fields.IntField(pk=True) 
    sector = fields.CharField(max_length=100)
    date = fields.CharField(max_length=10)
    projects = fields.IntField()
    local = fields.DecimalField(max_digits=10, decimal_places=2)
    foreign = fields.DecimalField(max_digits=10, decimal_places=2)
    total = fields.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        table = "projects_shares"
        verbose_name = "Projects Shares"  # Human-readable name for admin, etc.
        verbose_name_plural = "Projects Shares"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS projects_shares AS
        WITH project_data AS (
            -- Select distinct projects and their related data
            SELECT
                DISTINCT p.id AS project_id,
                s.name AS sector,
                TO_CHAR(p.created_at, 'YYYY-MM') AS date,
                co.code AS country_code,
                sh.value AS shareholder_value
            FROM 
                public.progress p
            JOIN 
                public.sectors s ON p.sector_id = s.id
            JOIN
                public.project_companies pc ON pc.progress_id = p.id
            JOIN
                public.companies c ON pc.company_id = c.id
            JOIN 
                public.shareholders sh ON c.id = sh.company_id
            JOIN
                public.countries co ON sh.country_id = co.id
            WHERE
                p.evaluation_status = 'APPROVED'
                AND pc.is_active = true 
                AND sh.is_active = true
        ),
        aggregated_data AS (
            -- Aggregate the data for local and foreign sums
            SELECT
                sector,
                date,
                COUNT(DISTINCT project_id) AS projects,
                SUM(CASE WHEN country_code = 'TZ' THEN shareholder_value ELSE 0 END) AS local_sum,
                SUM(CASE WHEN country_code <> 'TZ' THEN shareholder_value ELSE 0 END) AS foreign_sum
            FROM 
                project_data
            GROUP BY 
                sector, date
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY sector, date) AS id,
            sector,
            date,
            projects,
            ROUND(CAST(local_sum AS NUMERIC) / NULLIF(projects, 0), 2) AS local,
            ROUND(CAST(foreign_sum AS NUMERIC) / NULLIF(projects, 0), 2) AS foreign,
            ROUND(CAST(local_sum + foreign_sum AS NUMERIC) / NULLIF(projects, 0), 2) AS total
        FROM 
            aggregated_data
        ORDER BY 
            sector, date;
        """
        app = 'report_views'
        refresh_query = "REFRESH MATERIALIZED VIEW projects_ownership;"
        dependencies = [Progress, Ward, Council, District, Region]
        report_name = "Origin of Shares Sectorwise"
        report_description = "A report outlining projects categorized by economic activities (sectors) and the origin of the shareholders."
        managed = False  # Prevent Tortoise from managing this table
        
class ProjectsStatus(ReportView):
    id = fields.IntField(pk=True)
    region = fields.CharField(max_length=200)  # Region name
    district = fields.CharField(max_length=200)  # District name
    date = fields.CharField(max_length=10)  # Year of the project
    new_projects = fields.IntField()  # Count of new projects
    expansion_projects = fields.IntField()  # Count of expansion projects
    rehabilitation_projects = fields.IntField()  # Count of rehabilitation projects
    total_projects = fields.IntField()  # Total count of all projects

    class Meta:
        table = "projects_status"
        verbose_name = "Projects Status"
        verbose_name_plural = "Projects Status"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS projects_status AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY r.name, d.name) AS id,
            r.name AS region,
            d.name AS district,
            TO_CHAR(p.created_at, 'YYYY-MM') AS date,
            SUM(CASE WHEN p.status = 'New Project' THEN 1 ELSE 0 END) AS new_projects,
            SUM(CASE WHEN p.status = 'Expansion' THEN 1 ELSE 0 END) AS expansion_projects,
            SUM(CASE WHEN p.status = 'Rehabilitation' THEN 1 ELSE 0 END) AS rehabilitation_projects,
            
            SUM(CASE WHEN p.status = 'New Project' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN p.status = 'Expansion' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN p.status = 'Rehabilitation' THEN 1 ELSE 0 END) AS total_projects
        FROM
            public.progress p
        LEFT JOIN
            public.wards w ON p.ward_id = w.id
        LEFT JOIN
            public.councils c ON w.council_id = c.id
        LEFT JOIN
            public.districts d ON c.district_id = d.id
        LEFT JOIN
            public.regions r ON d.region_id = r.id
        WHERE 
            p.status IN ('New Project', 'Expansion', 'Rehabilitation') AND p.evaluation_status = 'APPROVED'
        GROUP BY
            r.name, d.name, date
        ORDER BY
            r.name, d.name, date;
        """
        app = 'report_views'  # Replace with the appropriate app name
        refresh_query = "REFRESH MATERIALIZED VIEW projects_status;"
        dependencies = [Progress, District, Region]
        report_name = "Projects Status Report"
        report_description = "Report showing counts of new, expansion, and rehabilitation projects"
        managed = False  # Prevents Tortoise ORM from managing this as a standard table   
        
class ProjectsAnnualSalesByLocation(ReportView):
    id = fields.IntField(pk=True)
    region = fields.CharField(max_length=200)  # Region name
    year = fields.IntField()  # Year of the report
    rural_count = fields.IntField()  # Count of projects in rural areas
    urban_count = fields.IntField()  # Count of projects in urban areas
    total_projects = fields.IntField()  # Total number of projects
    annual_sales = fields.FloatField()  # Total annual sales in USD

    class Meta:
        table = "projects_annual_sales_by_location"
        verbose_name = "Projects Annual Sales By Location"
        verbose_name_plural = "Projects Annual Sales By Locations"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS projects_annual_sales_by_location AS
        SELECT 
            ROW_NUMBER() OVER (ORDER BY r.name) AS id,
            r.name AS region,
            EXTRACT(YEAR FROM p.created_at) AS year,
            COUNT(*) FILTER (WHERE p.physical_location = 'Rural') AS rural_count,
            COUNT(*) FILTER (WHERE p.physical_location = 'Urban') AS urban_count,
            COUNT(*) AS total_projects,
            COALESCE(SUM(p.annual_sales), 0) AS annual_sales
        FROM 
            public.progress p
        LEFT JOIN
            public.wards w ON p.ward_id = w.id
        LEFT JOIN
            public.councils c ON w.council_id = c.id
        LEFT JOIN
            public.districts d ON c.district_id = d.id
        LEFT JOIN
            public.regions r ON d.region_id = r.id
        WHERE 
            p.physical_location IN ('Rural', 'Urban') AND p.evaluation_status = 'APPROVED'
        GROUP BY 
            r.name, year
        ORDER BY 
            r.name, year;
        """
        app = 'report_views'  # Replace with the appropriate app name
        refresh_query = "REFRESH MATERIALIZED VIEW projects_annual_sales_by_location;"
        dependencies = [Progress, Region]
        report_name = "Projects Annual Sales"
        report_description = "Report showing investments projects by region, physical location, and annual sales"
        managed = False 

class ProjectsExport(ReportView):
    id = fields.IntField(pk=True)
    project_name = fields.CharField(max_length=200)
    date = fields.CharField(max_length=10)
    export_countries = fields.CharField(max_length=1000)
    export_value = fields.FloatField() 

    class Meta:
        table = "projects_exports"
        verbose_name = "Projects Export"
        verbose_name_plural = "Projects Exports"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS projects_exports AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY p.name) AS id,
            p.name AS project_name,
            TO_CHAR(p.created_at, 'YYYY-MM') AS date,
            STRING_AGG(DISTINCT c.name, ', ') AS export_countries,
            COALESCE(SUM(p.annual_export), 0) AS export_value
        FROM
            public.progress_export_country pec
        JOIN 
            public.progress p ON pec.progress_id = p.id
        JOIN 
            public.countries c ON pec.country_id = c.id
        WHERE 
            p.annual_export IS NOT NULL
        GROUP BY
            p.name, date
        ORDER BY
            p.name, date;
        """
        app = 'report_views'  # Replace with the appropriate app name
        refresh_query = "REFRESH MATERIALIZED VIEW projects_exports;"
        dependencies = [Progress, Country]
        report_name = "Projects Exports Report"
        report_description = "Report showing investments projects by region, physical location, and annual sales"
        managed = False 

class ComplaintsReport(ReportView):
    id = fields.IntField(pk=True)
    complainant = fields.CharField(max_length=200)  # Name or identifier of the complainant
    project_name = fields.CharField(max_length=200)  # Project name linked to the complaint
    submission_date = fields.DateField()  # Date of complaint application
    complaint_type = fields.CharField(max_length=100)  # Type of complaint
    status = fields.CharField(max_length=100)  # Complaint status
    current_stage = fields.TextField()  # Current stage of the complaint
    # days_since_submission = fields.IntField()  # Number of days since the complaint was filed

    @property
    def days_since_submission(self) -> int:
        """
        Calculate the number of days from created_at to today.
        """
        if self.submission_date:
            return (date.today() - self.submission_date).days
        return 0

    class Meta:
        table = "complaints_report"
        verbose_name = "Complaints Report"
        verbose_name_plural = "Complaints Reports"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS complaints_report AS
        WITH latest_feedback AS (
            SELECT
                f.enquiry_id,
                f.action,
                f.action_date AS feedback_date
            FROM
                public.feedbacks f
            INNER JOIN (
                SELECT
                    enquiry_id,
                    MAX(created_at) AS latest_feedback_date
                FROM
                    public.feedbacks
                GROUP BY
                    enquiry_id
            ) lf ON f.enquiry_id = lf.enquiry_id AND f.created_at = lf.latest_feedback_date
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY e.submitted_at) AS id,
            p.name AS project_name,
            CONCAT(u.first_name, ' ', u.last_name) AS complainant,
            e.enquiry_type AS complaint_type,
            e.submitted_at::DATE AS submission_date,
            e.status AS status,
            lf.action AS current_stage
        FROM
            public.enquiries e
        LEFT JOIN
            public.users u ON e.user_id = u.id
        LEFT JOIN
            public.projects p ON e.project_id = p.id
        LEFT JOIN
            latest_feedback lf ON e.id = lf.enquiry_id
        ORDER BY
            e.submitted_at;
        """
        app = 'report_views'  # Replace with the appropriate app name
        refresh_query = "REFRESH MATERIALIZED VIEW complaints_report;"
        dependencies = [Enquiry]
        report_name = "Complaints Report"
        report_description = "Detailed report of complaints with filters for status, type, and date range."
        managed = False


class InvestmentOpportunityAnalytics(ReportView):
    id = fields.IntField(pk=True)
    sector = fields.CharField(max_length=200)

    # Core Counts
    total_investment_opportunities = fields.IntField()
    surveyed_opportunities = fields.IntField()
    total_land_size = fields.DecimalField(max_digits=15, decimal_places=2)
    average_land_size = fields.DecimalField(max_digits=15, decimal_places=2)

    # Evaluation Status Counts
    draft_opportunities = fields.IntField()
    submitted_opportunities = fields.IntField()
    verified_opportunities = fields.IntField()
    revoked_opportunities = fields.IntField()
    approved_opportunities = fields.IntField()
    published_opportunities = fields.IntField()

    # Ownership Type Counts
    public_ownership = fields.IntField()
    private_local_ownership = fields.IntField()
    private_foreign_ownership = fields.IntField()
    private_joint_venture = fields.IntField()
    ppp_ownership = fields.IntField()

    # Investment Modes
    lease_opportunities = fields.IntField()
    joint_venture_opportunities = fields.IntField()
    sales_opportunities = fields.IntField()

    # Land Types
    village_land_opportunities = fields.IntField()
    general_land_opportunities = fields.IntField()

    # Additional Metrics
    total_facilities = fields.IntField()
    unique_coordinates = fields.IntField()
    total_properties = fields.IntField()
    average_properties_per_opportunity = fields.DecimalField(max_digits=5, decimal_places=2)

    # Investment Opportunity Status Counts
    available_opportunities = fields.IntField()
    not_available_opportunities = fields.IntField()

    # IO Types
    property_opportunities = fields.IntField()
    land_opportunities = fields.IntField()

    class Meta:
        app = 'report_views'
        table = "investment_opportunity_analytics"
        verbose_name = "Investment Opportunity Analytic"
        verbose_name_plural = "Investment Opportunity Analytics"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS investment_opportunity_analytics AS
        WITH BaseIO AS (
            SELECT 
                io.id, 
                io.is_surveyed, 
                io.land_size, 
                io.evaluation_status, 
                io.is_published, 
                io.ownership, 
                io.investment_mode, 
                io.land_type, 
                io.status, 
                io.type
            FROM public.investment_opportunities io
        ),
        Facilities AS (
            SELECT DISTINCT io_id FROM public.io_facilities
        ),
        Coordinates AS (
            SELECT DISTINCT io_id FROM public.io_coordinates
        ),
        Properties AS (
            SELECT DISTINCT io_id FROM public.io_properties
        )
        SELECT 
            1 AS id,  
            'All Sectors' AS sector,


            -- Evaluation Status Counts
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'DRAFT' THEN b.id END) AS draft_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'SUBMITTED' THEN b.id END) AS submitted_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'VERIFIED' THEN b.id END) AS verified_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'REVOKED' THEN b.id END) AS revoked_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' THEN b.id END) AS approved_opportunities,
            COUNT(DISTINCT CASE WHEN b.is_published THEN b.id END) AS published_opportunities,

            -- Core Counts (Only for APPROVED opportunities)
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' THEN b.id END) AS total_investment_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.is_surveyed THEN b.id END) AS surveyed_opportunities,
            COALESCE(ROUND(SUM(CASE WHEN b.evaluation_status = 'APPROVED' THEN b.land_size ELSE NULL END)::numeric, 2), 0.00) AS total_land_size,
            COALESCE(ROUND(AVG(CASE WHEN b.evaluation_status = 'APPROVED' THEN b.land_size ELSE NULL END)::numeric, 2), 0.00) AS average_land_size,

            -- Ownership Type Counts (Only for APPROVED opportunities)
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.ownership = 'Public - Public Investment' THEN b.id END) AS public_ownership,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.ownership = 'Private (Local)' THEN b.id END) AS private_local_ownership,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.ownership = 'Private (Foreign)' THEN b.id END) AS private_foreign_ownership,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.ownership = 'Private (Joint Venture)' THEN b.id END) AS private_joint_venture,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.ownership = 'PPP' THEN b.id END) AS ppp_ownership,

            -- Investment Modes (Only for APPROVED opportunities)
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.investment_mode = 'Lease' THEN b.id END) AS lease_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.investment_mode = 'Joint Venture' THEN b.id END) AS joint_venture_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.investment_mode = 'Sales/Disposal' THEN b.id END) AS sales_opportunities,

            -- Land Types (Only for APPROVED opportunities)
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.land_type = 'Village' THEN b.id END) AS village_land_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.land_type = 'General' THEN b.id END) AS general_land_opportunities,

            -- Additional Metrics (Only for APPROVED opportunities)
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' THEN f.io_id END) AS total_facilities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' THEN c.io_id END) AS unique_coordinates,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' THEN p.io_id END) AS total_properties,
            COALESCE(
                ROUND(
                    NULLIF(COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' THEN p.io_id END), 0)::numeric /
                    NULLIF(COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' THEN b.id END), 0), 
                    2
                ), 
                0.00
            ) AS average_properties_per_opportunity,

            -- Investment Opportunity Status Counts (Only for APPROVED opportunities)
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.status = 'Available' THEN b.id END) AS available_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.status = 'Not Available' THEN b.id END) AS not_available_opportunities,

            -- IO Types (Only for APPROVED opportunities)
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.type = 'Other Investment Opportunity' THEN b.id END) AS property_opportunities,
            COUNT(DISTINCT CASE WHEN b.evaluation_status = 'APPROVED' AND b.type = 'Land' THEN b.id END) AS land_opportunities

            FROM 
                BaseIO b
            LEFT JOIN Facilities f ON f.io_id = b.id
            LEFT JOIN Coordinates c ON c.io_id = b.id
            LEFT JOIN Properties p ON p.io_id = b.id;
        """
        refresh_query = "REFRESH MATERIALIZED VIEW investment_opportunity_analytics;"
        dependencies = [InvestmentOpportunity, Sector, IOFacility, IOCoordinate, IOProperty]
        report_name = "Investment Opportunity Analytics"
        report_description = "Detailed analytics for investment opportunities, including facilities, properties, coordinates, and opportunity types."
        managed = False


class OutwardInvestmentAnalytics(ReportView):
    id = fields.IntField(pk=True)
    sector = fields.CharField(max_length=200)
    country = fields.CharField(max_length=100)

    # Core Metrics
    total_investments = fields.IntField()
    total_investment_capital = fields.DecimalField(max_digits=15, decimal_places=2)
    average_investment_capital = fields.DecimalField(max_digits=15, decimal_places=2)

    # Top Companies and Sectors
    top_company_by_capital = fields.CharField(max_length=100, null=True)
    highest_investment_capital = fields.DecimalField(max_digits=15, decimal_places=2, null=True)

    # Regional Analysis
    investments_in_africa = fields.IntField()
    investments_in_asia = fields.IntField()
    investments_in_europe = fields.IntField()
    investments_in_south_americas = fields.IntField()
    investments_in_north_americas = fields.IntField()
    investments_in_oceania = fields.IntField()

    class Meta:
        app = 'report_views'
        table = "outward_investment_analytics"
        verbose_name = "Outward Investment Analytic"
        verbose_name_plural = "Outward Investment Analytics"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS outward_investment_analytics AS
        SELECT 
            1 AS id,  -- Single analytic entry, hence '1'
            'All Sectors' AS sector,  -- Global sector label
            'All Countries' AS country,  -- Global country label
            COUNT(oi.id) AS total_investments,
            COALESCE(ROUND(SUM(oi.investment_capital)::numeric, 2), 0.00) AS total_investment_capital,
            COALESCE(ROUND(AVG(oi.investment_capital)::numeric, 2), 0.00) AS average_investment_capital,

            -- Top Company by Capital (Global)
            (
                SELECT oi.company
                FROM outward_investments oi
                ORDER BY oi.investment_capital DESC
                LIMIT 1
            ) AS top_company_by_capital,

            -- Highest Investment Capital (Global)
            (
                SELECT MAX(oi.investment_capital)
                FROM outward_investments oi
            ) AS highest_investment_capital,

            -- Regional Analysis (Global)
            COUNT(CASE WHEN cn.continent = 'Africa' THEN 1 ELSE NULL END) AS investments_in_africa,
            COUNT(CASE WHEN cn.continent = 'Asia' THEN 1 ELSE NULL END) AS investments_in_asia,
            COUNT(CASE WHEN cn.continent = 'Europe' THEN 1 ELSE NULL END) AS investments_in_europe,
            COUNT(CASE WHEN cn.continent = 'South America' THEN 1 ELSE NULL END) AS investments_in_south_americas,
            COUNT(CASE WHEN cn.continent = 'North America' THEN 1 ELSE NULL END) AS investments_in_north_americas,
            COUNT(CASE WHEN cn.continent = 'Oceania' THEN 1 ELSE NULL END) AS investments_in_oceania

        FROM 
            public.outward_investments oi
        JOIN 
            public.countries c ON oi.country_id = c.id
        JOIN 
            public.countries cn ON oi.country_id = cn.id;
        """
        refresh_query = "REFRESH MATERIALIZED VIEW outward_investment_analytics;"
        dependencies = [OutwardInvestment, Country]
        report_name = "Outward Investment Analytics"
        report_description = "Detailed analytics on outward investments, including regional distributions, top sectors, and companies."
        managed = False


class ProjectAnalytics(ReportView):
    id = fields.IntField(pk=True)
    sector = fields.CharField(max_length=200)
    total_projects = fields.IntField()
    total_investment_capital = fields.DecimalField(max_digits=15, decimal_places=2)
    average_investment_capital = fields.DecimalField(max_digits=15, decimal_places=2)

    # Evaluation Statuses
    draft_projects = fields.IntField()
    approved_projects = fields.IntField()
    verified_projects = fields.IntField()
    revoked_projects = fields.IntField()
    submitted_projects = fields.IntField()

    # Employment Metrics
    male_local_permanent_employment_number = fields.IntField(null=True)
    female_local_permanent_employment_number = fields.IntField(null=True)
    male_local_temporary_employment_number = fields.IntField(null=True)
    female_local_temporary_employment_number = fields.IntField(null=True)

    male_foreign_permanent_employment_number = fields.IntField(null=True)
    female_foreign_permanent_employment_number = fields.IntField(null=True)
    male_foreign_temporary_employment_number = fields.IntField(null=True)
    female_foreign_temporary_employment_number = fields.IntField(null=True)

    male_local_disabled_employment_number = fields.IntField(null=True)
    female_local_disabled_employment_number = fields.IntField(null=True)
    male_foreign_disabled_employment_number = fields.IntField(null=True)
    female_foreign_disabled_employment_number = fields.IntField(null=True)

    total_employment = fields.IntField()  # Total Employment Count

    # Capital Source Data
    total_capital_loan_local = fields.DecimalField(max_digits=15, decimal_places=2, null=True)
    total_capital_loan_foreign = fields.DecimalField(max_digits=15, decimal_places=2, null=True)
    total_capital_equity_local = fields.DecimalField(max_digits=15, decimal_places=2, null=True)
    total_capital_equity_foreign = fields.DecimalField(max_digits=15, decimal_places=2, null=True)

    # Production Source Data
    total_production_local = fields.IntField(null=True)
    total_production_foreign = fields.IntField(null=True)
    total_production_both = fields.IntField(null=True)

    class Meta:
        app = 'report_views'
        table = "project_analytics"
        verbose_name = "Project Analytic"
        verbose_name_plural = "Project Analytics"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS project_analytics AS
        SELECT 
            1 AS id,  -- Single row ID
            'All Sectors' AS sector,  -- Global sector label
            COUNT(DISTINCT CASE WHEN p.evaluation_status = 'APPROVED' THEN p.id END) AS total_projects,
            COALESCE(ROUND(SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.investment_capital ELSE 0 END)::numeric, 2), 0.00) AS total_investment_capital,
            COALESCE(ROUND(AVG(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.investment_capital ELSE NULL END)::numeric, 2), 0.00) AS average_investment_capital,

            -- Project Status Counts
            COUNT(CASE WHEN p.evaluation_status = 'APPROVED' THEN 1 ELSE NULL END) AS approved_projects,
            COUNT(CASE WHEN p.evaluation_status = 'DRAFT' THEN 1 ELSE NULL END) AS draft_projects,
            COUNT(CASE WHEN p.evaluation_status = 'VERIFIED' THEN 1 ELSE NULL END) AS verified_projects,
            COUNT(CASE WHEN p.evaluation_status = 'SUBMITTED' THEN 1 ELSE NULL END) AS submitted_projects,
            COUNT(CASE WHEN p.evaluation_status = 'REVOKED' THEN 1 ELSE NULL END) AS revoked_projects,

            -- Employment Metrics (Only APPROVED projects considered)
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.male_local_permanent_employment_number ELSE 0 END) AS male_local_permanent_employment_number,
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.female_local_permanent_employment_number ELSE 0 END) AS female_local_permanent_employment_number,
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.male_local_temporary_employment_number ELSE 0 END) AS male_local_temporary_employment_number,
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.female_local_temporary_employment_number ELSE 0 END) AS female_local_temporary_employment_number,

            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.male_foreign_permanent_employment_number ELSE 0 END) AS male_foreign_permanent_employment_number,
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.female_foreign_permanent_employment_number ELSE 0 END) AS female_foreign_permanent_employment_number,
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.male_foreign_temporary_employment_number ELSE 0 END) AS male_foreign_temporary_employment_number,
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.female_foreign_temporary_employment_number ELSE 0 END) AS female_foreign_temporary_employment_number,

            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.male_local_disabled_employment_number ELSE 0 END) AS male_local_disabled_employment_number,
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.female_local_disabled_employment_number ELSE 0 END) AS female_local_disabled_employment_number,
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.male_foreign_disabled_employment_number ELSE 0 END) AS male_foreign_disabled_employment_number,
            SUM(CASE WHEN p.evaluation_status = 'APPROVED' THEN p.female_foreign_disabled_employment_number ELSE 0 END) AS female_foreign_disabled_employment_number,

            -- Capital Source Aggregation (Only APPROVED projects considered)
            COALESCE(SUM(CASE WHEN p.evaluation_status = 'APPROVED' AND p.capital_source = 'Loan (Local)' THEN p.investment_capital ELSE 0 END), 0.00) AS total_capital_loan_local,
            COALESCE(SUM(CASE WHEN p.evaluation_status = 'APPROVED' AND p.capital_source = 'Loan (Foreign)' THEN p.investment_capital ELSE 0 END), 0.00) AS total_capital_loan_foreign,
            COALESCE(SUM(CASE WHEN p.evaluation_status = 'APPROVED' AND p.capital_source = 'Equity (Local)' THEN p.investment_capital ELSE 0 END), 0.00) AS total_capital_equity_local,
            COALESCE(SUM(CASE WHEN p.evaluation_status = 'APPROVED' AND p.capital_source = 'Equity (Foreign)' THEN p.investment_capital ELSE 0 END), 0.00) AS total_capital_equity_foreign,

            -- Production Source Aggregation
            COUNT(CASE WHEN p.evaluation_status = 'APPROVED' AND p.production_source = 'Local' THEN 1 ELSE NULL END) AS total_production_local,
            COUNT(CASE WHEN p.evaluation_status = 'APPROVED' AND p.production_source = 'Foreign' THEN 1 ELSE NULL END) AS total_production_foreign,
            COUNT(CASE WHEN p.evaluation_status = 'APPROVED' AND p.production_source = 'Both' THEN 1 ELSE NULL END) AS total_production_both,

            -- Total Employment Count (Only APPROVED projects considered)
            SUM(
                CASE WHEN p.evaluation_status = 'APPROVED' THEN 
                    p.male_local_permanent_employment_number + p.female_local_permanent_employment_number +
                    p.male_local_temporary_employment_number + p.female_local_temporary_employment_number +
                    p.male_foreign_permanent_employment_number + p.female_foreign_permanent_employment_number +
                    p.male_foreign_temporary_employment_number + p.female_foreign_temporary_employment_number +
                    p.male_local_disabled_employment_number + p.female_local_disabled_employment_number +
                    p.male_foreign_disabled_employment_number + p.female_foreign_disabled_employment_number
                ELSE 0 END
            ) AS total_employment

        FROM public.projects p;
        """
        refresh_query = "REFRESH MATERIALIZED VIEW project_analytics;"
        dependencies = [Project]
        report_name = "Project Analytics"
        report_description = "Aggregated data for projects, including employment and evaluation statistics."
        managed = False


class InvestmentOpportunitiesReport(ReportView):
    id = fields.IntField(pk=True)
    region = fields.CharField(max_length=100)
    district = fields.CharField(max_length=100)
    ward = fields.CharField(max_length=100)
    date = fields.CharField(max_length=10)
    land_size = fields.DecimalField(max_digits=15, decimal_places=2)
    land_type = fields.CharField(max_length=45)
    land_use = fields.CharField(max_length=45)
    sector = fields.CharField(max_length=200)
    land_ownership = fields.CharField(max_length=45)
    coordinates = fields.JSONField()  # Stores Longitude & Latitude as List or JSON
    available_infrastructure = fields.JSONField()  # Available infrastructure (List or JSON)
    investment_mode = fields.CharField(max_length=100)
    availability_status = fields.CharField(max_length=45)
    type = fields.CharField(max_length=45)  # Added new field for the investment type

    class Meta:
        app = 'report_views'
        table = "investment_opportunities_report"
        verbose_name = "Investment Opportunities Report"
        verbose_name_plural = "Investment Opportunities Reports"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS investment_opportunities_report AS
        SELECT 
            ROW_NUMBER() OVER() AS id, -- Unique row ID
            r.name AS region,          -- Region name from `regions` table
            d.name AS district,        -- District name from `districts` table
            c.name AS council,         -- Council name from `councils` table
            w.name AS ward,            -- Ward name from `wards` table
            TO_CHAR(b.created_at, 'YYYY-MM') AS date,
            b.land_size AS land_size,
            b.land_type AS land_type,
            b.land_use AS land_use,
            s.name AS sector,
            b.ownership AS land_ownership,
            JSON_AGG(JSON_BUILD_OBJECT('latitude', co.latitude, 'longitude', co.longitude)) AS coordinates,
            JSON_AGG(DISTINCT f.name) AS available_infrastructure,
            b.investment_mode AS investment_mode,
            b.status AS availability_status,
            b.type AS type              -- Investment type (e.g., "Land", "Other Investment Opportunity")
        FROM 
            public.investment_opportunities b
        LEFT JOIN 
            public.wards w ON b.ward_id = w.id
        LEFT JOIN 
            public.councils c ON w.council_id = c.id              -- Added Council layer
        LEFT JOIN 
            public.districts d ON c.district_id = d.id            -- Join Council to District
        LEFT JOIN 
            public.regions r ON d.region_id = r.id                -- Join District to Region
        LEFT JOIN 
            public.sectors s ON b.sector_id = s.id                -- Join Sector
        LEFT JOIN 
            public.io_facilities f ON f.io_id = b.id              -- Join Facilities for Infrastructure
        LEFT JOIN 
            public.io_coordinates co ON co.io_id = b.id           -- Join Coordinates
        GROUP BY 
            r.name, d.name, c.name, w.name, date, b.land_size, b.land_type, b.land_use, s.name, b.ownership, b.investment_mode, b.status, b.type;
        """
        refresh_query = "REFRESH MATERIALIZED VIEW investment_opportunities_report;"
        dependencies = [InvestmentOpportunity, IOFacility, IOCoordinate, Sector]
        report_name = "Investment Opportunities Report"
        report_description = "Analytics report for investment opportunities aggregated by region, district, ward and sector."
        managed = False

class OutwardInvestmentReport(ReportView):
    id = fields.IntField(pk=True)  # Auto-generated unique ID for the view
    country = fields.CharField(max_length=100)  # Country of Investment
    sector = fields.CharField(max_length=200)  # Sector of the investment (added)
    number_of_projects = fields.IntField()  # Number of investment projects
    total_capital = fields.DecimalField(max_digits=20, decimal_places=2)  # Total Capital (USD)

    class Meta:
        app = 'report_views'
        table = "outward_investment_report"
        verbose_name = "Outward Investment Report"
        verbose_name_plural = "Outward Investment Reports"
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS outward_investment_report AS
        SELECT 
            ROW_NUMBER() OVER() AS id, -- Unique row ID
            c.name AS country,         -- Country of Investment
            s.name AS sector,          -- Sector of Investment (added)
            COUNT(o.id) AS number_of_projects,  -- Count of investments (projects)
            COALESCE(SUM(o.investment_capital), 0) AS total_capital -- Total investment capital
        FROM 
            public.outward_investments o
        LEFT JOIN 
            public.countries c ON o.country_id = c.id -- Join with the Countries table
        LEFT JOIN 
            public.sectors s ON o.sector_id = s.id -- Join with the Sectors table
        WHERE 
            o.created_at IS NOT NULL  -- Ensure there are valid timestamps
        GROUP BY 
            c.name, s.name;  -- Group by country and sector (updated)
        """
        refresh_query = "REFRESH MATERIALIZED VIEW outward_investment_report;"
        dependencies = [OutwardInvestment, Country, Sector]  # Dependencies for the report
        report_name = "Outward Investment Aggregated Report"
        report_description = "Summary report for outward investments, grouped by country, sector, and other aggregations."
        managed = False  # This is a report, not an ORM-managed table