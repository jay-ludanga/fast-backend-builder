from abc import abstractmethod
from typing import Any, Dict, List
from tortoise import models
from tortoise import fields
from tortoise.exceptions import IntegrityError

from fast_api_builder.muarms.enums import HeadshipType

class HeadshipMixin(models.Model):
    """
    A mixin to handle headship logic for CRUD operations, including create, update, and delete.
    """
    
    class Meta:
        abstract = True
    
    # # Override the save method to handle create and update
    # async def save(self, user, *args, **kwargs):
    #     # Check headship for create or update
    #     if not await self.has_headship_access(user):
    #         raise IntegrityError("You do not have permission to create or update this resource.")

    #     # Call the actual save method
    #     await super().save(*args, **kwargs)

    # # Override the delete method to enforce headship rules
    # async def delete(self, user, *args, **kwargs):
    #     # Check headship before deletion
    #     if not await self.has_headship_access(user):
    #         raise IntegrityError("You do not have permission to delete this resource.")
        
    #     # Call the actual delete method
    #     await super().delete(*args, **kwargs)

    # # Override the create method to enforce headship rules
    # @classmethod
    # async def create(cls, user, **kwargs):
    #     # Check headship before creation
    #     instance = cls(**kwargs)
    #     if not await instance.has_headship_access(user):
    #         raise IntegrityError("You do not have permission to create this resource.")
        
    #     # Call the actual create method to save the instance
    #     await instance.save()
    #     return instance

    # Custom method to filter by user's headship (for list queries)
    @classmethod
    async def with_headship(cls, user):
        
        model_headships = cls.headships()        
        query = cls
        
        filtered = False
        
        for model_headship in model_headships:
            from fast_api_builder.auth.auth import Auth
            user_headships = Auth.user_headships(model_headship['headship_type'])
            
            for user_headship in user_headships:
                if user_headship:
                    
                    if user_headship.headship_type == HeadshipType.GLOBAL:
                        return query
                
                    filtered = True
                
                    ids = await model_headship['model'].filter(
                        **{f"{model_headship['path']}_id": user_headship.headship_type_id}
                    ).prefetch_related(f"{model_headship['path']}").values_list('id', flat=True)
                    
                    query = query.filter(**{f"{model_headship['column']}__in": ids})

        if not filtered and len(model_headships):
            query = query.filter(**{f"{model_headship['column']}__in": ["__NOTHING__"]})

        return query

    # Check whether a user has access to a particular instance based on headship
    # async def has_headship_access(self, user):
    #     # Check if user has access to this particular record
    #     return (
    #         (self.global_headship == user.headship.global_headship) or
    #         (self.institution == user.headship.institution) or
    #         (self.region == user.headship.region and
    #          self.district == user.headship.district and
    #          self.ward == user.headship.ward)
    #     )
        
    """
    Abstract base class that defines the `headships()` method.
    
    This method should return a list of dictionaries where each dictionary defines:
      - `model`: The Tortoise ORM model related to the entity (e.g., `Ward`).
      - `headship_type`: The type of headship (from the `HeadshipType` enum).
      - `column`: The foreign key column that links the resource to a headship 
                  (e.g., 'ward_id' for resources linked to wards).
      - `path`: The ORM path for filtering or accessing data through nested relationships.
               This helps identify how the resource is related to a specific entity 
               (e.g., a `Ward` linked via a region > district > council > division).
    
    Classes that inherit this abstract base class must implement their own version of `headships()`
    to define resource-specific headship relationships.

    This allows CRUD operations (create, read, update, delete) to be governed based on headship rules,
    ensuring that only users with the appropriate headship can perform operations on resources.
    """
    
    @classmethod
    def headships(self) -> List[Dict[str, Any]]:
        """
        Abstract method to be implemented by child classes.

        Returns:
            A list of dictionaries, where each dictionary defines:
              - `model`: The ORM model related to this model which is linked with headship rules.
              - `headship_type`: The type of headship (from `HeadshipType` enum).
              - `column`: The field in this model which is the foreign key to the model.
              - `path`: The ORM path for filtering using relationships describing parents of the model.
        """
        pass