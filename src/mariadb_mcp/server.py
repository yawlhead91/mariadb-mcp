#!/usr/bin/env python3
"""
MariaDB MCP Server

A Model Context Protocol server for MariaDB database operations.
Provides standard database tools compatible with Claude Code.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiomysql
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Configure logging
def setup_logging():
    """Setup logging with both console and file output."""
    import logging.handlers
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Get log level from environment (default to INFO)
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = log_dir / 'mariadb_mcp.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB max, 5 backups
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)

# Setup logging
logger = setup_logging()

class ConfigurationManager:
    """Manages configuration from environment variables."""
    
    def __init__(self):
        self.config = {}
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from environment variables with defaults."""
        
        # Load default .env file if it exists (for local development)
        default_env_file = Path(__file__).parent.parent.parent / '.env'
        if default_env_file.exists():
            load_dotenv(default_env_file, override=False)
        
        # Load configuration from environment variables
        # Note: Claude Code will set these from its 'env' or 'envFile' configuration
        self.config = {
            'host': os.getenv('MARIADB_HOST', 'localhost'),
            'port': int(os.getenv('MARIADB_PORT', '3306')),
            'user': os.getenv('MARIADB_USER', 'root'),
            'password': os.getenv('MARIADB_PASSWORD', ''),
            'database': os.getenv('MARIADB_DATABASE', 'mysql'),
        }
        
        logger.info(f"MariaDB configuration loaded: host={self.config['host']}, "
                   f"port={self.config['port']}, user={self.config['user']}, "
                   f"database={self.config['database']}")
    
    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def reload(self):
        """Reload configuration from environment."""
        self._load_configuration()

# Initialize configuration manager
config_manager = ConfigurationManager()

# Initialize MCP server
mcp = FastMCP("MariaDB MCP Server")

class MariaDBConnection:
    """Manages MariaDB database connections."""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.pool = None
        self.config_manager = config_manager
        self.host = config_manager.get('host')
        self.port = config_manager.get('port')
        self.user = config_manager.get('user')
        self.password = config_manager.get('password')
        self.database = config_manager.get('database')
        
    async def connect(self):
        """Create connection pool."""
        if self.pool is None:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                minsize=1,
                maxsize=10,
                autocommit=True
            )
            logger.info(f"Connected to MariaDB at {self.host}:{self.port}")
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results."""
        logger.debug(f"Executing query: {query[:100]}{'...' if len(query) > 100 else ''}")
        await self.connect()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                if cursor.description:
                    results = await cursor.fetchall()
                    logger.debug(f"Query returned {len(results)} rows")
                    return [dict(row) for row in results]
                logger.debug("Query executed successfully, no results returned")
                return []
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

@mcp.tool()
async def reload_config() -> str:
    """Reload configuration from environment variables and .env file."""
    try:
        # Close existing connection pool
        await db_connection.close()
        
        # Reload configuration
        config_manager.reload()
        
        # Update connection parameters
        db_connection.host = config_manager.get('host')
        db_connection.port = config_manager.get('port')
        db_connection.user = config_manager.get('user')
        db_connection.password = config_manager.get('password')
        db_connection.database = config_manager.get('database')
        db_connection.pool = None  # Reset pool to force reconnection
        
        logger.info("Configuration reloaded successfully")
        return "Configuration reloaded successfully. New connection will be established on next database operation."
        
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")
        return f"Error reloading configuration: {str(e)}"

# Global connection instance
db_connection = MariaDBConnection(config_manager)

@mcp.tool()
async def list_databases() -> str:
    """List all accessible databases in the MariaDB server."""
    logger.info("Tool called: list_databases")
    try:
        query = "SHOW DATABASES"
        results = await db_connection.execute_query(query)
        
        databases = [row['Database'] for row in results]
        logger.info(f"Found {len(databases)} databases")
        return f"Available databases ({len(databases)}):\n" + "\n".join(f"- {db}" for db in databases)
    
    except Exception as e:
        logger.error(f"Error listing databases: {e}")
        return f"Error listing databases: {str(e)}"

@mcp.tool()
async def list_tables(database: Optional[str] = None) -> str:
    """List all tables in a specific database."""
    try:
        if database:
            # Use the specified database
            query = f"SHOW TABLES FROM `{database}`"
        else:
            # Use current database
            query = "SHOW TABLES"
        
        results = await db_connection.execute_query(query)
        
        if not results:
            db_name = database or "current database"
            return f"No tables found in {db_name}"
        
        # Get table name from result (column name varies)
        tables = []
        for row in results:
            # The column name is usually "Tables_in_<database_name>"
            table_name = list(row.values())[0]
            tables.append(table_name)
        
        db_name = database or "current database"
        return f"Tables in {db_name} ({len(tables)}):\n" + "\n".join(f"- {table}" for table in tables)
    
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return f"Error listing tables: {str(e)}"

@mcp.tool()
async def get_table_schema(table_name: str, database: Optional[str] = None) -> str:
    """Get the schema/structure of a specific table."""
    try:
        if database:
            full_table_name = f"`{database}`.`{table_name}`"
        else:
            full_table_name = f"`{table_name}`"
        
        query = f"DESCRIBE {full_table_name}"
        results = await db_connection.execute_query(query)
        
        if not results:
            return f"Table '{table_name}' not found"
        
        schema_info = f"Schema for table '{table_name}':\n\n"
        schema_info += "| Field | Type | Null | Key | Default | Extra |\n"
        schema_info += "|-------|------|------|-----|---------|-------|\n"
        
        for row in results:
            field = row['Field']
            type_info = row['Type']
            null_info = row['Null']
            key_info = row['Key'] or ''
            default_info = row['Default'] or ''
            extra_info = row['Extra'] or ''
            
            schema_info += f"| {field} | {type_info} | {null_info} | {key_info} | {default_info} | {extra_info} |\n"
        
        # Also get table status for additional info
        status_query = f"SHOW TABLE STATUS LIKE '{table_name}'"
        if database:
            status_query = f"SHOW TABLE STATUS FROM `{database}` LIKE '{table_name}'"
        
        status_results = await db_connection.execute_query(status_query)
        if status_results:
            status = status_results[0]
            schema_info += f"\nTable Info:\n"
            schema_info += f"- Engine: {status.get('Engine', 'N/A')}\n"
            schema_info += f"- Rows: {status.get('Rows', 'N/A')}\n"
            schema_info += f"- Data Length: {status.get('Data_length', 'N/A')} bytes\n"
            schema_info += f"- Auto Increment: {status.get('Auto_increment', 'N/A')}\n"
            schema_info += f"- Create Time: {status.get('Create_time', 'N/A')}\n"
            schema_info += f"- Comment: {status.get('Comment', 'N/A')}\n"
        
        return schema_info
    
    except Exception as e:
        logger.error(f"Error getting table schema: {e}")
        return f"Error getting table schema: {str(e)}"

@mcp.tool()
async def execute_sql(query: str, database: Optional[str] = None) -> str:
    """Execute a read-only SQL query and return results."""
    try:
        # Security check: only allow SELECT, SHOW, DESCRIBE, EXPLAIN queries
        query_upper = query.strip().upper()
        allowed_keywords = ['SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN', 'WITH']
        
        if not any(query_upper.startswith(keyword) for keyword in allowed_keywords):
            return "Error: Only read-only queries (SELECT, SHOW, DESCRIBE, EXPLAIN) are allowed"
        
        # Switch database if specified
        if database:
            await db_connection.execute_query(f"USE `{database}`")
        
        results = await db_connection.execute_query(query)
        
        if not results:
            return "Query executed successfully. No results returned."
        
        # Format results as a table
        if len(results) == 0:
            return "No rows returned"
        
        # Get column names
        columns = list(results[0].keys())
        
        # Create table header
        output = "Query Results:\n\n"
        header = " | ".join(columns)
        separator = " | ".join(["-" * len(col) for col in columns])
        output += header + "\n" + separator + "\n"
        
        # Add data rows (limit to 100 rows for readability)
        for i, row in enumerate(results[:100]):
            row_data = " | ".join([str(row.get(col, '')) for col in columns])
            output += row_data + "\n"
        
        if len(results) > 100:
            output += f"\n... and {len(results) - 100} more rows (truncated for display)"
        
        output += f"\nTotal rows: {len(results)}"
        
        return output
    
    except Exception as e:
        logger.error(f"Error executing SQL: {e}")
        return f"Error executing SQL: {str(e)}"

def main():
    """Main entry point for the MCP server."""
    logger.info("Starting MariaDB MCP Server...")
    # FastMCP.run() is synchronous and handles asyncio properly
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()