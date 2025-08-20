from typing import Any, Dict, List
import uuid
from tortoise import fields, models
from fast_api_builder.muarms.models import TimeStampedModel, HeadshipType

'''List of Models'''


# Ministry
class Ministry(TimeStampedModel):
    name = fields.CharField(max_length=100, unique=True)
    code = fields.CharField(max_length=20, unique=True)

    class Meta:
        table = "ministries"
        verbose_name = "Ministry"
        verbose_name_plural = "Ministries"

    def __str__(self):
        return self.name


# Institution
class Institution(TimeStampedModel):
    name = fields.CharField(max_length=100, unique=True)
    code = fields.CharField(max_length=20, unique=True)
    ministry = fields.ForeignKeyField('models.Ministry', related_name='institutions', on_delete=fields.RESTRICT)

    class Meta:
        table = "institutions"
        verbose_name = "Institution"
        verbose_name_plural = "Institutions"

    def __str__(self):
        return self.name

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'id',
                'path': None
            },
        ]


# Country
class Country(TimeStampedModel):
    name = fields.CharField(max_length=100, unique=True)
    code = fields.CharField(max_length=20, unique=True)
    iso_3_code = fields.CharField(max_length=20, unique=True)
    continent = fields.CharField(max_length=100, null=True)

    regions: fields.ReverseRelation["Region"]

    class Meta:
        table = "countries"
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


# Region
class Region(TimeStampedModel):
    name = fields.CharField(max_length=100, unique=True)
    code = fields.CharField(max_length=20, unique=True)
    country = fields.ForeignKeyField("models.Country", related_name="regions", on_delete=fields.RESTRICT)
    napa_id = fields.IntField(max_length=100, nullable=True)
    districts: fields.ReverseRelation["District"]

    class Meta:
        table = "regions"
        verbose_name = "Region"
        verbose_name_plural = "Regions"

    def __str__(self):
        return f"{self.name}"

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Region,
                'headship_type': HeadshipType.REGION,
                'column': 'id',
                'path': None
            },
            {
                'model': District,
                'headship_type': HeadshipType.DISTRICT,
                'column': 'id',
                'path': 'region'
            },
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'id',
                'path': None,
                'global_filter': True
            },
        ]


# District
class District(TimeStampedModel):
    name = fields.CharField(max_length=100)
    code = fields.CharField(max_length=20)
    region = fields.ForeignKeyField('models.Region', related_name='districts', on_delete=fields.RESTRICT)
    napa_id = fields.IntField(max_length=100, nullable=True)
    councils: fields.ReverseRelation["Council"]

    class Meta:
        table = "districts"
        verbose_name = "District"
        verbose_name_plural = "Districts"
        unique_together = (("code", "region"),)

    def __str__(self):
        return self.name

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': District,
                'headship_type': HeadshipType.DISTRICT,
                'column': 'id',
                'path': None
            },
            {
                'model': Region,
                'headship_type': HeadshipType.REGION,
                'column': 'id',
                'path': 'districts'
            },
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'id',
                'path': None,
                'global_filter': True
            },
        ]


class Council(TimeStampedModel):
    name = fields.CharField(max_length=100)
    code = fields.CharField(max_length=20)
    district = fields.ForeignKeyField('models.District', related_name='councils', on_delete=fields.RESTRICT)
    napa_id = fields.IntField(max_length=100, nullable=True)
    wards: fields.ReverseRelation["Ward"]

    class Meta:
        table = "councils"
        verbose_name = "Council"
        verbose_name_plural = "Councils"
        # unique_together = (("code", "district"),)

    def __str__(self):
        return self.name


# Ward
class Ward(TimeStampedModel):
    name = fields.CharField(max_length=100)
    code = fields.CharField(max_length=20)
    napa_id = fields.IntField(max_length=100, nullable=True)
    council = fields.ForeignKeyField('models.Council', related_name='wards', on_delete=fields.RESTRICT)
    villages: fields.ReverseRelation["Village"]

    class Meta:
        table = "wards"
        verbose_name = "Ward"
        verbose_name_plural = "Wards"
        unique_together = (("code", "council"),)

    def __str__(self):
        return self.name

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        from fast_api_builder.muarms.models import Company
        return [
            {
                'model': Region,
                'headship_type': HeadshipType.REGION,
                'column': 'id',
                'path': 'districts__councils__wards'
            },
            {
                'model': District,
                'headship_type': HeadshipType.DISTRICT,
                'column': 'id',
                'path': 'councils__wards'
            },
            {
                'model': Institution,
                'headship_type': HeadshipType.INSTITUTION,
                'column': 'id',
                'path': None,
                'global_filter': True
            },
            {
                'model': Company,
                'headship_type': HeadshipType.COMPANY,
                'column': 'id',
                'path': None,
                'global_filter': True
            },
        ]


class Village(TimeStampedModel):
    name = fields.CharField(max_length=100)
    code = fields.CharField(max_length=20)
    ward = fields.ForeignKeyField('models.Ward', related_name='villages', on_delete=fields.RESTRICT)
    areas: fields.ReverseRelation["Area"]

    class Meta:
        table = "villages"
        verbose_name = "Village"
        verbose_name_plural = "Villages"
        unique_together = (("code", "ward"),)

    def __str__(self):
        return self.name


class Area(TimeStampedModel):
    name = fields.CharField(max_length=100)
    code = fields.CharField(max_length=20)
    village = fields.ForeignKeyField('models.Village', related_name='areas', on_delete=fields.RESTRICT)

    class Meta:
        table = "areas"
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        unique_together = (("code", "village"),)

    def __str__(self):
        return self.name


class Sector(TimeStampedModel):
    name = fields.CharField(max_length=250)
    code = fields.CharField(max_length=20, unique=True)

    sub_sectors: fields.ReverseRelation["SubSector"]

    class Meta:
        table = "sectors"
        verbose_name = "Sector"
        verbose_name_plural = "Sectors"

    def __str__(self):
        return self.name


# Sub Sector
class SubSector(TimeStampedModel):
    name = fields.CharField(max_length=250)
    code = fields.CharField(max_length=20, unique=True)
    sector = fields.ForeignKeyField('models.Sector', related_name='sub_sectors', on_delete=fields.RESTRICT)

    class Meta:
        table = "sub_sectors"
        verbose_name = "Sub Sector"
        verbose_name_plural = "Sub Sectors"

    def __str__(self):
        return self.name


class Attachment(TimeStampedModel):
    title = fields.CharField(max_length=100, null=True)
    description = fields.CharField(max_length=1000, null=True)
    file_path = fields.CharField(max_length=200)
    mem_type = fields.CharField(max_length=45, null=True)
    attachment_type = fields.CharField(max_length=45)
    attachment_type_id = fields.IntField()
    attachment_type_category = fields.CharField(max_length=45, null=True) # category for particular type


    class Meta:
        table = "attachments"  # Specify the table name if needed

    def __str__(self):
        return f"Attachment {self.id} - {self.file_path}"


class CooperateSocial(TimeStampedModel):
    name = fields.CharField(max_length=100)

    class Meta:
        table = "cooperate_social"
        verbose_name = "Cooperate Social"
        verbose_name_plural = "Cooperate Socials"

class Campus(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    code = fields.CharField(max_length=200, unique=True)
    campus_number = fields.IntField(unique=True)
    tcu_code = fields.CharField(max_length=20, null=True)

    class Meta:
        table = "campus"

    def __str__(self):
        return self.name

class Unit(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    code = fields.CharField(max_length=200, unique=True)
    campus = fields.ForeignKeyField("models.Campus", related_name="units")
    school_number = fields.IntField()

    class Meta:
        table = "unit"
        unique_together = ("campus", "school_number")

    def __str__(self):
        return self.name

class Department(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    code = fields.CharField(max_length=200, null=True)
    unit = fields.ForeignKeyField("models.Unit", related_name="departments")

    class Meta:
        table = "department"
        unique_together = ("code", "unit")

    def __str__(self):
        return self.name