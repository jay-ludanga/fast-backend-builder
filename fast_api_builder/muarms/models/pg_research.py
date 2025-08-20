from typing import List, Dict, Any

from tortoise import fields

from fast_api_builder.muarms.enums import ResearchStage
from fast_api_builder.muarms.models import HeadshipModel, TimeStampedModel, Programme, HeadshipType


# class Conversation(TimeStampedModel):
#     stage = fields.CharField(max_length=100, unique=True)

#     class Meta:
#         table = "conversations"
#         verbose_name = "Conversation"
#         verbose_name_plural = "Conversations"

#     def __str__(self):
#         return self.stage

class StudentResearchStage(TimeStampedModel):
    student = fields.ForeignKeyField('models.Student', related_name='research_stage', on_delete=fields.CASCADE)
    stage = fields.CharField(max_length=100)

    class Meta:
        table = "student_research_stages"
        verbose_name = "Research Stage"
        verbose_name_plural = "Research Stages"
        
    async def can_go_to(self, next_stage: str):
        """Validates if the student can proceed to the next stage."""

        # Ensure student has an approved title
        title = await Title.filter(
            student_id=self.student_id,
            evaluation_status='APPROVED',
            is_active=True
        ).first()
        print('title', title)
        if not title:
            return False  

        is_phd = True # self.student.is_phd
        ordered_stages = ResearchStage.get_ordered_stages(is_phd)

        try:
            current_index = ordered_stages.index(ResearchStage(self.stage))
            next_index = ordered_stages.index(ResearchStage(next_stage))
        except ValueError:
            return False  # Invalid stage provided

        # Allow moving backwards to any previous stage
        if next_index <= current_index:
            return True

        # Ensure the next stage is exactly the next in sequence
        if next_index != current_index + 1:
            return False

        # Define stage-specific conditions
        stage_conditions = {
            ResearchStage.TITLE_AGREEMENT: self._can_leave_supervisor_allocation,
            ResearchStage.SUPERVISOR_ALLOCATION: self._can_leave_proposal_development,
            ResearchStage.PROPOSAL_DEVELOPMENT: self._can_leave_data_collection,
            ResearchStage.DATA_COLLECTION: self._can_leave_data_finding,
            ResearchStage.DATA_FINDING: self._can_leave_viva,  # Only for PhD
        }

        # Run specific checks for the current stage (if they exist)
        check_func = stage_conditions.get(ResearchStage(next_stage))
        return await check_func() if check_func else True
    
    async def _can_leave_supervisor_allocation(self):
        return True
    
    async def _can_leave_proposal_development(self):
        return True
    
    async def _can_leave_data_collection(self):
        return True
    
    async def _can_leave_data_finding(self):
        return True
    
    async def _can_leave_viva(self):
        return True
    
class SpecializationArea(HeadshipModel):
    class Meta:
        table = 'specialization_area'
        verbose_name_plural = 'SpecializationAreas'
        
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    
class Title(TimeStampedModel):
    name = fields.CharField(max_length=255)
    student = fields.ForeignKeyField('models.Student', related_name='titles', on_delete=fields.CASCADE)
    specialization_area = fields.ForeignKeyField('models.SpecializationArea', related_name='titles', on_delete=fields.CASCADE)
    address = fields.CharField(max_length=200, nullable=False)
    last_stage = fields.CharField(max_length=100, default=ResearchStage.TITLE_AGREEMENT.value)
    evaluation_status = fields.CharField(max_length=20, default="DRAFT")
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "titles"
        verbose_name = "Title"
        verbose_name_plural = "Titles"
        
    def resource_notification_message(self):
        return f"'{self.name}'"

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Programme,
                'combine': 'OR',  # Combine with OR
                'headship_type': HeadshipType.PROGRAMME,
                'column': 'student__programme_id',
                'path': None,
            }
        ]

class TitleChangeRequest(TimeStampedModel):
    name = fields.CharField(max_length=255)
    title = fields.ForeignKeyField('models.Title', related_name='title_change_request', on_delete=fields.CASCADE)
    specialization_area = fields.ForeignKeyField('models.SpecializationArea', related_name='title_change', on_delete=fields.CASCADE)
    address = fields.CharField(max_length=200, null=True)
    evaluation_status = fields.CharField(max_length=20, default="DRAFT")
    reason = fields.CharField(max_length=500)
    

    class Meta:
        table = "title_change_requests"
        verbose_name = "Title Change Request"
        verbose_name_plural = "Titles Change Requests"

    def resource_notification_message(self):
        return f"'{self.name}'"

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        return [
            {
                'model': Programme,
                'combine': 'OR',  # Combine with OR
                'headship_type': HeadshipType.PROGRAMME,
                'column': 'title__student__programme_id',
                'path': None,
            }
        ]
        
class Supervisor(TimeStampedModel):
    SupervisorType = [
        ('Major', 'Major'),
        ('Core', 'Core'),
        ('External', 'External'),
        ('Findings', 'Findings'),
    ]
    user = fields.ForeignKeyField('models.User', related_name='supervisions', on_delete=fields.CASCADE)
    title = fields.ForeignKeyField('models.Title', related_name='supervisors', on_delete=fields.CASCADE)
    type = fields.CharField(max_length=20, choices=SupervisorType)
    address = fields.CharField(max_length=200, null=True)
    is_active = fields.BooleanField(default=True)


    class Meta:
        table = "research_supervisors"
        verbose_name = "Supervisor"
        verbose_name_plural = "Supervisors"
        unique_together = (("user", "title"),)


class StudyPlan(TimeStampedModel):
    title = fields.ForeignKeyField('models.Title', on_delete=fields.CASCADE)

    class Meta:
        table = "study_plans"
        verbose_name = "Study Plan"
        verbose_name_plural = "Study Plan"


class Proposal(TimeStampedModel):
    title = fields.ForeignKeyField('models.Title', on_delete=fields.CASCADE)
    evaluation_status = fields.CharField(max_length=20, null=True)

    class Meta:
        table = "proposals"
        verbose_name = "Proposal"
        verbose_name_plural = "Proposals"

class DataCollection(TimeStampedModel):
    title = fields.ForeignKeyField('models.Title', on_delete=fields.CASCADE,unique=True)

    class Meta:
        table = "data_collections"
        verbose_name = "Data Collection"
        verbose_name_plural = "Data Collections"
class DataFinding(TimeStampedModel):
    title = fields.ForeignKeyField('models.Title', on_delete=fields.CASCADE)
    class Meta:
        table = "data_findings"
        verbose_name = "Data Finding"
        verbose_name_plural = "Data Findings"

class Presentation(TimeStampedModel):
    title = fields.ForeignKeyField('models.Title', on_delete=fields.CASCADE)
    program_type = fields.CharField(max_length=45)
    type = fields.CharField(max_length=45)
    stage = fields.CharField(max_length=20)
    level = fields.CharField(max_length=20)

    class Meta:
        table = "presentations"
        verbose_name = "Presentation"
        verbose_name_plural = "Presentations"

class PresentationMember(TimeStampedModel):
    user = fields.ForeignKeyField('models.User', related_name='presentations', on_delete=fields.CASCADE)
    presentation = fields.ForeignKeyField('models.Presentation', related_name='members', on_delete=fields.CASCADE)

    class Meta:
        table = "presentation_members"
        verbose_name = "Presentation Member"
        verbose_name_plural = "Presentation Members"

class Conversation(TimeStampedModel):
    title = fields.ForeignKeyField('models.Title', on_delete=fields.CASCADE)
    type = fields.CharField(max_length=45)
    # participants = fields.ManyToManyField(
    #     'models.User', 
    #     related_name='conversations', 
    #     through='conversation_participants'  # Specifies the join table
    # )
    
    class Meta:
        table = "conversations"
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"

class ConversationParticipant(TimeStampedModel):
    conversation = fields.ForeignKeyField('models.Conversation', related_name='participants', on_delete=fields.CASCADE)
    user = fields.ForeignKeyField('models.User', related_name='participants', on_delete=fields.CASCADE)

    class Meta:
        table = "conversation_participants"
        verbose_name = "Conversation Participant"
        verbose_name_plural = "Conversation Participants"

class Message(TimeStampedModel):
    conversation = fields.ForeignKeyField('models.Conversation', on_delete=fields.CASCADE)
    sender = fields.ForeignKeyField('models.User', related_name='messages_sender', on_delete=fields.CASCADE)
    content = fields.TextField()
    stage = fields.CharField(max_length=20)
    is_read = fields.BooleanField(default=False)
    reply_to = fields.ForeignKeyField('models.User', related_name='messages_reply', on_delete=fields.CASCADE,null=True)

    class Meta:
        table = "messages"
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["-created_at"]

class Examiner(TimeStampedModel):
    title = fields.ForeignKeyField('models.Title', on_delete=fields.CASCADE)
    user = fields.ForeignKeyField('models.User', related_name='examiner', on_delete=fields.CASCADE)
    is_active = fields.BooleanField(default=True)
    class Meta:
        table = "examiners"
        verbose_name = "Examiner"
        verbose_name_plural = "Examiners"
class ResearchExamResult(TimeStampedModel):
    examiner = fields.ForeignKeyField('models.Examiner', on_delete=fields.CASCADE)
    comment = fields.TextField()
    score = fields.FloatField()
    class Meta:
        table = "research_exam_results"
        verbose_name = "Research Exam Result"
        verbose_name_plural = "Research Exam Results"
class Manuscript(TimeStampedModel):
    title = fields.ForeignKeyField('models.Title', on_delete=fields.CASCADE)
    status = fields.CharField(max_length=20)
    class Meta:
        table = "manuscripts"
        verbose_name = "Manuscript"
        verbose_name_plural = "Manuscripts"