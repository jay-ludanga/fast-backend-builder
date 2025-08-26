import uuid
from enum import Enum

from tortoise import models, fields
from tortoise.queryset import Q

from typing import Any, Dict, List

from fast_backend_builder.utils.enums import HeadshipType


class HeadshipModel(models.Model):
    class Meta:
        abstract = True  # Ensure no table is created for this model

    @classmethod
    async def with_headship(cls, headships: List[Dict[str, Any]] = None):
        """
        Main function to filter query based on user headships.

        Args:
            headships (List[Dict[str, Any]]): An optional list of dictionaries containing
            headship information, including:
                - `model`: The Tortoise ORM model related to the entity (e.g., `Ward`).
                - `headship_type`: The type of headship (from the `HeadshipType` enum).
                - `column`: The foreign key column that links the resource to a headship.
                - `path`: The ORM path for filtering or accessing data through nested relationships.

        Returns:
            The filtered query based on user headships or an unfiltered query if conditions are met.
        """
        # Start with an empty query (can be customized in subclasses)
        query = cls.init_headship_query()

        # Retrieve headships either from the provided argument or by calling get_headships
        model_headships = headships if headships else cls.get_headships()

        # Proceed only if model_headships is a list with elements
        if model_headships and isinstance(model_headships, List):
            filtered = False  # Flag to check if any filtering occurred
            q_and_group = []  # For conditions that must be combined with AND
            q_or_group = []  # For conditions that must be combined with OR

            # Iterate over each headship in model_headships
            for model_headship in model_headships:
                # Get the user-specific headships based on the model headship type
                user_headships = await cls.get_user_headships(model_headship)

                # If any user has a GLOBAL headship, skip filtering and return the query
                if cls.has_global_headship(user_headships):
                    return query

                if cls.has_global_filter(model_headship, user_headships):
                    return query

                # Build and categorize the conditions
                conditions = await cls.build_q_conditions(model_headship, user_headships)
                q_and_group.extend(conditions["AND"])
                q_or_group.extend(conditions["OR"])

                filtered = filtered or bool(conditions["AND"] or conditions["OR"])
            query = cls.apply_q_conditions(query, q_and_group, q_or_group)

            # If no filters were applied but headships are defined, add a placeholder filter
            if not filtered and len(model_headships):
                query = cls.apply_placeholder_filter(query)

        return query

    @classmethod
    def init_headship_query(cls):
        """
        Initialize an empty query for the base class.

        Returns:
            The initial query object for the class. Can be overridden by subclasses to
            modify the default starting query (e.g., applying default filters).
        """
        return cls.all()

    @classmethod
    def get_headships_safe(cls):
        """
        Safely attempt to get headships if the function is defined, otherwise return None.

        Returns:
            The result of get_headships if defined; otherwise, None.
        """
        return getattr(cls, 'get_headships', lambda: None)()

    @classmethod
    async def get_user_headships(cls, model_headship):
        """
        Fetch user headships for a given model headship type.

        Args:
            model_headship (dict): Contains information about the model headship.

        Returns:
            A list of user headships based on the headship type.
        """
        from fast_backend_builder.auth.auth import Auth
        return await Auth.user_headships(model_headship['headship_type'])

    @classmethod
    def has_global_headship(cls, user_headships):
        """
        Check if there is a global headship among the user headships.

        Args:
            user_headships (list): List of user headship objects.

        Returns:
            bool: True if a global headship is present, otherwise False.
        """

        return any(
            user_headship.headship_type == HeadshipType.GLOBAL.value
            for user_headship in user_headships if user_headship
        )

    @classmethod
    def has_global_filter(cls, model_headship, user_headships):
        """
        Check if a global filter exists among the user headships.
        """
        headship_type = model_headship.get('headship_type').value
        return any(
            user_headship.headship_type == headship_type and model_headship.get('global_filter')
            for user_headship in user_headships if user_headship
        )

    @classmethod
    async def build_q_conditions(cls, model_headship, user_headships):
        """
        Build Q conditions based on model headships and user headships,
        supporting different combinations (e.g., AND or OR) based on configuration.

        Args:
            model_headship (dict): Information about the model's headship.
            user_headships (list): User headships associated with the model.

        Returns:
            dict: A categorized dictionary with `AND` and `OR` conditions.
        """
        q_and_conditions = []  # Collect conditions for AND combination
        q_or_conditions = []  # Collect conditions for OR combination

        # Determine the combination logic (default to AND if not specified)
        combine_type = model_headship.get('combine', 'AND').upper()

        # Loop through each user headship to build filtering conditions
        for user_headship in user_headships:
            if user_headship:
                # If filter_func is defined in the headship column, it is stored for additional filtering
                if model_headship['model'].__name__ == user_headship.headship_type and 'filter_func' in model_headship:
                    _condition = model_headship['filter_func']
                else:
                    _condition = Q()  # Default to an empty Q (no additional filtering)

                # Build the Q condition for this user headship
                if cls is model_headship['model']:
                    condition = Q(id=user_headship.headship_id)  # Direct match
                else:
                    ids = await cls.get_related_ids(model_headship, user_headship)
                    condition = Q(**{f"{model_headship['column']}__in": ids})  # Indirect match

                # Combine the main condition with _condition using AND
                condition &= _condition

                # Categorize the condition based on the "combine" key
                if combine_type == 'AND':
                    q_and_conditions.append(condition)
                elif combine_type == 'OR':
                    q_or_conditions.append(condition)

        return {"AND": q_and_conditions, "OR": q_or_conditions}

    # @classmethod
    # async def get_related_ids(cls, model_headship, user_headship):
    #     """
    #     Fetch related IDs for filtering based on a specific path or model headship.
    #
    #     Args:
    #         model_headship (dict): Information about the model's headship.
    #         user_headship (object): Specific user headship instance.
    #
    #     Returns:
    #         list: A list of IDs for use in filtering related entities.
    #     """
    #     ids_query = model_headship['model'].filter(id=user_headship.headship_id)
    #
    #     # If a path is defined, fetch related IDs using prefetch_related
    #     if model_headship.get('path', None):
    #         return await ids_query.prefetch_related(f"{model_headship['path']}") \
    #             .values_list(f"{model_headship['path']}__id", flat=True)
    #     else:
    #         # Directly fetch IDs without prefetching
    #         return await ids_query.values_list("id", flat=True)

    @classmethod
    async def get_related_ids(cls, model_headship, user_headship):
        """
        Fetch related IDs for filtering based on a specific path or model headship.

        Args:
            model_headship (dict): Information about the model's headship.
            user_headship (object): Specific user headship instance.

        Returns:
            list: A list of IDs for use in filtering related entities.
        """
        ids_query = model_headship['model'].filter(id=user_headship.headship_id)

        # If a path is defined, fetch related IDs
        if model_headship.get('path', None):
            # Filter out None values directly in the query
            ids = await ids_query.prefetch_related(f"{model_headship['path']}") \
                .exclude(**{f"{model_headship['path']}__id": None}) \
                .values_list(f"{model_headship['path']}__id", flat=True)
        else:
            # Directly fetch IDs without prefetching
            ids = await ids_query.values_list("id", flat=True)

        return ids

    @classmethod
    def apply_q_conditions(cls, query, q_and_group, q_or_group):
        """
        Combine Q conditions with OR and apply them to the query.

        Args:
            query: The initial query object.
            q_conditions (list): List of Q objects to be combined and applied.

        Returns:
            The query with combined conditions applied.
        """
        # Combine `AND` conditions
        combined_and = None
        if q_and_group:
            combined_and = q_and_group.pop(0)
            for cond in q_and_group:
                combined_and &= cond  # Combine with AND

        # Combine `OR` conditions
        combined_or = None
        if q_or_group:
            combined_or = q_or_group.pop(0)
            for cond in q_or_group:
                combined_or |= cond  # Combine with OR

        # Combine `AND` and `OR` groups with OR
        final_condition = combined_and
        if combined_or:
            final_condition = combined_and | combined_or if combined_and else combined_or

        # Apply the final conditions to the query
        if final_condition:
            query = query.filter(final_condition)

        return query

    @classmethod
    def apply_placeholder_filter(cls, query):
        """
        Apply a placeholder filter if no actual filters were applied.

        Args:
            query: The initial query object.

        Returns:
            The query with a placeholder filter that returns no results.
        """
        import uuid
        # Filter by a non-existent UUID to ensure no results are returned
        return query.filter(id=uuid.uuid4())

    """
    Abstract base class that defines the `get_headships()` method.

    This method should return a list of dictionaries where each dictionary defines:
      - `model`: The Tortoise ORM model related to the entity (e.g., `Ward`).
      - `headship_type`: The type of headship (from the `HeadshipType` enum).
      - `column`: The foreign key column that links the resource to a headship 
                  (e.g., 'ward_id' for resources linked to wards).
      - `path`: The ORM path for filtering or accessing data through nested relationships.
               This helps identify how the resource is related to a specific entity 
               (e.g., a `Ward` linked via a region > district > council > division).

    Classes that inherit this abstract base class must implement their own version of `get_headships()`
    to define resource-specific headship relationships.

    This allows CRUD operations (create, read, update, delete) to be governed based on headship rules,
    ensuring that only users with the appropriate headship can perform operations on resources.
    """

    @classmethod
    def get_headships(cls) -> List[Dict[str, Any]]:
        """
        Abstract method to be implemented by child classes.

        Returns:
            A list of dictionaries, where each dictionary defines:
              - `model`: The ORM model related to this model which is linked with headship rules.
              - `headship_type`: The type of headship (from `HeadshipType` enum).
              - `column`: The field in this model which is the foreign key to the model.
              - `path`: The ORM path for filtering using relationships describing parents of the model.
        """
        return None


class TimeStampedModel(HeadshipModel):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True  # Ensure no table is created for this model

from .attachment import Attachment
from .group_permissions import Group, Permission
from .headship import Headship
from .notification import NotificationTemplate
from .workflow import Workflow, WorkflowStep, Transition, Evaluation
