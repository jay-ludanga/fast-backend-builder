import strawberry
from enum import Enum


@strawberry.enum
class CapitalSource(str, Enum):
    LOAN_LOCAL = "Loan (Local)"
    LOAN_FOREIGN = "Loan (Foreign)"
    EQUITY_LOCAL = "Equity (Local)"
    EQUITY_FOREIGN = "Equity (Foreign)"


@strawberry.enum
class ProductionSource(str, Enum):
    LOCAL = "Local"
    FOREIGN = "Foreign"
    BOTH = "Both"


@strawberry.enum
class OwnershipType(str, Enum):
    PUBLIC = "Public - Public Investment"
    PRIVATE_LOCAL = "Private (Local)"
    PRIVATE_FOREIGN = "Private (Foreign)"
    PRIVATE_JOINT_VENTURE = "Private (Joint Venture)"
    PPP = "PPP"  # Public-Private Partnership


@strawberry.enum
class LicenseType(str, Enum):
    PRIMARY = "Primary License"
    PROSPECTING = "Prospecting License"
    PROCESSING = "Processing License"


@strawberry.enum
class ProjectStatus(str, Enum):
    OPERATIONAL = "Operational"
    TERMINATED = "Terminated"
    SUSPENDED = "Suspended"


@strawberry.enum
class LandUnit(str, Enum):
    ACRE = 'ac'
    HECTARE = 'ha'
    SQUARE_FOOT = 'sq ft'
    SQUARE_METER = 'sq m'
    SQUARE_KILOMETER = 'sq km'
    SQUARE_MILE = 'sq mi'
    SQUARE_YARD = 'sq yd'


@strawberry.enum
class LandType(str, Enum):
    RESERVED = "Reserved"
    VILLAGE = "Village"
    GENERAL = "General"


@strawberry.enum
class LandOwnershipType(str, Enum):
    PUBLIC = "Public"
    VILLAGE = "Village"
    PRIVATE = "Private"
    OTHERS = "Others"


@strawberry.enum
class InvestmentOpportunityType(str, Enum):
    PROPERTY = "Other Investment Opportunity"
    LAND = "Land"


@strawberry.enum
class InvestmentOpportunityStatus(str, Enum):
    AVAILABLE = "Available"
    NOT_AVAILABLE = "Not Available"


@strawberry.enum
class EnquiryType(str, Enum):
    Complaint = "Complaint"
    Compliments = "Compliments"
    Inquiries = "Inquiries"
    Commendation = "Commendation"


@strawberry.enum
class InvestmentModeType(str, Enum):
    LEASE = "Lease"
    JOINTVENTURE = "Joint Venture"
    SALES = "Sales/Disposal"


@strawberry.enum
class NotificationContentType(str, Enum):
    PASSWORD_RESET = "Password Reset"
    ACCOUNT_CONFIRMATION = "Account Confirmation"
    PUSH_NOTIFICATION = "PUSH Notification"
    APPLICANT_NOTIFICATION = "Applicant Notification"
    EVALUATOR_NOTIFICATION = "Evaluator Notification"


@strawberry.enum
class ProjectStatus(str, Enum):
    NEW_PROJECT = "New Project"
    EXPANSION = "Expansion"
    REHABILITATION = "Rehabilitation"


# @strawberry.enum
# class HeadshipType(str, Enum):
#     GLOBAL = "Global"
#     INSTITUTION = "Institution"
#     COMPANY = "Company"
#     REGION = "Region"
#     DISTRICT = "District"


@strawberry.enum
class PushNotificationType(str, Enum):
    survey = "projects/survey"
    iop = "investments/iop"
    outwardInvestment = "investments/outward-investments"
    standalone = "projects/standalone"
    project = "project"


@strawberry.enum
class OutwardInvestmentReason(str, Enum):
    UNPREDICTABLE_POLICIES = "Unpredictable Policies"
    HIGH_COST = "High Cost of Productions"
    RAW_MATERIALS = "Scarcity of Raw Materials"
    TAX_MANAGEMENT = "Tax Management"
    GOVT_RESTRICTIONS = "Government Restrictions"
    TECH_ISSUES = "Technology Issues"
    SKILLED_LABOR = "Skilled Labor"
    INTL_CERTIFICATIONS = "International Certifications"
    MARKET_ISSUES = "Market Issues"
    INCENTIVES = "Special Incentives Package"
    INFRASTRUCTURE = "Infrastructure Issues"


@strawberry.enum
class PhysicalLocationType(str, Enum):
    RURAL = "Rural"
    URBAN = "Urban"


@strawberry.enum
class CsrContributionType(str, Enum):
    EDUCATION_SERVICES = "Education Services",
    HEALTH_SERVICES = "Health Services",
    WATER_SERVICES = "Water Services",
    PHYSICAL_SERVICES = "Physical Infrastructures",
    RELIGIOUS_SERVICES = "Religious Services"


@strawberry.enum
class ReportPriority(Enum):
    HIGH = "High"
    LOW = "Low"


# deed type
@strawberry.enum
class TitleDeedType(Enum):
    GRANTED_RIGHT = "Granted right"
    DERIVATIVE_RIGHT = "Derivative Right"
    CUSTOMARY_RIGHT = "Customary Right"
    OTHER_SPECIFY = "Other"


@strawberry.enum
class OutwardInvestmentStatus(Enum):
    OPERATIONAL = "Operational"
    NOT_OPERATIONAL = "Not Operational"
@strawberry.enum
class ConversationType(str, Enum):
    PRIVATE = "Private"
    GROUP = "Group"
@strawberry.enum
class IoAttachmentType(Enum):
    PHOTO = "Photo"
    LEASE = "Lease"

@strawberry.enum
class ProgrammeType(str, Enum):
    MASTERS = "Masters"
    PHD= "PhD"

@strawberry.enum
class PresentationLevel(str, Enum):
    DEPARTMENT = "Department"
    FACULTY = "Faculty"
    DRPS = "DrPS"
@strawberry.enum
class DataFindingStatus(Enum):
    INITIATED = "Initiated"
    APPROVED = "Approved"
    REJECTED = "Rejected"
@strawberry.enum
class ResearchStage(str, Enum):
    TITLE_AGREEMENT = "Title Agreement"
    SUPERVISOR_ALLOCATION = "Supervisor Allocation"
    PROPOSAL_DEVELOPMENT = "Proposal Development"
    DATA_COLLECTION = "Data Collection"
    DATA_FINDING = "Data Finding"
    VIVA = "Viva"
    
    @classmethod
    def get_ordered_stages(cls, is_phd: bool):
        """Returns ordered stages based on student level."""
        stages = [
            cls.TITLE_AGREEMENT, 
            cls.SUPERVISOR_ALLOCATION, 
            cls.PROPOSAL_DEVELOPMENT, 
            cls.DATA_COLLECTION, 
            cls.DATA_FINDING if is_phd else None,
            cls.VIVA
        ]
        return [stage for stage in stages if stage]