from datetime import timedelta
import asyncpg
import asyncio
import time

from fast_api_builder.utils.error_logging import log_exception, log_message, log_warning

class DBMetrics:
    _instance = None
    is_fetching = False

    def __new__(cls, *args, **kwargs):
        # Prevent instantiation if an instance already exists
        if cls._instance is None:
            cls._instance = super(DBMetrics, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # Avoid re-initializing
            """Initialize the service with a default interval."""
            self.db_host = None
            self.db_port = None
            self.db_name = None
            self.db_user = None
            self.db_password = None
            self.idle_connections = None
            self.idle_locks = None
            self.idle_max_query = None
            self.is_debug = None

            self.initialized = False
            
    async def init(self, 
        db_host: str, 
        db_port: int, 
        db_name: str, 
        db_user: str, 
        db_password: str, 
        idle_connections: int, 
        idle_locks: int, 
        idle_max_query: int, 
        debug: bool = False
    ):
        try:
            if not self.initialized:
                # Initialize the attributes only once
                self.db_host = db_host
                self.db_port = db_port
                self.db_name = db_name
                self.db_user = db_user
                self.db_password = db_password
                self.idle_connections = idle_connections
                self.idle_locks = idle_locks
                self.idle_max_query = idle_max_query
                self.is_debug = debug
                
                self.initialized = True
                print(f"DBMetrics service initialized successfully")
            else:
                print("DBMetrics service is already initialized.")

            return True
        except Exception as e:
            log_exception(f"Failed to initialize DBMetrics service: {str(e)}")
            return False

    async def is_db_idle(self) -> bool:
        conn = await asyncpg.connect(
            host=self.db_host, 
            port=self.db_port, 
            user=self.db_user, 
            password=self.db_password, 
            database=self.db_name
        )
        
        # Query to check for active connections, long-running queries, and locks
        query = """
        SELECT 
            COUNT(*) AS active_connections,
            MAX(AGE(NOW(), query_start)) AS max_query_duration,
            COUNT(l.locktype) AS active_locks
        FROM pg_stat_activity sa
        LEFT JOIN pg_locks l ON sa.pid = l.pid
        WHERE sa.state = 'active' 
        AND sa.query != '<IDLE>' 
        AND sa.pid != pg_backend_pid();
        """
        result = await conn.fetchrow(query)
        
        # Check the conditions to determine if the DB is idle:
        active_connections = result['active_connections']
        max_query_duration = result['max_query_duration']
        active_locks = result['active_locks']
        
        log_message(f"")
        
        print(f"CONN: {active_connections}, MAX_QUERY: {max_query_duration}, LOCKS: {active_locks}")
        
        # Example threshold: DB is considered idle if there are fewer than 10 active connections and no long-running queries
        # You can adjust these thresholds based on your system's behavior
        db_idle = (
            active_connections <= self.idle_connections and 
            (max_query_duration is None or max_query_duration <= timedelta(seconds=self.idle_max_query)) and 
            active_locks <= self.idle_locks
        )
        
        await conn.close()

        return db_idle