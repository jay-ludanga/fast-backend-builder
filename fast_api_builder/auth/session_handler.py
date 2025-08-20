from datetime import datetime, timezone
from tortoise.exceptions import DoesNotExist


from fast_api_builder.muarms.models.uaa import DjangoSession, User
from fast_api_builder.utils.error_logging import log_exception


class SessionHandler:
    
    async def get_data(self, session_id: str, token_expiry: int = 0):
        try:
            expiry_datetime = datetime.fromtimestamp(token_expiry, tz=timezone.utc)
            if token_expiry and expiry_datetime < datetime.now(timezone.utc):
                return {
                    'data': None,
                    'error': "TOKEN_EXPIRED"
                }, None
                
            session: DjangoSession = await DjangoSession.get(session_key=session_id)
            if session.expire_date < datetime.now(timezone.utc):
                return {
                    'data': None,
                    'error': "EXPIRED"
                }, None

            user = await User.filter(id=session.user_id).prefetch_related(
                "student__programme__programme_type"
            ).first()
            
            if user:
                return {
                    'data': {
                        'user_id': user.id,
                        'email': user.email
                    },
                    'error': None
                }, user
                
            else:
                return {
                    'data': None,
                    'error': 'INVALID'
                }, None
            
        except DoesNotExist as e:
            log_exception(e)
            return {
                'data': None,
                'error': 'INVALID'
            }, None
        
        except Exception as e:
            log_exception(e)
            return {
                'data': None,
                'error': 'ERROR'
            }, None