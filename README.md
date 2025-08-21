# MariaDB MCP Server

A Model Context Protocol (MCP) server for MariaDB database operations, compatible with Claude Code and other MCP clients.

## Features

This MCP server provides these standard database tools:

- **list_databases**: List all accessible databases
- **list_tables**: List tables in a database
- **get_table_schema**: Get detailed table schema and statistics
- **execute_sql**: Execute read-only SQL queries (SELECT, SHOW, DESCRIBE, EXPLAIN)
- **reload_config**: Reload configuration without restarting

## Installation

### Prerequisites

- Python 3.10 or higher
- MariaDB server running
- `uv` package manager

### Quick Setup

```bash
# Clone/download this repository
cd mariadb-mcp

# Install dependencies
uv sync

# Configure database connection
cp .env.example .env
# Edit .env with your MariaDB credentials
```

## Configuration

### Environment Variables

Configure your MariaDB connection using these environment variables:

```env
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=your_password_here
MARIADB_DATABASE=mysql

# Optional: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO
```

### Local Development

For local testing, create a `.env` file in the project root with your database credentials.

## Usage

### Command Line

Run the server directly:

```bash
uv run python src/mariadb_mcp/server.py
```

Connect with Claude Code in another terminal:

```bash
claude-code --mcp-server "uv run python src/mariadb_mcp/server.py"
```

### Adding to Claude Code Permanently

To add this server to your Claude Code MCP server list:

#### Manual Configuration

Add to your Claude Code configuration file:

**Option A: Using environment file (recommended)**

```json
{
  "mcpServers": {
    "MariaDB_Server": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/mariadb-mcp/",
        "run",
        "python",
        "src/mariadb_mcp/server.py"
      ],
      "envFile": "/absolute/path/to/mariadb-mcp/.env"
    }
  }
}
```

**Option B: Direct environment variables**

```json
{
  "mcpServers": {
    "MariaDB_Server": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/mariadb-mcp/",
        "run",
        "python",
        "src/mariadb_mcp/server.py"
      ],
      "env": {
        "MARIADB_HOST": "localhost",
        "MARIADB_PORT": "3306",
        "MARIADB_USER": "root",
        "MARIADB_PASSWORD": "your_password_here",
        "MARIADB_DATABASE": "mysql"
      }
    }
  }
}
```

**Note**: When both `env` and `envFile` are specified, `env` variables take precedence.

**After configuration:**

1. Restart Claude Code
2. Verify "MariaDB_Server" appears in your MCP server list
3. Test with: "List all databases"

## Available Tools

### reload_config()

Reload database configuration without restarting the server.

**Example**: "Reload the database configuration"

### list_databases()

List all databases you have access to.

**Example**: "List all available databases"

### list_tables(database: Optional[str])

List tables in a database.

**Parameters:**

- `database` (optional): Database name

**Examples:**

- "List tables in the current database"
- "List tables in the 'myapp' database"

### get_table_schema(table_name: str, database: Optional[str])

Get detailed schema information for a table.

**Parameters:**

- `table_name`: Table name
- `database` (optional): Database name

**Examples:**

- "Show schema for the 'users' table"
- "Get table structure for 'orders' in the 'ecommerce' database"

### execute_sql(query: str, database: Optional[str])

Execute read-only SQL queries.

**Parameters:**

- `query`: SQL query to execute
- `database` (optional): Database to use

**Examples:**

- "Execute: SELECT \* FROM users LIMIT 10"
- "Run query: SHOW CREATE TABLE products"
- "Execute in 'analytics' database: SELECT COUNT(\*) FROM events"

## Security

- **Read-only operations**: Only SELECT, SHOW, DESCRIBE, EXPLAIN allowed
- **No data modification**: INSERT, UPDATE, DELETE, DDL statements blocked
- **Connection pooling**: Efficient resource management
- **Comprehensive logging**: Full error reporting

## Troubleshooting

### Connection Issues

1. Verify MariaDB is running:

   ```bash
   sudo systemctl status mariadb
   # or on macOS with Homebrew:
   brew services list | grep mariadb
   ```

2. Test connection manually:

   ```bash
   mysql -h localhost -u root -p
   ```

3. Check firewall settings for remote connections

### Permission Issues

Ensure your MariaDB user has SELECT permissions:

```sql
GRANT SELECT ON *.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

### Debug Mode

For development debugging:

```bash
uv run mcp dev src/mariadb_mcp/server.py
```

## Logging

The MariaDB MCP server includes comprehensive logging for monitoring and debugging:

### Log Locations

- **Console**: Real-time logs displayed in the terminal
- **Log Files**: Stored in `logs/mariadb_mcp.log` with automatic rotation
  - Maximum file size: 10MB
  - Backup files: 5 (mariadb_mcp.log.1, mariadb_mcp.log.2, etc.)

### Log Levels

Set the `LOG_LEVEL` environment variable to control log verbosity:

- **DEBUG**: Detailed information for diagnosing problems (shows SQL queries)
- **INFO**: General information about server operations (default)
- **WARNING**: Something unexpected happened but the server continues
- **ERROR**: An error occurred but the server continues
- **CRITICAL**: A serious error occurred

### Example Logging Configuration

```env
# In your .env file
LOG_LEVEL=DEBUG  # For detailed debugging
```

Or in Claude Code configuration:

```json
"env": {
  "MARIADB_HOST": "localhost",
  "MARIADB_USER": "root",
  "MARIADB_PASSWORD": "dev",
  "LOG_LEVEL": "DEBUG"
}
```

### Log Contents

Logs include:

- Server startup/shutdown events
- Database connection status
- Tool function calls and results
- SQL query execution (DEBUG level)
- Error messages with stack traces
- Configuration changes

## License

MIT License
