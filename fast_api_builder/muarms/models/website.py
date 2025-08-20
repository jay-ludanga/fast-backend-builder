from tortoise import fields

from fast_api_builder.muarms.models import TimeStampedModel, Project


class News(TimeStampedModel):
    title = fields.CharField(max_length=250)
    description = fields.TextField()
    content = fields.TextField(null=True)
    is_published = fields.BooleanField(default=False)

    created_by = fields.ForeignKeyField(
        "models.User",
        null=True,
        on_delete=fields.SET_NULL,
        related_name="news_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "news"
        verbose_name = "News"
        verbose_name_plural = "News"

    def __str__(self):
        return self.title


class Enquiry(TimeStampedModel):
    title = fields.CharField(max_length=100)
    description = fields.TextField()
    suggestions = fields.TextField(null=True)
    user = fields.ForeignKeyField('models.User', related_name='enquiries', on_delete=fields.RESTRICT)
    enquiry_type = fields.CharField(max_length=100)
    project = fields.ForeignKeyField('models.Project', related_name='project_enquiries', on_delete=fields.RESTRICT)
    track_no = fields.CharField(max_length=100, null=True, unique=True)
    track_id = fields.CharField(max_length=100, null=True, unique=True)
    status = fields.CharField(max_length=100, default='draft')
    submitted_at = fields.DatetimeField(null=True)
    feedback_locked_at = fields.CharField(max_length=100, null=True)
    
    closing_remarks = fields.TextField(null=True)
    legal_opinions = fields.TextField(null=True)


    class Meta:
        table = "enquiries"
        verbose_name = "Enquiry"
        verbose_name_plural = "Enquiries"
    
    def __str__(self):
        return self.title

    async def get_status(self):
        latest_feedback = await Feedback.filter(enquiry=self).order_by("-created_at").first()
        if latest_feedback:
            return latest_feedback.status
        return self.status  # or a default status like "no_feedback"


class EnquiryHistory(TimeStampedModel):
    enquiry = fields.ForeignKeyField('models.Enquiry', related_name='history', on_delete=fields.CASCADE)
    title = fields.CharField(max_length=100)
    description = fields.TextField()
    enquiry_type = fields.CharField(max_length=100)
    suggestions = fields.TextField(null=True)



    class Meta:
        table = "enquiry_history"
        verbose_name = "Enquiry History"
        verbose_name_plural = "Enquiry History"

    def __str__(self):
        return f"History for {self.enquiry.title} at {self.updated_at}"



class Feedback(TimeStampedModel):
    # Optional association with an internal enquiry
    enquiry = fields.ForeignKeyField('models.Enquiry', related_name='feedbacks', on_delete=fields.CASCADE, null=True)

    action = fields.CharField(max_length=255)
    action_date = fields.DatetimeField()
    action_by = fields.CharField(max_length=255)
    
    stage = fields.CharField(max_length=50)
    stage_name = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "feedbacks"
        verbose_name = "Feedback"
        verbose_name_plural = "Feedbacks"

    def __str__(self):
        if self.enquiry:
            return f"Feedback for {self.enquiry.title} - {self.status}"
        elif self.external_enquiry:
            return f"External Feedback {self.external_enquiry.external_reference} - {self.status}"
        return f"Feedback (Unknown Source) - {self.status}"

    @property
    def is_internal(self):
        return self.enquiry is not None

    @property
    def is_external(self):
        return self.external_enquiry is not None
