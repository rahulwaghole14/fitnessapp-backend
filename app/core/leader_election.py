import logging
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import engine

logger = logging.getLogger(__name__)

# Fixed lock key for scheduler and daily job generator leader election
SCHEDULER_LOCK_KEY = 777123456

class AdvisoryLockManager:
    """
    Manages PostgreSQL session-level advisory locks for leader election
    in multi-process/multi-pod deployments.
    """
    def __init__(self, lock_key: int = SCHEDULER_LOCK_KEY):
        self.lock_key = lock_key
        self._connection = None
        self._is_leader = False

    async def acquire_leader_lock(self) -> bool:
        """
        Attempts to acquire the session-level advisory lock.
        Returns True if acquired (process is now the leader), False otherwise.
        """
        if self._is_leader:
            return True

        try:
            # We must use raw_connection so that SQLAlchemy doesn't return it to the pool
            # and close it automatically when a session ends. We need a persistent session.
            loop = asyncio.get_running_loop()
            conn = await loop.run_in_executor(None, engine.raw_connection)
            
            # Execute pg_try_advisory_lock
            def try_lock(connection):
                cursor = connection.cursor()
                cursor.execute(f"SELECT pg_try_advisory_lock({self.lock_key});")
                result = cursor.fetchone()
                cursor.close()
                return result[0] if result else False

            acquired = await loop.run_in_executor(None, try_lock, conn)
            
            if acquired:
                self._connection = conn
                self._is_leader = True
                logger.info(f"[LEADER ELECTION] Successfully acquired advisory lock ({self.lock_key}). This process is the LEADER.")
                return True
            else:
                # Release connection if we didn't get the lock
                conn.close()
                self._is_leader = False
                logger.debug(f"[LEADER ELECTION] Failed to acquire advisory lock ({self.lock_key}). Another process is the leader.")
                return False
        except Exception as e:
            logger.error(f"[LEADER ELECTION] Error attempting to acquire advisory lock: {e}")
            if self._connection:
                try:
                    self._connection.close()
                except Exception:
                    pass
                self._connection = None
            self._is_leader = False
            return False

    def release_leader_lock(self):
        """Releases the advisory lock and closes the connection."""
        if not self._is_leader or not self._connection:
            return

        try:
            conn = self._connection
            def unlock(connection):
                cursor = connection.cursor()
                cursor.execute(f"SELECT pg_advisory_unlock({self.lock_key});")
                cursor.close()
            
            # Explicitly run advisory unlock on the connection before returning to pool/closing
            unlock(conn)
            conn.close()
            logger.info(f"[LEADER ELECTION] Released advisory lock ({self.lock_key}).")
        except Exception as e:
            logger.error(f"[LEADER ELECTION] Error releasing advisory lock: {e}")
        finally:
            self._connection = None
            self._is_leader = False

    @property
    def is_leader(self) -> bool:
        return self._is_leader

# Global advisory lock manager instance
scheduler_leader_lock = AdvisoryLockManager()
